import json
import fitz  # PyMuPDF
import docx
from pathlib import Path
from typing import Union


def load_json(file_path: Union[str, Path]) -> dict:
    """
    Load and return JSON data from a file.
    """
    with open(file_path, 'r') as f:
        return json.load(f)


def parse_docx(file_path: Union[str, Path]) -> str:
    """
    Parse and return text content from a DOCX file.
    """
    doc = docx.Document(file_path)
    return "\n".join([para.text.strip() for para in doc.paragraphs if para.text.strip()])


def parse_pdf(file_path: Union[str, Path]) -> str:
    """
    Extract and return text from a PDF file using PyMuPDF.
    """
    doc = fitz.open(file_path)
    return "\n".join([page.get_text() for page in doc])


def parse_file(file_path: Union[str, Path]) -> str:
    """
    Detect and parse DOCX or PDF based on file extension.
    """
    ext = Path(file_path).suffix.lower()
    if ext == ".docx":
        return parse_docx(file_path)
    elif ext == ".pdf":
        return parse_pdf(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}")
