import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import google.generativeai as genai
import os
import uuid
import json
# Import document generator without causing circular import
from document_generated import generate_proposal_document

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

    # Add retry logic for embedding creation
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
            vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
            vector_store.save_local(folder_path)
            
            metadata = {"doc_name": doc_name, "folder": folder_id}
            with open(os.path.join(folder_path, "metadata.json"), "w") as f:
                json.dump(metadata, f)
                
            return folder_id
        
        except Exception as e:
            if attempt < max_retries - 1:
                import time
                print(f"Embedding attempt {attempt+1} failed: {str(e)}. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print(f"Failed to create embeddings after {max_retries} attempts: {str(e)}")
                raise

@st.cache_resource
def load_vector_store(folder_name):
    """Loads vector store with Streamlit resource caching."""
    # Add retry logic for loading vector store
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
            return FAISS.load_local(os.path.join("faiss_index", folder_name), embeddings, allow_dangerous_deserialization=True)
        except Exception as e:
            if attempt < max_retries - 1:
                import time
                print(f"Vector store loading attempt {attempt+1} failed: {str(e)}. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print(f"Failed to load vector store after {max_retries} attempts: {str(e)}")
                raise

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
    # Add retry logic for answering questions
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            vector_store = load_vector_store(folder_name)
            docs = vector_store.similarity_search(user_question)
            chain = get_conversational_chain()
            response = chain({"input_documents": docs, "question": user_question}, return_only_outputs=True)
            return response["output_text"]
        except Exception as e:
            if attempt < max_retries - 1:
                import time
                print(f"Question answering attempt {attempt+1} failed: {str(e)}. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print(f"Failed to answer question after {max_retries} attempts: {str(e)}")
                raise

# ======================== Document Generation Helper ========================

def get_rag_content(folder_name):
    """Gathers RAG content for document generation.
    
    This function queries the RAG system for specific content to be used
    in generating the proposal document.
    """
    rag_content = {}
    
    # Key questions to get content for the document
    queries = {
        'executive_summary': "What are the key highlights or executive summary of this proposal?",
        'approach': "What is the company's approach to solving the problem or delivering services?",
        'qualifications': "What are the company's qualifications and past performance?",
        'implementation': "What is the company's implementation plan?",
        'quality_control': "What quality control measures does the company have?"
    }
    
    # Get answers for each query
    for key, question in queries.items():
        try:
            # Add a timeout limit to prevent hanging
            import time
            start_time = time.time()
            max_timeout = 30  # 30 seconds max per query
            
            answer = answer_question(question, folder_name)
            
            # If we get a valid answer, add it to the content
            if answer and "not available in the context" not in answer:
                rag_content[key] = answer
                
        except Exception as e:
            # Log the error but continue with other queries
            print(f"Error getting RAG content for '{key}': {str(e)}")
            # Don't let one failure stop the document generation
            continue
    
    # If we couldn't get any RAG content, at least provide empty content
    if not rag_content:
        print("Warning: Could not retrieve any RAG content. Using fallback content.")
    
    return rag_content

# ======================== Streamlit App ========================

def main():
    st.set_page_config("RFP Assistant", layout="wide")
    st.title("📄 RFP Assistant")

    # Initialize tabs
    tabs = st.tabs(["Chat with RFP", "Generate Proposal Document"])
    
    chat_tab, document_tab = tabs
    
    # Sidebar (shared between tabs)
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
                    st.rerun()  # 🔁 Trigger rerun to update dropdown

    # Chat Tab Content
    with chat_tab:
        st.subheader("💬 Ask a Question")
        
        if selected_doc:
            user_question = st.text_input("Type your question below 👇", key="chat_question")

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
        else:
            st.info("Please upload and select a document to start chatting.")

    # Document Generation Tab Content
    with document_tab:
        st.subheader("📝 Generate Proposal Document")
        
        if selected_doc:
            st.markdown("""
            This feature allows you to create a professionally formatted proposal document using:
            1. Company data from data.csv
            2. Content from the selected RFP document
            """)

            output_filename = st.text_input("Output filename (without extension)", 
                                           value=f"proposal_{selected_doc[0]}")
            
            if st.button("Generate Document"):
                with st.spinner("Generating document..."):
                    try:
                        _, folder_name = selected_doc
                        
                        # Show a progress indicator
                        progress_bar = st.progress(0)
                        progress_text = st.empty()
                        
                        # Step 1: Preparing RAG content
                        progress_text.text("Step 1/3: Gathering content from document...")
                        progress_bar.progress(20)
                        
                        # Try to get RAG content, but proceed even if it fails
                        try:
                            rag_content = get_rag_content(folder_name)
                            progress_bar.progress(40)
                            if not rag_content:
                                st.warning("Could not extract content from the document. Using default content.")
                        except Exception as e:
                            st.warning(f"Could not extract content from the document due to an error: {str(e)}. Using default content.")
                            rag_content = {}
                            progress_bar.progress(40)
                        
                        # Step 2: Generating document
                        progress_text.text("Step 2/3: Creating document...")
                        progress_bar.progress(60)
                        
                        # Generate the document using the restructured approach
                        output_path = generate_proposal_document(
                            folder_name=folder_name, 
                            get_rag_content_func=lambda x: rag_content,  # Use already fetched content
                            output_path=f"{output_filename}.docx"
                        )
                        
                        # Step 3: Finalizing
                        progress_text.text("Step 3/3: Finalizing document...")
                        progress_bar.progress(80)
                        
                        # Provide download link
                        with open(output_path, "rb") as file:
                            file_data = file.read()
                        
                        progress_bar.progress(100)
                        progress_text.text("Document generation complete!")
                        
                        # Create download button
                        st.download_button(
                            label="Download Document",
                            data=file_data,
                            file_name=f"{output_filename}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        )
                        
                        st.success(f"Document generated successfully! Click the button above to download.")
                    except Exception as e:
                        st.error(f"Error generating document: {str(e)}")
                        st.error("Please try again or contact support if the error persists.")
        else:
            st.info("Please upload and select a document to generate a proposal.")

if __name__ == "__main__":
    main()