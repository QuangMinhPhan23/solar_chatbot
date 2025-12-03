import json
import streamlit as st
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from db import get_connection
import agents
# ======================= Setup =======================

load_dotenv()
st.set_page_config(page_title="Simple Ask DB", page_icon="🔆🔋", layout="wide")

def load_css(css_path: str = "styles.css"):
    p = Path(css_path)
    if not p.exists():
        st.warning(f"Custom CSS not found at {css_path}. Skipping style injection.")
        return
    st.markdown(f"<style>{p.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

load_css("styles.css")

# ======================= UI =======================
st.title("☀️ Solar PV Performance Analytics Chatbot")
st.caption("Ask about solar PV performance metrics, energy output, and more.")

with st.form("ask_form", clear_on_submit=False):
    question = st.text_input(
        "Question",
        placeholder="Examples: What is the average daily production? · What is the peak power in March 2025?",
    )
    ask = st.form_submit_button("Ask", type="primary")

if ask:
    if not question.strip():
        st.warning("Please enter a question before clicking Ask.")
        st.stop()
    
    sql = "(n/a)"
    df = pd.DataFrame()
    predict_json = None
    final_answer = ""
    
    # Create fresh connection for this request
    conn = None
    try:
        conn = get_connection()

        if agents.is_user_intent_destructive(question):
            st.error("Sorry, I can't delete or modify data. This app is read-only.")
            st.stop()

        with st.spinner("Generating SQL & running..."):
            deps = agents.Deps(conn=conn)
            try:
                res = agents.sql_agent.run_sync(question, deps=deps)
                sql = res.output.sql_query.strip().rstrip(";")
            except Exception as e:
                st.error(f"SQL generation failed: {e}")
                st.stop()

            if not agents.is_select_only(sql):
                st.error("Blocked a non-SELECT or potentially destructive SQL.")
                st.subheader("Generated (blocked) SQL")
                st.code(sql, language="sql")
                st.stop()

            try:
                # Reconnect if connection was closed
                if conn.is_closed():
                    conn.reconnect()
                
                df = conn.execute(sql).fetchdf()
            except Exception as e:
                st.error(f"Query failed: {e}")
                st.subheader("Generated SQL")
                st.code(sql, language="sql")
                st.stop()

            rows_for_llm = json.loads(
                df.head(agents.ANSWER_ROWS_LIMIT).to_json(orient="records", date_format="iso")
            )
            row_count = len(rows_for_llm)
            columns = list(df.columns)
            prompt = (
                f"QUESTION:\n{question}\n\n"
                f"ROW_COUNT: {row_count}\n"
                f"COLUMNS: {columns}\n"
                "SQL RESULT ROWS (JSON array of objects):\n"
                f"{json.dumps(rows_for_llm, ensure_ascii=False)}"
            )
            try:
                ans = agents.answer_agent.run_sync(prompt)
                if isinstance(ans.output, str):
                    final_answer = ans.output
                else:
                    final_answer = ans.output.final_answer
            except Exception as e:
                final_answer = f"Could not summarize result. Error: {e}"
    
    finally:
        # Always close connection after request
        if conn:
            try:
                conn.close()
            except:
                pass  # Ignore errors on close

    # ====== Output ======
    st.markdown(f"#### 🧠 Answer to: *{question}*")
    tab1, tab2, tab3, tab4 = st.tabs(["🧾 Answer", "🧮 SQL", "📊 Table", "🧱 JSON"])

    with tab1:
        st.markdown(
            f"<div class='card' style='color:#9333ea; font-weight:500;'>{final_answer}</div>",
            unsafe_allow_html=True,
        )
    with tab2:
        st.code(sql, language="sql")
    with tab3:
        st.caption(f"{len(df)} rows • showing up to {min(len(df), agents.ROW_LIMIT)}")
        if len(df) > 0:
            st.dataframe(df.head(agents.ROW_LIMIT), use_container_width=True)
            c1, c2 = st.columns(2)
            with c1:
                st.download_button(
                    "Download CSV",
                    df.to_csv(index=False).encode("utf-8"),
                    file_name="query_result.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            with c2:
                st.download_button(
                    "Download JSON",
                    df.to_json(orient="records", date_format="iso"),
                    file_name="query_result.json",
                    mime="application/json",
                    use_container_width=True,
                )
        else:
            st.info("No table data for this query type.")

    with tab4:
        # Show API response JSON for predictions, otherwise show dataframe JSON
        if predict_json is not None:
            preview_json = json.dumps(predict_json, indent=2, ensure_ascii=False)
        elif len(df) > 0:
            preview_json = df.head(agents.ROW_LIMIT).to_json(orient="records", date_format="iso", indent=2)
        else:
            preview_json = "{}"
        st.code(preview_json, language="json")