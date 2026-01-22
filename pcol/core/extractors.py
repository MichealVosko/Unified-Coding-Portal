import re
from typing import Dict, List

from .utils import normalize_text

def extract_single(pattern: str, text: str) -> str | None:
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1).strip() if m else None


def extract_patient_name(text: str) -> str | None:
    m = re.search(
        r"^([A-Z][A-Z\s\-']+,\s*[A-Za-z][A-Za-z\s\-']+)",
        text,
        re.MULTILINE,
    )
    if m:
        return m.group(1).strip()

    # Fallback Patient field
    m = re.search(
        r"Patient:\s*([A-Za-z ,]+?)(?:\s+Provider:|\s+DOB:)",
        text,
        re.IGNORECASE,
    )
    return m.group(1).strip() if m else None


def extract_dob(text: str) -> str | None:
    return extract_single(r"DOB:\s*(\d{2}/\d{2}/\d{4})", text)


def extract_dos(text: str) -> str | None:
    return extract_single(r"DOS:\s*(\d{2}/\d{2}/\d{4})", text)


def extract_age(text: str) -> str | None:
    m = re.search(
        r"(?:\(|Age:\s*)(\d+\s*(?:yo|mo|wo|y))",
        text,
        re.IGNORECASE,
    )
    return m.group(1) if m else None


def extract_account_number(text: str) -> str | None:
    return extract_single(r"Acc(?:ount)?\s*No\.?\s*(\d+)", text)


def extract_provider(text: str) -> str | None:
    return extract_single(r"Provider:\s*([A-Za-z ,\.]+MD)", text)


def extract_icd_codes(text: str) -> List[str]:
    return sorted(
        set(
            re.findall(
                r"\b[A-Z]\d{2}(?:\.\d{1,4})?\b",
                text,
            )
        )
    )


def extract_cpt_codes(text: str) -> List[str]:
    m = re.search(
        r"Procedure Codes:(.*?)(?:Preventive Medicine:|Provider:|$)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if not m:
        return []

    block = m.group(1)
    return sorted(set(re.findall(r"\b\d{5}\b", block)))


def extract_testing_log(text: str) -> List[Dict[str, str]]:
    results = []

    for test, result in re.findall(
        r"\b(Flu A|Flu B|Covid-19)\s+(POSITIVE|NEGATIVE)\b", text, re.IGNORECASE
    ):
        results.append({"test": test, "result": result.upper()})

    return results


def extract_patient_demographics(text: str) -> Dict:
    text = normalize_text(text)
    name = extract_patient_name(text)

    return {
        "patient_name": name.split("DOB")[0].strip() if name else None,
        "dob": extract_dob(text),
        "age": extract_age(text),
        "service_date": extract_dos(text),
        "account_number": extract_account_number(text),
        "provider_name": extract_provider(text),
        "testing_log": extract_testing_log(text),
        "cpt_codes": extract_cpt_codes(text),
        "icd_codes": extract_icd_codes(text),
    }
