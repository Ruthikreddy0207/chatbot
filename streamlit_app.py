import streamlit as st
import json

st.set_page_config(page_title="Small LLM Chatbot (SiS + Cortex)", page_icon="🤖", layout="centered")
st.title("🤖 ChatBot 🤖 ")

SMALL_MODEL = "llama3-8b"
SYSTEM_PROMPT = "Answer in English, concisely, with brief code when useful."

def init_history():
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "assistant", "content": "Hi! Ask me anything about Anything"},
    ]

if "messages" not in st.session_state:
    init_history()

for m in st.session_state.messages:
    if m["role"] == "system":
        continue
    with st.chat_message(m["role"]):
        st.write(m["content"])

prompt = st.chat_input("Type your question…")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # Get Snowflake session via st.connection
    cnx = st.connection("snowflake")
    session = cnx.session()

    history = st.session_state.messages[-10:]

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            result = session.sql("""
                SELECT SNOWFLAKE.CORTEX.COMPLETE(
                    ?, 
                    PARSE_JSON(?), 
                    OBJECT_CONSTRUCT(
                        'temperature', 0.2,
                        'max_tokens', 400,
                        'guardrails', TRUE
                    )
                ) AS resp
            """, params=[SMALL_MODEL, json.dumps(history)]).collect()[0]["RESP"]

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
    st.markdown("Try switching to 'mistral-7b' or 'gemma-7b' for similar speed/cost profiles.")
    if st.button("🧹 Clear chat", type="secondary"):
        init_history()
        st.experimental_rerun()
