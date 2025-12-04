import re


def extract_dos(text):
    pattern = r"Date and[^\d]*(\d{1,2}/\d{1,2}/\d{4})"
    matches = re.findall(pattern, text)
    return matches[0] if matches else None


def extract_clinician(text):
    pattern = r"Clinician\s*[:\-]\s*([A-Za-z\s]+(?:, [A-Za-z\s]+)*)"
    match = re.search(pattern, text)
    if match:
        return match.group(1).split(",")[0].strip()
    return None


def extract_supervisor(text):
    pattern = r"Supervisor\s*[:\-]\s*([A-Za-z\s]+(?:, [A-Za-z\s]+)*)"
    match = re.search(pattern, text)
    if match:
        return match.group(1).split(",")[0].strip()
    return None


def extract_patient(text):
    pattern = r"Patient\s*[:\-]\s*([A-Za-z\s]+)"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None


def extract_dob(text):
    pattern = r"DOB\s*[:\-]?\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None


def extract_duration(text):
    pattern = r"Duration\s*[:\-]\s*([0-9]+ ?minutes)"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None


def extract_service_code(text):
    pattern = r"Service Code\s*[:\-]\s*(\d{5})"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None


def extract_location(text):
    pattern = r"Location\s*[:\-]\s*([A-Za-z0-9\s\-]+)"
    match = re.search(pattern, text)
    return match.group(1).split("\n")[0].strip() if match else None


def extract_participants(text):
    pattern = r"Participants\s*[:\-]\s*([A-Za-z\s;]+)"
    match = re.search(pattern, text)
    return match.group(1).split("\n")[0].strip() if match else None


def extract_diagnosis(text):
    pattern = r"Diagnosis\s*[:\n]\s*([A-Z]\d{2}(?:\.\d+)?(?: [A-Za-z ,]+)?)"
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(1).strip() if match else None


def extract_icds(text):
    icd_pattern = r"\b[A-Z]\d{2}(?:\.\d+)?\b"
    icds = re.findall(icd_pattern, text)

    unique_icds = list(dict.fromkeys(icds))

    return ", ".join(unique_icds)


def apply_pos(location):
    loc = location.strip().lower()
    if "telehealth" in loc:
        return {"POS": 10, "MODIFIER": 95}
    return {"POS": None, "MODIFIER": None}


def extract_session_info(text):
    location = extract_location(text)
    pos_info = apply_pos(location)
    pos, modifier = pos_info["POS"], pos_info["MODIFIER"]

    service_code = extract_service_code(text)
    diagnosis = extract_diagnosis(text)
    icds = extract_icds(diagnosis)
    return {
        "Date": extract_dos(text),
        "Patient": extract_patient(text),
        "DOB": extract_dob(text),
        "Service Code": service_code,
        "Diagnosis": icds,
        "Clinician": extract_clinician(text),
        "Coding": f"{service_code}--{modifier if modifier else ''}--{icds}",
        "Status": "On Hold",
        # "Supervisor": extract_supervisor(text),
        # "Duration": extract_duration(text),
        # "Location": location,
        # "Participants": extract_participants(text),
        "POS": pos,
        "Modifier": modifier,
        "Comments": "",
    }
