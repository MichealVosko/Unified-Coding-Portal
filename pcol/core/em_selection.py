from langchain_google_genai import ChatGoogleGenerativeAI
from .utils import norm
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

ALLOWED_EM_CODES = [
    {"cpt": "99201", "description": "Office visit for a new patient, level 1"},
    {"cpt": "99202", "description": "Office visit for a new patient, level 2"},
    {"cpt": "99203", "description": "Office visit for a new patient, level 3"},
    {"cpt": "99204", "description": "Office visit for a new patient, level 4"},
    {"cpt": "99205", "description": "Office visit for a new patient, level 5"},
    {"cpt": "99211", "description": "Office visit for an established patient, level 1"},
    {"cpt": "99212", "description": "Office visit for an established patient, level 2"},
    {"cpt": "99213", "description": "Office visit for an established patient, level 3"},
    {"cpt": "99214", "description": "Office visit for an established patient, level 4"},
    {"cpt": "99215", "description": "Office visit for an established patient, level 5"},
]

class EMSelection(BaseModel):
    em_code: str = Field(
        ..., description="Selected E/M (Evaluation & Management) code for the encounter"
    )

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

em_llm = llm.with_structured_output(EMSelection)


EM_PROMPT_TEMPLATE = """
You are a professional medical coder.

Based on the SOAP note, select the SINGLE most appropriate CPT code
from the allowed Office Visit and Preventive Visit codes below.

────────────────────────
CPT SELECTION RULES
────────────────────────

1. WELL-CHILD/MINOR ACUTE VISITS:

- If this is a pediatric/well-child visit and the patient has only minor acute complaints (e.g., cough, congestion, sore throat, mild viral illness, medication refill), **always code 99213**.
- Do NOT escalate to 99214 or higher for minor complaints during a preventive or well-child visit.

2. LOW COMPLEXITY (99202, 99203, 99212, 99213):

- 99202: 1 self-limited or minor problem
- 99203/99212/99213: 2 or more self-limited or minor problems, or 1 stable chronic illness, or 1 acute uncomplicated illness or injury

3. MODERATE COMPLEXITY (99204, 99214):

- 1 acute illness with systemic symptoms
- OR 1 or more chronic problems with progression/exacerbation/adverse effects
- OR 2 or more stable chronic illnesses
- OR 1 undiagnosed new problem with uncertain prognosis
- OR 1 acute complicated injury or hospital/observation-level care

4. HIGH COMPLEXITY (99205, 99215):

- 1 or more chronic illnesses with severe progression/exacerbation/adverse effects
- OR 1 acute or chronic illness/injury that poses a threat to life or body function

5. DATA REVIEW & MDM:

- Ignore routine labs, vaccines, and medication refills unless they clearly affect MDM
- Use MDM rules only when documentation explicitly supports moderate/high complexity
- Prefer the lower code if documentation is borderline

────────────────────────
ADDITIONAL RULES
────────────────────────

- Minor acute complaints in well-child or preventive visits **must be coded 99213**, no matter the number of medications or lab mentions.
- Always select the lowest appropriate code if borderline.
- Output JSON ONLY, no explanation.
- Select ONE CPT code only.

────────────────────────
ALLOWED CPT CODES
────────────────────────
{allowed_em_cpts}

────────────────────────
SOAP NOTE
────────────────────────
\"\"\" 
{soap_note}
\"\"\" 
"""

def build_em_prompt(soap_note: str, allowed_em_codes: list[dict]) -> str:
    from langchain_core.prompts import PromptTemplate

    cpt_list = [f"{item['cpt']} - {item['description']}" for item in allowed_em_codes]

    prompt_template = PromptTemplate(
        input_variables=["soap_note", "allowed_em_cpts"],
        template=EM_PROMPT_TEMPLATE,
    )

    return prompt_template.format(
        soap_note=soap_note,
        allowed_em_cpts="\n".join(cpt_list),
    )


def select_em_cpt(masked_text: str, allowed_em_codes: list[dict]) -> str:
    prompt = build_em_prompt(masked_text, allowed_em_codes)
    result = em_llm.invoke(prompt)
    return result.em_code
