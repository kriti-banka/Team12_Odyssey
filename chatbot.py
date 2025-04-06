import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain.vectorstores import FAISS
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import google.generativeai as genai
import os
import uuid
import json

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# ======================== PDF & Text Functions ========================
def get_pdf_text(pdf_docs):
    """Extracts and concatenates text from a list of uploaded PDFs."""
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
    return text

def get_text_chunks(text):
    """Splits long text into smaller overlapping chunks."""
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    return text_splitter.split_text(text)

# ======================== Vector Store Functions ========================
def save_vector_store(text_chunks, doc_name):
    """Creates and saves FAISS vector store with metadata."""
    folder_id = f"{doc_name}_{uuid.uuid4().hex[:6]}"
    folder_path = os.path.join("faiss_index", folder_id)
    os.makedirs(folder_path, exist_ok=True)

    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    vector_store.save_local(folder_path)

    metadata = {"doc_name": doc_name, "folder": folder_id}
    with open(os.path.join(folder_path, "metadata.json"), "w") as f:
        json.dump(metadata, f)

    return folder_id

@st.cache_resource
def load_vector_store(folder_name):
    """Loads vector store with Streamlit resource caching."""
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    return FAISS.load_local(os.path.join("faiss_index", folder_name), embeddings, allow_dangerous_deserialization=True)

def list_processed_documents():
    """Lists available processed documents with their metadata."""
    base_path = "faiss_index"
    if not os.path.exists(base_path):
        return []
    docs = []
    for name in os.listdir(base_path):
        path = os.path.join(base_path, name)
        metadata_path = os.path.join(path, "metadata.json")
        if os.path.isdir(path) and os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
                docs.append((metadata["doc_name"], name))
    return docs

# ======================== QA Chain Setup ========================
def get_conversational_chain():
    """Initializes the prompt + LLM chain for QA."""
    prompt_template = """
    Answer the question as detailed as possible from the provided context. If the answer is not in
    the provided context, just say "Answer is not available in the context." Do not make up answers.

    Context:
    {context}

    Question: {question}

    Answer:
    """
    model = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.3)
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    return load_qa_chain(model, chain_type="stuff", prompt=prompt)

def answer_question(user_question, folder_name):
    """Fetches relevant docs and returns model-generated answer."""
    vector_store = load_vector_store(folder_name)
    docs = vector_store.similarity_search(user_question)
    chain = get_conversational_chain()
    response = chain({"input_documents": docs, "question": user_question}, return_only_outputs=True)
    return response["output_text"]

# ======================== Streamlit App ========================
def main():
    # st.set_page_config("Chat with RFP", layout="wide")
    # st.title("📄 Chat with RFP Document")

    # Sidebar for document management
    with st.sidebar:
        st.header("📁 Manage Documents")
        available_docs = list_processed_documents()
        selected_doc = st.selectbox(
            "Select a processed document:",
            options=available_docs,
            format_func=lambda x: x[0]
        )
        st.markdown("---")
        pdf_docs = st.file_uploader("Upload your PDF(s)", accept_multiple_files=True)
        if st.button("Submit & Process"):
            if pdf_docs:
                with st.spinner("Processing..."):
                    text = get_pdf_text(pdf_docs)
                    chunks = get_text_chunks(text)
                    name = os.path.splitext(pdf_docs[0].name)[0].replace(" ", "_")
                    save_vector_store(chunks, name)
                    st.success(f"'{name}' processed and saved!")
                    st.rerun()  # Trigger rerun to update dropdown

    # QA Section
    if selected_doc:
        st.subheader("💬 Ask a Question")
        user_question = st.text_input("Type your question below 👇")
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        if user_question:
            with st.spinner("Generating answer..."):
                _, folder_name = selected_doc
                answer = answer_question(user_question, folder_name)
                st.session_state.chat_history.append((user_question, answer))
        for q, a in st.session_state.chat_history:
            st.markdown(f"**Q:** {q}")
            st.markdown(f"**A:** {a}")

    # (Optional) Bottom-right button can be added here as well if needed.
    st.markdown("""
        <style>
        .bottom-right-button {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 100;
        }
        </style>
    """, unsafe_allow_html=True)
    with st.container():
        if st.button("Refresh Page", key="chat_refresh"):
            st.markdown(
                "<script>window.location.reload();</script>",
                unsafe_allow_html=True
            )

if __name__ == "__main__":
    main()
