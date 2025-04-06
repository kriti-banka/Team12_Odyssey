from langchain.text_splitter import RecursiveCharacterTextSplitter

# You can adjust these depending on your model limits
MAX_TOKENS = 1500  # Keep well below Groq's limit (~6000)

def chunk_text(text: str, chunk_size=MAX_TOKENS, chunk_overlap=100) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " "],
    )
    return splitter.split_text(text)