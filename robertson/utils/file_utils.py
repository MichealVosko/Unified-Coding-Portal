from robertson.utils.pdf_utils import load_pdf, deidentify_and_strip
from robertson.utils.cpt_utils import predict_cpt_code, calculate_cpt_units
from robertson.utils.validation_utils import check_note, check_biopsychosocial, check_mental_status_assessed
from robertson.utils.phi_utils import get_phi
from robertson.utils.psych_eval_utils import extract_psych_eval_data
from robertson.utils.cpt_utils import sort_diagnosis_codes
import tempfile

# Ensure the uploaded file pointer is at the start


def process_file(uploaded_file, cpt_icd_mapping_df):
    uploaded_file.seek(0)
    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    text = load_pdf(tmp_path)    
    clean = deidentify_and_strip(text)
    phi_data = get_phi(text)
    service_code = phi_data.get("Service Code", "")

    # Psych evaluation CPTs
    psych_cpts = ["96130", "96131", "96138", "96139"]

    if service_code in psych_cpts:
        # Run psych evaluation logic
        psych_data = extract_psych_eval_data(text)
        units = psych_data["Follow up code Units"]

        # CPT description safely
        service_descriptions = []
        service_desc_df = cpt_icd_mapping_df[cpt_icd_mapping_df["CPT"] == service_code]
        if not service_desc_df.empty:
            service_descriptions.append(service_desc_df["CPT Description"].iloc[0])

        # ICD codes from chart
        diagnosis_codes = sort_diagnosis_codes(phi_data.get("Diagnosis Codes", []))
        unit_str = f"{units}X" if units > 0 else ""
        modifier = phi_data.get("Modifier", "")
        row_coding = (
            f"{service_code}--{unit_str}--{modifier}--{', '.join(diagnosis_codes)}"
        )

        comments_str = "Check portal for evaluation file"

    else:
        # Normal flow for other CPTs (908x etc.)
        predicted_cpts = predict_cpt_code(clean)
        if "90840" in predicted_cpts and "90839" not in predicted_cpts:
            predicted_cpts.remove("90840")

        # ICD extraction from chart
        diagnosis_codes = sort_diagnosis_codes(phi_data.get("Diagnosis Codes", []))

        # Note validation
        validation_result = check_note(clean, uploaded_file.name)
        comments_str = (
            f"Missing: {', '.join(validation_result['missing_sections'])}"
            if validation_result["missing_sections"]
            else ""
        )
        
        if not check_mental_status_assessed(clean):
            note = "Current Mental Status not assessed."
            comments_str = f"{comments_str} | {note}" if comments_str else note

        clinician_name = phi_data.get("Clinician", "") or ""
        medicaid_clinicians = ["Kayla", "Kaeli", "Virginia", "Courtney"]

        is_medicaid_clinician = any(
            name.lower() in clinician_name.lower() for name in medicaid_clinicians
        )
        if service_code == "90837" and is_medicaid_clinician:
            note = "Verify the H0004 with Medicaid guidelines."
            comments_str = f"{comments_str} | {note}" if comments_str else note

        # Duration & CPT units
        duration_str = phi_data.get("Duration")
        cpt_with_units = calculate_cpt_units(predicted_cpts, duration_str)
        cpt_with_units = list(dict.fromkeys(cpt_with_units))
        # CPT descriptions safely
        service_descriptions = []
        if service_code:
            service_desc_df = cpt_icd_mapping_df[
                cpt_icd_mapping_df["CPT"] == service_code
            ]
            if not service_desc_df.empty:
                service_descriptions.append(service_desc_df["CPT Description"].iloc[0])

        # Build coding string using predicted CPT units and ICDs
        modifier = phi_data.get("Modifier", "") or ""
        row_coding = (
            f"{', '.join(cpt_with_units)}--{modifier}--{', '.join(diagnosis_codes)}"
        )
        
        if service_code == "90791":
            ok, issue = check_biopsychosocial(clean)
            if not ok:
                note = f"Section 'Biopsychosocial Assessment' {issue}."
                comments_str = f"{comments_str} | {note}" if comments_str else note

    # Build row dictionary
    row = {
        "Date": phi_data.get("Date", ""),
        "Appointment Type": "Therapy Session",
        "Client Name": phi_data.get("Patient", ""),
        "DOB": phi_data.get("DOB", ""),
        "Service Code": service_code,
        "Primary Diagnosis": ", ".join(diagnosis_codes),
        "Service Description": ", ".join(service_descriptions)
        if service_descriptions
        else "",
        "Clinician Name": phi_data.get("Clinician", ""),
        "POS": phi_data.get("POS", ""),
        "Modifier": phi_data.get("Modifier", ""),
        "Coding": row_coding,
        "Note Status": "Finalized",
        "Status": "On Hold",
        "Comments": comments_str,
    }

    import os
    os.remove(tmp_path)
    return row
