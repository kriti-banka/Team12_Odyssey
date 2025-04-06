import streamlit as st
from pathlib import Path
from openai import RateLimitError


from utility.fileparser import parse_file, load_json
from utility.chunker import chunk_text
from utility.feedback_logger import log_feedback  # New

from agents import checklist, requirements, risk_analysis_agent, summary, verdict
from chatbot import main as chatbot_main_raw
from generate_doc_ui import get_rag_content, list_processed_documents, answer_question
from document_generated import generate_proposal_document
# Setup
st.set_page_config(page_title="RFP Assistant", layout="wide")
company_data = load_json("json/company_data.json")

# Initialize session state for tab
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "Analyzer"

# Tab buttons (simulate tabs with radio)
tab_selection = st.radio("Choose Tool", ["📊 RFP Analyzer", "💬 Chatbot", "📝 Proposal Generator"], horizontal=True)


# Update tab state
if tab_selection == "📊 RFP Analyzer":
    st.session_state.active_tab = "Analyzer"
elif tab_selection == "💬 Chatbot":
    st.session_state.active_tab = "Chatbot"
elif tab_selection == "📝 Proposal Generator":
    st.session_state.active_tab = "Generator"

# ---------------- Sidebar ----------------
with st.sidebar:
    if st.session_state.active_tab == "Analyzer":
        st.markdown("### 📂 RFP Analyzer Tools")
        uploaded_file = st.file_uploader("Upload an RFP PDF", type=["pdf"], key="analyzer_file")
        if uploaded_file:
            run_type = st.radio("Run Agent:", [
                "📌 Eligibility Verdict",
                "📋 Legal Terms Checklist",
                "📤 Submission Requirements",
                "📝 Summary",
                "⚠️ Risk Analysis"
            ])
        else:
            st.info("Upload a PDF to enable analysis tools.")
    elif st.session_state.active_tab == "Chatbot":
        st.markdown("### 💬 Chatbot Tools")
        st.markdown("Use natural language to chat with the uploaded RFP.")

# ---------------- Main Area ----------------
if st.session_state.active_tab == "Analyzer":
    st.title("⚡ Fast RFP Analyzer")
    chunks = []

    if "analyzer_file" in st.session_state and st.session_state.analyzer_file:
        uploaded_file = st.session_state.analyzer_file
        temp_path = Path(f"temp_{uploaded_file.name}")
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.read())

        rfp_text = parse_file(temp_path)
        chunks = chunk_text(rfp_text)

        def run_agent_single(agent, chunks, extra_inputs=None):
            """Run the agent on the full document instead of per-chunk to avoid multiple outputs."""
            full_doc = "\n\n".join(chunks)
            input_payload = {"document": full_doc}
            if extra_inputs:
                input_payload.update(extra_inputs)
            try:
                output = agent.invoke(input_payload)
                if hasattr(output, "content"):
                    return output.content
                elif isinstance(output, dict) and "text" in output:
                    return output["text"]
                else:
                    return str(output)
            except RateLimitError:
                st.error("🛑 Rate limit hit. Try again later.")
                return "Rate limit error."
            except Exception as e:
                st.error(f"Error running agent: {e}")
                return str(e)


        if run_type:
            st.subheader(run_type)
            with st.spinner("Running agent..."):
                if run_type == "📌 Eligibility Verdict":
                    result = run_agent_single(verdict.agent, chunks)
                #     result = verdict.agent.invoke({
                #     "document": chunk,
                #     "aggregated_json": json.dumps(aggregated_json)
                # })
                elif run_type == "📋 Legal Terms Checklist":
                    result = run_agent_single(checklist.agent, chunks)

                elif run_type == "📤 Submission Requirements":
                    result = run_agent_single(requirements.agent, chunks)

                elif run_type == "📝 Summary":
                    result = run_agent_single(summary.agent, chunks)

                elif run_type == "⚠️ Risk Analysis":
                    result = run_agent_single(
                        risk_analysis_agent.agent,
                        chunks,
                        extra_inputs={"company_data": company_data}
                    )
                else:
                    result = "Invalid selection"
            st.success("✅ Done!")
            st.write(result)

            # Feedback Section
            st.markdown("#### 🙋 Was this helpful?")
            col_up, col_down = st.columns(2)
            feedback_key = f"{run_type}_{uploaded_file.name}"

            if col_up.button("👍 Yes", key=feedback_key + "_up"):
                log_feedback(uploaded_file.name, run_type, result, "👍")
                st.success("Thanks for your feedback!")

            if col_down.button("👎 No", key=feedback_key + "_down"):
                st.warning("Please tell us what went wrong:")
                user_comment = st.text_area("Optional Feedback", key=feedback_key + "_text")
                if st.button("Submit Feedback", key=feedback_key + "_submit"):
                    log_feedback(uploaded_file.name, run_type, result, "👎", comment=user_comment)
                    st.success("Thanks — we'll use this to improve!")

elif st.session_state.active_tab == "Chatbot":
    st.title("💬 RFP Chatbot Assistant")
    chatbot_main_raw()

elif st.session_state.active_tab == "Generator":
    st.title("📝 Proposal Generator")

    available_docs = list_processed_documents()
    selected_doc = st.selectbox(
        "Select a processed RFP document",
        options=available_docs,
        format_func=lambda x: x[0],
        key="generator_selected"
    )

    if selected_doc:
        st.markdown("""
        This tool generates a fully formatted Word proposal document using:
        1. Company profile (CSV)
        2. Extracted RAG content from selected RFP
        """)

        output_filename = st.text_input("Output filename (without extension)",
                                        value=f"proposal_{selected_doc[0]}")
        
        if st.button("📄 Generate Proposal Document"):
            with st.spinner("Generating document..."):
                try:
                    _, folder_name = selected_doc

                    progress_bar = st.progress(0)
                    progress_text = st.empty()
                    progress_text.text("Step 1/3: Getting content from document...")
                    progress_bar.progress(20)

                    rag_content = get_rag_content(folder_name)
                    progress_bar.progress(50)

                    output_path = generate_proposal_document(
                        folder_name=folder_name,
                        get_rag_content_func=lambda x: rag_content,
                        output_path=f"{output_filename}.docx"
                    )

                    with open(output_path, "rb") as file:
                        file_data = file.read()

                    progress_text.text("Step 3/3: Finalizing...")
                    progress_bar.progress(100)

                    st.download_button(
                        label="⬇️ Download Proposal Document",
                        data=file_data,
                        file_name=f"{output_filename}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                    st.success("Proposal document generated successfully!")

                except Exception as e:
                    st.error(f"Error generating document: {e}")



