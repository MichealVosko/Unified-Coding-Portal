import re

required_sections = {
    "Interventions Used": r"\bInterventions\s+Used\b",
    # Match "Risk Assessment" OR "Assessment" optionally followed by
    # words, slashes, or spaces
    "Risk Assessment": r"\b(Risk\s+Assessment|Assessment(\s*[/\-\w\s]+)*)\b",
    "Current Mental Status": r"\bCurrent\s+Mental\s+Status\b",
}


def has_objectives_content(text):
    # Extract the content between 'Objectives' and the next section
    pattern = re.compile(
        r"Treatment\s*Plan\s*Progress.*?Objectives(.*?)(?:\n(?:Plan|Assessment|Additional\s*Notes)|$)",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        return False  # No objectives section at all

    # Extract content
    content = match.group(1).strip()

    # Check if it's non-empty
    return bool(content and len(content) > 10)


def check_note(note_text: str, filename: str):
    missing = [section for section in required_sections if section not in note_text]

    if not has_objectives_content(note_text):
        missing.append("Objectives")
    return {
        "filename": filename,
        "status": "RED" if missing else "OK",
        "missing_sections": missing,
    }


def check_biopsychosocial(note_text: str, min_words: int = 200) -> tuple[bool, str]:
    section_regex = r"\bBiopsychosocial\s+Assessment\b" 
    match = re.search(
        section_regex + r"(.*?)(?:\n(?:Plan|Assessment|Additional Notes)|$)",
        note_text,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return False, "missing"
    content = match.group(1).strip()
    word_count = len(content.split())
    if word_count < min_words:
        return False, "too short"
    return True, ""
    