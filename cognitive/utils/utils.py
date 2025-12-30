import re
import pypdfium2 as pdfium
import pytesseract

from datetime import datetime
import pandas as pd
import PyPDF2

def load_pdf(uploaded_file):
    reader = PyPDF2.PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    
    if text.strip() == "":
        # Fallback to OCR
        text = ocr_pdf(uploaded_file)
    return text


def ocr_pdf(pdf_path, dpi=300, tesseract_cmd=None):
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

def extract_icd10_from_assessment(text: str) -> list:
    """
    Return a list of ICD-10 codes found in the Assessment section.
    Falls back to full-text scan if the Assessment block boundary can't be found cleanly.
    """

    start_match = re.search(r'(?mi)^\s*Assessment\s*$', text)
    if start_match:
        start = start_match.end()
        end_match = re.search(
            r'(?mi)^\s*(Plan|Orders|Medications(?:\s+attached.*)?|Screenings/.*|Observations|Quality of care|Care plan)\b.*$',
            text[start:]
        )
        if end_match:
            end = start + end_match.start()
            scope = text[start:end]
        else:
            scope = text[start:] 
    else:

        scope = text

    bracket_chunks = re.findall(r'\[ICD-10:\s*([^\]]+)\]', scope, flags=re.IGNORECASE)

    code_pattern = re.compile(r'\b[A-TV-Z][0-9]{2}[A-Z0-9]?(?:\.[A-Z0-9]{1,4})?\b', re.IGNORECASE)

    codes = []
    seen = set()
    for chunk in bracket_chunks:
        for code in code_pattern.findall(chunk):
            code = code.upper()
            if code not in seen:
                seen.add(code)
                codes.append(code)

    return codes

# def is_existing_patient(text: str) -> bool:
#     pattern = r"\bRETURN (?:FROM|FORM) INTAKE\b"
#     return bool(re.search(pattern, text, re.IGNORECASE))


def extract_section(text: str, start: str, end: str) -> str:
    pattern = re.compile(f"{start}(.*?){end}", re.IGNORECASE | re.DOTALL)
    m = pattern.search(text)
    return m.group(1) if m else ""

def has_dates(text: str) -> bool:
    date_pattern = r"\b(?:\d{1,2}/\d{1,2}/\d{2,4})\b"
    return bool(re.search(date_pattern, text))

def is_existing_patient(text: str) -> bool:
    text = clean_text(text)
    pattern = r"\bRETURN (?:FROM|FORM) INTAKE\b"
    if re.search(pattern, text, re.IGNORECASE):
        return True

    block = extract_section(text, "Social History", "Objective")
    if not block:
        return False
    return has_dates(block)


def extract_time_spent(text: str):
    """
    Detects if 'total time spent' is present (case-insensitive)
    and extracts time spent in minutes (integer).

    Returns:
        (bool, int or None)
    """
    if not isinstance(text, str):
        return False, None

    # Normalize
    t = text.lower()

    # Check phrase exists
    if "total time spent" not in t:
        return False, None

    # Regex to capture patterns like "15 minutes", "5 min", "30 mins"
    match = re.search(r"(\d+)\s*min(ute)?s?", t, flags=re.IGNORECASE)
    if match:
        minutes = int(match.group(1))
        return True, minutes

    return True, None

def clean_text(text: str) -> str:
    lines = []
    for line in text.splitlines():
        # skip URLs
        if line.startswith("http"):
            continue
        # skip encounter headers / timestamps
        if re.match(r"\d{1,2}/\d{1,2}/\d{2,4},?\s+\d{1,2}:\d{2}", line):
            continue
        lines.append(line)
    return "\n".join(lines)


def extract_patient_info(text: str) -> dict:
    data = {}

    # --- Extract Name ---
    name_match = re.search(
        r"Patient[:\s]+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+)(?=\s+DOB|\s+PRN|\s*$)",
        text
    )
    if not name_match:
        # Fallback: try FIRST + LAST NAME
        first = re.search(r"FIRST NAME\s+([A-Za-z]+)", text)
        last = re.search(r"LAST NAME\s+([A-Za-z]+)", text)
        if first and last:
            data["Patient Name"] = f"{first.group(1)} {last.group(1)}"
    else:
        data["Patient Name"] = name_match.group(1)


    # --- Extract DOB ---
    dob_match = re.search(r"(?:DOB|DATE OF BIRTH)[:\s]+(\d{2}/\d{2}/\d{4})", text)
    if dob_match:
        data["DOB"] = dob_match.group(1)

    # --- Extract DOS (Date of Service) ---
    dos_match = re.search(r"Date of service[:\s]+(\d{2}/\d{2}/\d{2,4})", text, re.IGNORECASE)
    if dos_match:
        raw_dos = dos_match.group(1)
        # Normalize to DD-MM-YY
        try:
            dt = datetime.strptime(raw_dos, "%m/%d/%y")  # e.g. 08/26/25
        except ValueError:
            dt = datetime.strptime(raw_dos, "%m/%d/%Y") # e.g. 08/26/2025
        data["DOS"] = dt.strftime("%d-%m-%y")

    # --- Extract Member ID ---
    member_id_match = re.search(r"INSURED ID NUMBER\s+([A-Z0-9]+)", text)
    if member_id_match:
        data["Member ID"] = member_id_match.group(1)

    # --- Extract Insurance Provider ---
    payer_match = re.search(r"PAYER\s+([A-Za-z0-9& ]+)", text)
    if payer_match:
        data["Insurance"] = payer_match.group(1).strip()
        data["Insurance"] = data["Insurance"].split("INSURED")[0].strip()
        
    data["ICD Codes"] = ", ".join(extract_icd10_from_assessment(text))
    
    data["CPT Codes"] = []
    if is_existing_patient(text):
        data["CPT Codes"].append("99214-GT")
    else:    
        data["CPT Codes"].append("99205-GT")

    if extract_time_spent(text)[0]:
        data["CPT Codes"].append("90833-GT")
    else:
        data["Comments"] = "Time spent not documented; please verify."
    data["CPT Codes"] = ", ".join(data["CPT Codes"])
    
    return data


def get_patient_df(patients_data):
    phi_df = pd.DataFrame(patients_data)
    
    phi_df.insert(0, "Facility Name", "Cognitive Works")
    return phi_df