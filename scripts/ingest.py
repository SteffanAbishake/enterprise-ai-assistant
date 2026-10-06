"""Explicit live-only command. Requires an existing dense 1536-dimensional cosine index."""
import asyncio
from app.config import Settings
from app.providers import Providers
from app.retrieval import load_documents, chunks


async def main():
    settings = Settings()
    if settings.app_mode != "live":
        raise SystemExit("Set APP_MODE=live deliberately before ingestion (provider usage applies)")
    providers = Providers(settings)
    try:
        rows = [row for doc in load_documents() for row in chunks(doc)]
        for start in range(0, len(rows), 50):
            batch = rows[start:start + 50]
            embeddings = await providers.embed([r["text"] for r in batch])
            await providers.pinecone("/vectors/upsert", {"vectors": [
                {"id": row["id"], "values": vector, "metadata": row}
                for row, vector in zip(batch, embeddings, strict=True)
            ]})
        print(f"Upserted {len(rows)} sections; allow time for Pinecone indexing.")
    finally:
        await providers.close()


if __name__ == "__main__":
    asyncio.run(main())
