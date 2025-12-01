import re
import math
from langchain_core.prompts import PromptTemplate
from robertson.models.llm import structured_llm

cpt_prediction_prompt = """You are a medical coding assistant.
Assign the correct CPT code(s) from the allowed list below, based on the clinical note.
Do not guess codes that are not in the list.

Allowed CPTs:
- 90791: Psychiatric diagnostic evaluation
- 90832: Psychotherapy, 30 minutes with patient
- 90834: Psychotherapy, 45 minutes with patient
- 90837: Psychotherapy, 60 minutes with patient
- H0004: Behavioral health counseling and therapy, per 15 minutes
- 96130: Psychological testing evaluation services, first hour
- 96131: Psychological testing evaluation services, each additional hour
- 90839: Psychotherapy for crisis; first 60 minutes (Time range: 30–74 minutes)


Examples:
Note: "Patient presented for initial psychiatric diagnostic interview..." → CPT: 90791
Note: "Session lasted 60 minutes, focused on psychotherapy..." → CPT: 90837
Note: "Behavioral therapy session lasted 15 minutes..." → CPT: H0004
Note: "Patient in acute crisis, session lasted 45 minutes addressing suicidal ideation..." → CPT: 90839


Now classify the following clinical note and return the result in the specified JSON format:
{soap_note}

Return the result in this JSON format:
{{
  "CPT": [ "code1", "code2" ]
}}
"""


def predict_cpt_code(soap_note: str):
    prompt = PromptTemplate(
        input_variables=["soap_note"], template=cpt_prediction_prompt
    )
    soap_note_prompt = prompt.format(soap_note=soap_note)
    response = structured_llm.invoke(soap_note_prompt)
    return response.CPT


def calculate_cpt_units(predicted_cpts, duration_str):
    """
    Returns a list of CPTs with units where applicable.
    Handles H0004 and 90839/90840 logic.
    """
    cpt_with_units = []

    # Extract numeric duration in minutes if available
    duration_min = None
    if duration_str:
        match = re.search(r"(\d+)", duration_str)
        if match:
            duration_min = int(match.group(1))

    for cpt in predicted_cpts:
        # Default: just add the code
        entry = cpt

        # H0004: units based on duration
        if cpt == "H0004" and duration_min is not None:
            units = math.ceil(duration_min / 15)
            entry = f"{cpt} x{units}"

        cpt_with_units.append(entry)

        # 90839/90840 logic
        if cpt == "90839" and duration_min is not None:
            # Always add 90839
            entry_90839 = "90839"
            if entry_90839 not in cpt_with_units:
                cpt_with_units.append(entry_90839)

            # Calculate extra units for 90840
            extra_minutes = max(
                0, duration_min - 53
            )  # base threshold for initial session
            if extra_minutes > 0:
                extra_units = math.ceil(extra_minutes / 30)
                cpt_with_units.append(f"90840 x{extra_units}")

    return cpt_with_units


def sort_diagnosis_codes(codes):
    # F-codes first (e.g., F33.1), everything else after
    return sorted(codes, key=lambda c: 0 if c.strip().upper().startswith("F") else 1)
