import streamlit as st
from snowflake.snowpark.context import get_active_session
import json



connection_parameters = st.secrets["connections"]["my_example_connection"]
session = Session.builder.configs(connection_parameters).create()



st.set_page_config(page_title="Small LLM Chatbot (SiS + Cortex)", page_icon="🤖", layout="centered")
st.title("🤖 ChatBot")
 
# --- Settings ---
# Pick a small, cost-effective model:
SMALL_MODEL = "llama3-8b"   # try "mistral-7b" or "gemma-7b"
 
# System prompt to steer tone/format
SYSTEM_PROMPT = (
    "Answer in English, concisely, with brief code when useful."
)
def init_history():
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "assistant", "content": "Hi! Ask me anything about Anything"},
    ]
 
if "messages" not in st.session_state:
    init_history()
 
# --- Chat state ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "assistant", "content": "Hi! Ask me anything about Snowflake, Streamlit, or data engineering."},
    ]
 
# Render history (skip system for UI)
for m in st.session_state.messages:
    if m["role"] == "system":
        continue
    with st.chat_message(m["role"]):
        st.write(m["content"])
 
# --- Ask ---
prompt = st.chat_input("Type your question…")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
 
    # Call Cortex COMPLETE with full conversation history
    session = get_active_session()
 
    # Build Cortex chat array: [{role, content}, ...]
    # Keep history but cap to avoid too many tokens
    history = st.session_state.messages[-10:]  # last 10 turns (includes system once)
    # Convert to SQL array of objects via Python list-of-dicts directly; Snowflake Python SDK handles it.
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            result = session.sql("""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                ?,                               -- model name (STRING)
                PARSE_JSON(?),                   -- messages as VARIANT (from JSON string)
                OBJECT_CONSTRUCT(                -- options as VARIANT
                    'temperature', 0.2,
                    'max_tokens', 400,
                    'guardrails', TRUE
                )
            ) AS resp
        """, params=[SMALL_MODEL, json.dumps(history)]).collect()[0]["RESP"]
 
        # COMPLETE returns a plain string if options omitted; with options it returns JSON string with choices->messages
        # We'll try to parse; if it fails, just show the raw string.
        import json
        try:
            obj = json.loads(result)
            reply = obj["choices"][0]["messages"]
        except Exception:
            reply = result
 
        st.write(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})
 
with st.sidebar:
    st.subheader("Model & Settings")
    st.caption("Using Snowflake Cortex COMPLETE under the hood.")
    st.markdown(f"- *Model:* {SMALL_MODEL}  \n- *temperature:* 0.2  \n- *max_tokens:* 400  \n- *guardrails:* on")
    st.markdown(
        "Try switching to 'mistral-7b' or 'gemma-7b' for similar speed/cost profiles."
    )
    if st.button("🧹 Clear chat", type="secondary"):
        init_history()
        st.rerun()
