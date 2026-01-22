from langchain_google_genai import ChatGoogleGenerativeAI
from .em_selection import select_em_cpt, ALLOWED_EM_CODES
from .utils import is_holiday
from .extractors import extract_cpt_codes
from .models import TopLevelCategory, SOAPCategoryPrediction, CPTSelection
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
categories_prediction_llm = llm.with_structured_output(SOAPCategoryPrediction)
cpt_selection_llm = llm.with_structured_output(CPTSelection)


CATEGORIES_PREDICTION_PROMPT = """
You are a medical coding classification system.

Your task is to identify which TOP-LEVEL CPT CATEGORIES are clearly and
explicitly supported by the SOAP note.

You must ONLY choose from the allowed categories listed below.
Do NOT invent new categories.
Do NOT infer or assume.
If a category is not explicitly billable based on the documentation,
do NOT include it.

Allowed top-level categories:
{allowed_categories}

STRICT DEFINITIONS (follow exactly):

1. Office and Patient Visits
- Include ONLY if a patient encounter occurred AND a clinical evaluation was performed.
- Presence of Subjective, Objective, Assessment, and Plan counts as a visit.

2. Procedures
- Include ONLY if a procedure was actually performed during the encounter.
- Examples: incision, injection, nebulization administered in-office, imaging performed in-office.
- Do NOT include for:
  - laboratory tests
  - orders, referrals, or prescriptions
  - imaging or procedures that were only ordered

3. Laboratory and Diagnostic Tests
- Include ONLY if a lab or diagnostic test was performed and resulted.
- Examples: rapid flu, RSV, COVID tests with results.
- Do NOT include if the test was only ordered.

4. Vaccines and Immunizations
- Include ONLY if vaccines were administered during the visit.
- Do NOT include if vaccines were discussed, planned, or deferred.

5. Nutrition and Counseling
- Include ONLY if billable counseling or nutrition therapy was provided.
- Must involve documented counseling beyond routine advice.
- Examples: obesity counseling, nutrition therapy, time-based counseling.
- Do NOT include for:
  - routine patient education
  - reassurance, supportive care, anticipatory guidance
  - general discussion of illness or home care

6. Medications and Injectable Drugs
- Include ONLY if medications or injections were administered in-office.
- Do NOT include if medications were only prescribed or listed as home meds.

7. Administrative and Billing
- Include ONLY if administrative or billing services were performed.
- Examples: after-hours services (99051), reporting, billing modifiers.
- Do NOT include for routine visit documentation alone.

SOAP note:
\"\"\"
{soap_note}
\"\"\"

Return output strictly as valid JSON matching the provided schema.
- Do NOT include explanations
- Do NOT include extra keys
- Do NOT include categories not in the allowed list
"""


CPT_SELECTION_PROMPT = """
You are a CPT medical coding system.

Your task is to determine the EXACT CPT CODES to bill for THIS ENCOUNTER ONLY
based strictly on what was performed, administered, or evaluated on the date of service.

You MUST select only from the allowed CPT list provided.
Do NOT guess.
Do NOT invent codes.
If documentation is ambiguous or incomplete, DO NOT select the CPT.

SOAP note:
{soap_note}

Allowed CPT codes:
{allowed_cpts}

CPT codes already appearing in SOAP (consider as likely candidates, include only if rules are met):
{referenced_cpts}

CRITICAL RULES (must follow):

1. TEMPORAL RULES
- Do NOT select CPTs for prior visits, historical tests, or past dates.
- Do NOT select labs or diagnostic CPTs that are:
  - pending
  - planned
  - ordered but not resulted during this encounter

2. PROCEDURES
- Select procedure CPTs ONLY if the procedure was actually performed and completed during this visit.


3. MEDICATIONS
- Continuing existing medications alone does NOT justify higher E/M.
- Prescription changes or new medications must be explicitly documented.

4. ADMINISTRATIVE / SCREENING CODES
- Select ONLY if explicitly documented as performed during this encounter.
- Do NOT select based on assumptions or general discussion.

OUTPUT RULES:
- Return ONLY valid JSON.
- Do NOT include explanations.
- Do NOT include CPTs not in the allowed list.
- Do NOT include CPTs unless ALL criteria for that CPT are fully met.

Return JSON:
{{
  "selected_cpt_codes": [
    {{ "cpt": "12345", "description": "Example Description" }}
  ]
}}
"""


def build_categories_prompt(soap_note: str) -> str:
    from langchain_core.prompts import PromptTemplate

    allowed_categories = [c.value for c in TopLevelCategory]

    prompt_template = PromptTemplate(
        input_variables=["soap_note", "allowed_categories"],
        template=CATEGORIES_PREDICTION_PROMPT,
    )

    return prompt_template.format(
        soap_note=soap_note, allowed_categories="\n- " + "\n- ".join(allowed_categories)
    )


def serialize_cpt_tree(tree: dict, indent: int = 0) -> str:
    result = []
    prefix = "  " * indent
    for k, v in tree.items():
        result.append(f"{prefix}{k}")
        if isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    code = item.get("CPT")
                    desc = item.get("Description", "")
                    result.append(f"{prefix}  {code} - {desc}")
        elif isinstance(v, dict):
            result.append(serialize_cpt_tree(v, indent + 1))
    return "\n".join(result)


def build_cpt_selection_prompt(
    soap_note: str, allowed_subtree: Dict, referenced_cpts: List[str]
) -> str:
    from langchain_core.prompts import PromptTemplate

    allowed_subtree_str = serialize_cpt_tree(allowed_subtree)

    return PromptTemplate(
        input_variables=["soap_note", "allowed_cpts", "referenced_cpts"],
        template=CPT_SELECTION_PROMPT,
    ).format(
        soap_note=soap_note,
        allowed_cpts=allowed_subtree_str,
        referenced_cpts="\n".join(referenced_cpts or []),
    )


def select_cpts(
    masked_text: str,
    predicted_categories: list[str],
    normalized_mapping: dict,
    service_date: str,
) -> list[str]:
    # Extract allowed CPT subtree
    extracted_tree = {
        cat: normalized_mapping[cat]
        for cat in predicted_categories
        if cat in normalized_mapping
    }
    if not extracted_tree:
        return []

    referenced_cpts = extract_cpt_codes(masked_text)
    selected = []

    try:
        cpt_prompt = build_cpt_selection_prompt(
            masked_text, extracted_tree, referenced_cpts
        )
        results_obj = cpt_selection_llm.invoke(cpt_prompt)
        selected = [
            item["cpt"] for item in results_obj.selected_cpt_codes if "cpt" in item
        ]

        if TopLevelCategory.OFFICE_AND_PATIENT_VISITS.value.lower() in predicted_categories:
            em_code = select_em_cpt(masked_text, ALLOWED_EM_CODES)
            if em_code:
                selected.append(em_code)

        if is_holiday(service_date) and "99051" not in selected:
            selected.append("99051")
    except Exception as e:
        print(f"Error during CPT selection: {e}")

    return selected