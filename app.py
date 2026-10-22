"""Run:  streamlit run app.py"""
import os
import sqlite3
import streamlit as st
import pandas as pd
import agent

st.set_page_config(page_title="Data Analysis Agent", page_icon="📊")
st.title("📊 Natural-Language Data Analysis Agent")


def get_connection():
    """Sample shop database, or an in-memory database built from the user's uploaded CSV files."""
    source = st.sidebar.radio("Data source", ["Sample shop database", "Upload my own CSV"])
    if source == "Sample shop database":
        return sqlite3.connect(agent.seed_sample_db("sample.db"), check_same_thread=False)

    files = st.sidebar.file_uploader("Upload one or more CSV files", type="csv", accept_multiple_files=True)
    if not files:
        st.info("Upload a CSV file from the sidebar to start. (Or switch to the sample database.)")
        return None
    key = tuple((f.name, f.size) for f in files)
    if st.session_state.get("csv_key") != key:  # rebuild only when the files change
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        for f in files:
            try:
                df = pd.read_csv(f)
            except Exception as e:
                st.sidebar.error(f"Could not read {f.name}: {e}")
                continue
            agent.load_csv_to_db(conn, df, os.path.splitext(f.name)[0])
        st.session_state["csv_key"], st.session_state["csv_conn"] = key, conn
    return st.session_state["csv_conn"]


conn = get_connection()
if conn is None:
    st.stop()

schema = agent.get_schema(conn)
if not schema:
    st.warning("No tables found in the database.")
    st.stop()

with st.sidebar:
    st.header("Database schema")
    st.code(schema, language="sql")

with st.sidebar:
    st.header("LLM")
    names = {"Claude API (needs key)": "claude", "Gemini API (free tier, needs key)": "gemini",
             "Free local model (Ollama)": "ollama"}
    default = 0 if os.getenv("ANTHROPIC_API_KEY") else 1 if os.getenv("GEMINI_API_KEY") else 2
    choice = st.radio("Which LLM to use?", list(names), index=default)
    agent.PROVIDER = names[choice]
    if agent.PROVIDER == "ollama":
        st.caption(f"Needs Ollama running with the model: ollama pull {agent.OLLAMA_MODEL}. Works only on your own computer.")
    elif agent.PROVIDER == "gemini":
        st.caption("Free key from Google AI Studio. Do not use private data with the free tier.")
    st.header("Agent settings")
    strategy = st.selectbox("Prompt strategy", list(agent.STRATEGIES), index=len(agent.STRATEGIES) - 1,
                            format_func=lambda k: agent.STRATEGIES[k])
    self_correct = st.checkbox("Self-correction (retry on errors)", value=True)

with st.expander("Preview tables"):
    for (tname,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
        st.write(f"**{tname}**")
        st.dataframe(pd.read_sql_query(f'SELECT * FROM "{tname}" LIMIT 5', conn))

question = st.text_input("Ask a question about the data")

MAX_QUESTIONS = int(os.getenv("MAX_QUESTIONS", "25"))  # per browser session; protects your API credits

if question and not agent.llm_ready():
    key_name = "GEMINI_API_KEY" if agent.PROVIDER == "gemini" else "ANTHROPIC_API_KEY"
    st.error(f"{key_name} is not set for the selected LLM. Pick another LLM in the sidebar, set the key (see README), "
             "or use 'Run SQL manually' below, for example: SELECT name, price FROM products WHERE name = 'Laptop'")

if question and agent.llm_ready():
    cache = st.session_state.setdefault("cache", {})
    key = (question, strategy, self_correct, schema, agent.PROVIDER)
    if key not in cache:  # call the LLM only for new questions, not on every page refresh
        if len(cache) >= MAX_QUESTIONS:
            st.error(f"Question limit ({MAX_QUESTIONS}) reached for this session. Refresh the page to start again.")
            st.stop()
        try:
            with st.spinner("Thinking... (a local model can take 10-60 seconds)"):
                result = agent.answer_question(conn, question, max_retries=2 if self_correct else 0, strategy=strategy)
                if result["df"] is not None and len(result["df"]):
                    result["explanation"] = agent.explain(question, result["sql"], result["df"])
        except Exception as e:
            st.error(f"LLM problem: {e}")
            st.stop()
        cache[key] = result
    result = cache[key]
    st.subheader("Generated SQL")
    st.code(result["sql"] or "", language="sql")
    if result["error"]:
        st.error(f"Could not get a valid answer after {result['attempts']} attempt(s): {result['error']}")
    else:
        df = result["df"]
        st.caption(f"Query succeeded in {result['attempts']} attempt(s).")
        st.dataframe(df)
        if df.shape[1] == 2 and pd.api.types.is_numeric_dtype(df.iloc[:, 1]):
            st.bar_chart(df.set_index(df.columns[0]))
        if result.get("explanation"):
            st.subheader("Explanation")
            st.write(result["explanation"])

with st.expander("Run SQL manually (no API key needed)"):
    manual = st.text_area("SELECT query", "SELECT * FROM " + conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' LIMIT 1").fetchone()[0] + " LIMIT 10")
    if st.button("Run"):
        ok, reason = agent.is_safe(manual)
        if not ok:
            st.error(reason)
        else:
            try:
                st.dataframe(agent.run_query(conn, manual))
            except Exception as e:
                st.error(str(e))