from pathlib import Path
import PyPDF2
import pypdfium2 as pdfium
import pytesseract
from .utils import normalize_text, mask_phi
from .extractors import extract_patient_demographics
import io

def perform_ocr_on_pdf(pdf_path, dpi=300, tesseract_cmd=None):
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    pdf = pdfium.PdfDocument(pdf_path)
    text_pages = []
    scale = dpi / 72

    for page in pdf:
        bitmap = page.render(scale=scale)
        img = bitmap.to_pil()
        text_pages.append(pytesseract.image_to_string(img, config="--psm 6"))

    return "\n".join(text_pages)


def read_pdf_text(file):
    """Read PDF text using PyPDF2 first, fallback to OCR if empty"""
    # Handle file path or file-like object
    if isinstance(file, (str, Path)):
        f = open(file, "rb")
        close_file = True
    else:
        f = file if hasattr(file, "read") else io.BytesIO(file)
        close_file = False

    # Attempt text extraction via PyPDF2
    try:
        reader = PyPDF2.PdfReader(f)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception:
        text = ""

    if close_file:
        f.close()

    # Fallback to OCR if PyPDF2 failed or text is empty
    if not text.strip():
        text = perform_ocr_on_pdf(file)

    # Normalize, mask PHI, extract demographics
    normalized_text = normalize_text(text)
    masked_text = mask_phi(normalized_text)
    demographics = extract_patient_demographics(normalized_text)

    return masked_text, demographics