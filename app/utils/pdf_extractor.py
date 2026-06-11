"""
app/utils/pdf_extractor.py — PDF text extraction using PyMuPDF.
"""

import fitz  # PyMuPDF


def extract_text(file_bytes: bytes) -> str:
    """
    Extract text from a PDF byte stream.

    Parameters
    ----------
    file_bytes : bytes
        Raw bytes of the PDF file.

    Returns
    -------
    str
        Concatenated text from all pages.

    Raises
    ------
    ValueError
        If no text could be extracted from the PDF.
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()

    if not text.strip():
        raise ValueError("Could not extract text from PDF")

    return text
