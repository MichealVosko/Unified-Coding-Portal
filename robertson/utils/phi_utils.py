import re
import math
from datetime import datetime


def format_date(date_str: str) -> str:
    date_formats = [
        "%m/%d/%Y",
        "%m-%d-%Y",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%B %d, %Y",
        "%b %d, %Y",
    ]
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%d-%m-%Y")
        except ValueError:
            continue
    return date_str


def split_date_time(datetime_str: str):
    parts = datetime_str.strip().split(" ", 1)
    if len(parts) == 2:
        return format_date(parts[0]), parts[1].strip()
    else:
        return format_date(datetime_str.strip()), ""


def get_phi(note_text: str) -> dict:
    details = {}

    clinician_match = re.search(r"Clinician:\s*(.+)", note_text)
    if clinician_match:
        details["Clinician"] = clinician_match.group(1).strip()

    # Supervisor
    supervisor_match = re.search(r"Supervisor:\s*(.+)", note_text)
    if supervisor_match:
        details["Supervisor"] = supervisor_match.group(1).strip()

    # Patient & DO
    patient_match = re.search(r"Patient:\s*([^,]+),\s*DOB\s*([^\n]+)", note_text)
    if patient_match:
        details["Patient"] = patient_match.group(1).strip()
        details["DOB"] = format_date(patient_match.group(2).strip())

    # Date & Time
    datetime_match = re.search(r"Date and Time:\s*([^\n]+)", note_text)
    if datetime_match:
        date_str, time_str = split_date_time(datetime_match.group(1))
        details["Date"] = date_str
        if time_str:
            details["Time"] = time_str

    # Duration
    duration_match = re.search(r"Duration:\s*([^\n]+)", note_text)
    if duration_match:
        details["Duration"] = duration_match.group(1).strip()

    # Service Code
    service_code_match = re.search(r"Service Code:\s*([A-Z0-9]+)", note_text)
    if service_code_match:
        details["Service Code"] = service_code_match.group(1).strip()

    # Diagnosis (ICD-10 extraction)
    diagnosis_section = None

    section_start = re.search(
        r"(Diagnosis|Diagnoses|Dx)[:\-]?", note_text, re.IGNORECASE
    )

    if section_start:
        diagnosis_section = note_text[section_start.start() :]
    stop_match = re.search(
        r"(Plan|Treatment|Intervention|Procedure|Assessment)[:\-]?",
        diagnosis_section,
        re.IGNORECASE,
    )

    if stop_match:
        diagnosis_section = diagnosis_section[: stop_match.start()]

    if diagnosis_section:
        diagnosis_section = re.sub(r"([0-9])([A-Z])", r"\1 \2", diagnosis_section)

        # Extract ICD-10 codes
        icd_pattern = r"([A-TV-Z][0-9]{2}(?:\.[0-9A-Z]{1,4})?)"
        diagnosis_codes = list(set(re.findall(icd_pattern, diagnosis_section)))

        # Optional: remove trailing letters if accidentally captured
        cleaned_codes = []
        for code in diagnosis_codes:
            if re.match(r".*[A-Z]$", code):
                code = code[:-1]
            cleaned_codes.append(code)
        details["Diagnosis Codes"] = list(set(cleaned_codes))[::-1]

    location_match = re.search(
        r"^Location[:\-]?\s*(.*)$", note_text, re.IGNORECASE | re.MULTILINE
    )

    if location_match:
        details["Location"] = location_match.group(1).strip()
    else:
        details["Location"] = ""

    # Map Location to POS/Modifier
    if re.search(r"telehealth|virtual|video", details["Location"], re.IGNORECASE):
        details["POS"] = "10"
        details["Modifier"] = "95"
    else:
        details["POS"] = "11"
        details["Modifier"] = ""

    return details


def ceilling_value(duration: str):
    print(type(duration))
    duration = int(duration.split()[0])
    return math.ceil(duration / 15)
