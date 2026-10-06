import asyncio
import json
import re
from pathlib import Path

from langsmith import traceable
from rank_bm25 import BM25Okapi

from app.models import Document
from app.security import SUSPICIOUS, allowed, authorize

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "documents.json"


def tokens(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def load_documents():
    return [Document.model_validate(d) for d in json.loads(DATA_PATH.read_text())]


def chunks(doc):
    # Bounded overlapping sections; metadata and parent attribution are retained.
    words = doc.text.split()
    for i, start in enumerate(range(0, len(words), 140)):
        yield {
            "id": f"{doc.id}#{i}",
            "doc_id": doc.id,
            "title": doc.title,
            "text": " ".join(words[start : start + 180]),
            "department": doc.department,
            "access_level": doc.access_level,
            "document_type": doc.document_type,
            "created_day": doc.created_date.toordinal(),
            "created_date": doc.created_date.isoformat(),
            "root_cause": doc.root_cause or "unspecified",
        }


def fuse(sparse, dense, limit):
    scores, rows = {}, {}
    for ranking in (sparse, dense):
        for rank, row in enumerate(ranking, 1):
            key = row["id"]
            rows[key] = row
            scores[key] = scores.get(key, 0) + 1 / (60 + rank)
    return [
        {**rows[k], "score": scores[k]}
        for k in sorted(scores, key=scores.get, reverse=True)[:limit]
    ]


class Retrieval:
    def __init__(self, settings, providers):
        self.settings, self.providers = settings, providers
        self.documents = load_documents()
        self.by_id = {d.id: d for d in self.documents}

    def eligible(self, user, request):
        return [
            d
            for d in self.documents
            if allowed(user, d)
            and (not request.department or d.department == request.department)
            and (not request.since or d.created_date >= request.since)
            and (not request.until or d.created_date <= request.until)
            and not SUSPICIOUS.search(d.text)
        ]

    @traceable(name="hybrid_knowledge_search", run_type="retriever")
    async def search(self, user, request, query, limit=12):
        authorize(user, "search")
        eligible = self.eligible(user, request)
        sections = [c for d in eligible for c in chunks(d)]
        if not sections:
            return [], []

        def sparse_search():
            scores = BM25Okapi([tokens(c["text"] + " " + c["title"]) for c in sections]).get_scores(
                tokens(query)
            )
            return [
                sections[i]
                for i in sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
                if scores[i] > 0
            ][:limit]

        warnings = []

        async def dense_search():
            if self.settings.app_mode == "local":
                return []  # Explicit BM25-only baseline; never pretend this is semantic embedding.
            filters = [
                {"department": {"$in": user.departments}},
                {
                    "access_level": {
                        "$in": ["internal", "restricted"]
                        if user.role == "administrator"
                        else ["internal"]
                    }
                },
            ]
            if request.department:
                filters.append({"department": {"$eq": request.department}})
            if request.since:
                filters.append({"created_day": {"$gte": request.since.toordinal()}})
            if request.until:
                filters.append({"created_day": {"$lte": request.until.toordinal()}})
            try:
                vector = (await self.providers.embed([query]))[0]
                result = await self.providers.pinecone(
                    "/query",
                    {
                        "vector": vector,
                        "topK": limit,
                        "includeMetadata": True,
                        "filter": {"$and": filters},
                    },
                )
                # Revalidate IDs against trusted catalog; do not trust vector-store text or ACLs.
                permitted = {c["id"]: c for c in sections}
                return [
                    permitted[m["id"]] for m in result.get("matches", []) if m["id"] in permitted
                ]
            except Exception:
                warnings.append("Dense retrieval unavailable; using authorized keyword results.")
                return []

        sparse, dense = await asyncio.gather(asyncio.to_thread(sparse_search), dense_search())
        return fuse(sparse, dense, limit), warnings
