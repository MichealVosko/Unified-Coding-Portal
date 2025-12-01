import re
from langchain_community.document_loaders import PyPDFLoader

def load_pdf(file_path: str) -> str:
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    return "\n".join([doc.page_content for doc in documents])

def deidentify_and_strip(text: str) -> str:
    cleaned_lines = []
    for line in text.splitlines():
        line_stripped = line.strip()
        if not line_stripped:
            continue
        if re.search(r"(Patient|Clinician|Participants|Supervisor?):", line_stripped, re.IGNORECASE):
            continue
        if re.search(r"DOB|Date and Time:", line_stripped, re.IGNORECASE):
            continue
        if re.search(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", line_stripped):  # dates
            continue
        if re.search(r"\d{1,2}:\d{2}\s?(AM|PM|am|pm)", line_stripped):
            continue
        if re.search(r"(Location|Clinic|Hospital|Center|LLC|LLP|PC)", line_stripped):
            continue
        if re.search(r"License|http|www|Page \d+ of \d+", line_stripped):
            continue
        cleaned_lines.append(line_stripped)
    return "\n".join(cleaned_lines)
