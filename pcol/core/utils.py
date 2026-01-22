import re
from datetime import datetime
import holidays


def normalize_text(text: str) -> str:
    text = text.replace("\u2013", "-")
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ ]{2,}", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def mask_phi(text: str) -> str:
    # Mask patient names (assumes "LAST, First" or "Patient: First Last")
    text = re.sub(
        r"^([A-Z][A-Z\s\-']+,\s*[A-Za-z][A-Za-z\s\-']+)",
        "[PATIENT_NAME]",
        text,
        flags=re.MULTILINE,
    )
    text = re.sub(
        r"Patient:\s*([A-Za-z ,]+?)(?:\s+Provider:|\s+DOB:)",
        "Patient: [PATIENT_NAME]",
        text,
        flags=re.IGNORECASE,
    )

    # Mask DOB
    text = re.sub(r"\bDOB:\s*\d{1,2}/\d{1,2}/\d{2,4}\b", "DOB: [DOB]", text)

    # Mask age
    text = re.sub(
        r"Age:\s*\d+\s*(?:mo|yo|y|d)", "Age: [AGE]", text, flags=re.IGNORECASE
    )

    # Mask account numbers / MRN
    text = re.sub(r"\bAcc No\.:?\s*\d+\b", "Acc No.: [ACCOUNT_NUMBER]", text)

    # Mask provider names
    text = re.sub(r"Provider:\s*[A-Za-z ,\.]+MD", "Provider: [PROVIDER]", text)

    # Mask phone numbers
    text = re.sub(r"\b\d{3}-\d{3}-\d{4}\b", "[PHONE]", text)

    # Mask addresses
    text = re.sub(
        r"\d{1,5}\s+[A-Za-z0-9\s,.-]+, [A-Za-z\s]+, [A-Z]{2}-\d{5}", "[ADDRESS]", text
    )

    # Mask dates (service dates, visit dates, etc.)
    text = re.sub(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", "[DATE]", text)

    # Mask URLs
    text = re.sub(r"https?://\S+", "[URL]", text)

    return text

def normalize_excel_cpts(cpt_string: str) -> list[str]:
    if not isinstance(cpt_string, str):
        return []
    return [
        re.match(r"(\d{5})", line.strip()).group(1)
        for line in cpt_string.splitlines()
        if re.match(r"(\d{5})", line.strip())
    ]


def norm(s: str) -> str:
    return s.strip().lower()


def is_holiday(dos_str: str) -> bool:
    dos_date = datetime.strptime(dos_str, "%m/%d/%Y").date()
    us_holidays = holidays.US(years=dos_date.year)

    return dos_date in us_holidays

