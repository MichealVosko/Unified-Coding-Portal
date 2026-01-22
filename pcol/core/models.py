from pydantic import BaseModel, Field
from typing import List, Dict
from enum import Enum

class TopLevelCategory(str, Enum):
    OFFICE_AND_PATIENT_VISITS = "Office and Patient Visits"
    PROCEDURES = "Procedures"
    LAB_AND_DIAGNOSTIC_TESTS = "Laboratory and Diagnostic Tests"
    VACCINES_AND_IMMUNIZATIONS = "Vaccines and Immunizations"
    NUTRITION_AND_COUNSELING = "Nutrition and Counseling"
    MEDICATIONS_AND_INJECTABLE_DRUGS = "Medications and Injectable Drugs"
    ADMINISTRATIVE_AND_BILLING = "Administrative and Billing"


class SOAPCategoryPrediction(BaseModel):
    categories: List[TopLevelCategory] = Field(
        ..., description="Top-level CPT categories applicable to the SOAP note"
    )


class CPTSelection(BaseModel):
    selected_cpt_codes: List[Dict[str, str]] = Field(
        ...,
        description="List of selected CPT codes and their description based on the predicted categories",
    )
