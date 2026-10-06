import hashlib
import json
import os
from uuid import uuid4

import httpx
import streamlit as st

st.set_page_config(page_title="Demo Bank Knowledge Assistant", layout="wide")
st.title("Demo Bank · Knowledge Assistant")
st.caption(
    "Fictional enterprise data · evidence and activity are visible · no financial transactions"
)

with st.sidebar:
    st.header("Connection")
    api_key = st.text_input("Your assigned API key", type="password")
    st.caption(
        "The backend determines your role from this key. Changing UI text cannot elevate access."
    )
    department = st.selectbox("Department", ["All allowed", "payments", "platform", "hr"])
    use_dates = st.checkbox("Filter document dates")
    since = st.date_input("From") if use_dates else None
    until = st.date_input("Through") if use_dates else None
    if st.button("New conversation"):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid4())
    st.markdown("Try: **Summarize payment outages and recurring root causes** (analyst key).")
    st.markdown("Try: **Who owns the payments service?** (analyst key, MCP enabled).")

# A changed identity must not retain another identity's chat in the same browser session.
key_fingerprint = hashlib.sha256(api_key.encode()).hexdigest()
if st.session_state.get("key_fingerprint") != key_fingerprint:
    st.session_state.messages = []
    st.session_state.session_id = str(uuid4())
    st.session_state.key_fingerprint = key_fingerprint

api_url = os.environ.get("API_URL", "http://localhost:8000")
st.session_state.setdefault("messages", [])
st.session_state.setdefault("session_id", str(uuid4()))
chat_col, activity_col = st.columns([2, 1])
with activity_col:
    st.subheader("Agent activity")
    activity_box = st.empty()
with chat_col:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

if question := st.chat_input("Ask about the indexed documents", disabled=not api_key):
    with chat_col:
        with st.chat_message("user"):
            st.markdown(question)
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("assistant"):
            response_box = st.empty()
            output, activity, final = "", [], None
            try:
                with httpx.stream(
                    "POST",
                    f"{api_url}/chat",
                    headers={"X-API-Key": api_key},
                    json={
                        "session_id": st.session_state.session_id,
                        "message": question,
                        "department": None if department == "All allowed" else department,
                        "since": since.isoformat() if since else None,
                        "until": until.isoformat() if until else None,
                    },
                    timeout=100,
                ) as response:
                    if response.status_code != 200:
                        response.read()
                        st.error(
                            f"Request rejected ({response.status_code}): {response.json().get('detail', 'Error')}"
                        )
                    else:
                        for line in response.iter_lines():
                            if not line.startswith("data: "):
                                continue
                            event = json.loads(line[6:])
                            if event["type"] == "token":
                                output += event["text"]
                                response_box.markdown(output)
                            elif event["type"] == "activity":
                                activity.append(event)
                                activity_box.json(activity[-20:])
                            elif event["type"] == "answer":
                                final = event
                                response_box.markdown(event["text"])
                                for warning in event["warnings"]:
                                    st.warning(warning)
                                with st.expander("Supporting evidence"):
                                    st.json(event["sources"])
                            elif event["type"] == "done":
                                st.caption(f"Trace ID: {event['trace_id']}")
                            elif event["type"] == "error":
                                st.error(event["message"])
                if final:
                    st.session_state.messages.append(
                        {"role": "assistant", "content": final["text"]}
                    )
            except (httpx.HTTPError, ValueError):
                st.error("Cannot reach the API. Check that the backend is running and retry.")
