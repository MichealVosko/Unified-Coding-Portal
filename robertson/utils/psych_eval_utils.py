# utils/psych_eval_utils.py
import math
import re
from robertson.utils.phi_utils import get_phi


def extract_total_time(note_text: str) -> int:
    match = re.search(
        r"Total Time Spent\s*[:\-]?\s*(\d+)\s*minutes?", note_text, re.IGNORECASE
    )
    if match:
        return int(match.group(1))
    return 0


def count_procedures(note_text: str) -> int:
    procedures_match = re.search(
        r"Procedures\s*(.*?)(?:Total Time Spent|Diagnosis|$)",
        note_text,
        re.DOTALL | re.IGNORECASE,
    )
    if not procedures_match:
        return 0
    procedures_text = re.sub(r"([a-zA-Z])(\d+)", r"\1 \2", procedures_match.group(1))
    matches = re.findall(r"\b\d+\s*minutes?\b", procedures_text, re.IGNORECASE)
    return len(matches)


def contains_psychometrist(note_text: str) -> bool:
    procedures_match = re.search(
        r"Procedures\s*(.*?)(?:Total Time Spent|Diagnosis|$)",
        note_text,
        re.DOTALL | re.IGNORECASE,
    )
    if not procedures_match:
        return False
    return bool(
        re.search(
            r"\b(administration by )?psychometrist\b",
            procedures_match.group(1),
            re.IGNORECASE,
        )
    )


def calculate_code_units(code, time):
    def custom_round(value: float) -> int:
        fractional = value - math.floor(value)
        return math.ceil(value) if fractional > 0.5 else math.floor(value)

    if code == "96139":
        return custom_round(time / 30)
    elif code == "96131":
        return custom_round(time / 60)
    else:
        return 1


def extract_psych_eval_data(text: str) -> dict:
    phi_data = get_phi(text)
    service_code = phi_data.get("Service Code", "")
    diagnosis_codes = phi_data.get("Diagnosis Codes")
    total_time = extract_total_time(text)
    procedure_count = count_procedures(text)
    by_psychometrist = contains_psychometrist(text)
    code_units = calculate_code_units(service_code, total_time)

    return {
        "Service Code": service_code,
        "Total Time Spent": total_time,
        "Procedures": procedure_count,
        "Diagnosis Codes": diagnosis_codes,
        "By Psychometrist": "Yes" if by_psychometrist else "No",
        "Follow up code Units": code_units,
    }
