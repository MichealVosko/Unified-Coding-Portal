def run():
    import streamlit as st
    import pandas as pd
    import io
    import json
    from pathlib import Path
    import time

    from pcol.core.pdf_processing import read_pdf_text
    from pcol.core.cpt_selection import (
        build_categories_prompt,
        categories_prediction_llm,
        select_cpts,
    )
    from pcol.core.utils import norm

    # =========================
    # CONFIG
    # =========================

    CPT_MAPPING_PATH = Path("pcol/data/cpt_mapping.json")
    RESULTS_CURRENT_PATH = Path("pcol/data/results_current.json")  # for current batch
    RESULTS_LAST_BATCH_PATH = Path("pcol/data/results_last_batch.json")  # optional n-1 batch

    st.set_page_config(page_title="Pediatric of La Porte", layout="wide")
    st.title("Pediatric of La Porte")
    st.session_state.patient_data = []

    # =========================
    # LOAD CPT MAPPING
    # =========================
    @st.cache_data
    def load_cpt_mapping():
        if not CPT_MAPPING_PATH.exists():
            raise FileNotFoundError(f"Missing CPT mapping: {CPT_MAPPING_PATH}")
        with open(CPT_MAPPING_PATH, "r", encoding="utf-8") as f:
            mapping = json.load(f)
        return {k.strip().lower(): v for k, v in mapping.items()}

    normalized_mapping = load_cpt_mapping()

    # =========================
    # LOAD CRASH-RECOVERY RESULTS (CURRENT BATCH ONLY)
    # =========================
    if RESULTS_CURRENT_PATH.exists():
        try:
            with open(RESULTS_CURRENT_PATH, "r", encoding="utf-8") as f:
                st.session_state.patient_data = json.load(f)
        except json.JSONDecodeError:
            st.session_state.patient_data = []
    else:
        st.session_state.patient_data = []

    # =========================
    # FILE UPLOAD
    # =========================
    uploaded_files = st.file_uploader(
        "Upload SOAP note PDFs",
        type=["pdf"],
        accept_multiple_files=True,
    )

    # =========================
    # PROCESS FILES
    # =========================
    if uploaded_files:
        progress_bar = st.progress(0)
        status_text = st.empty()
        total_files = len(uploaded_files)

        # Keep track of already processed files in this batch
        processed_files = {r["filename"] for r in st.session_state.patient_data}

        for idx, uploaded_file in enumerate(uploaded_files, start=1):
            if uploaded_file.name in processed_files:
                status_text.text(f"Skipping already processed file: {uploaded_file.name}")
                progress_bar.progress(idx / total_files)
                continue

            status_text.text(f"Processing file {idx}/{total_files}: {uploaded_file.name}")

            # Read uploaded file into BytesIO
            pdf_bytes = io.BytesIO(uploaded_file.read())

            # -------------------------
            # Extract SOAP text + demographics
            # -------------------------
            masked_text, demographics = read_pdf_text(pdf_bytes)

            # -------------------------
            # Category Prediction
            # -------------------------
            cat_prompt = build_categories_prompt(masked_text)
            cat_obj = categories_prediction_llm.invoke(cat_prompt)
            predicted_categories = [norm(c.value) for c in cat_obj.categories]

            # -------------------------
            # CPT Selection (includes E/M)
            # -------------------------
            service_date = demographics.get("service_date", "")
            final_cpts = select_cpts(
                masked_text=masked_text,
                predicted_categories=predicted_categories,
                normalized_mapping=normalized_mapping,
                service_date=service_date,
            )

            # -------------------------
            # Store results
            # -------------------------
            record = {
                "filename": uploaded_file.name,
                "patient_name": demographics.get("patient_name"),
                "dob": demographics.get("dob"),
                "age": demographics.get("age"),
                "service_date": service_date,
                "provider_name": demographics.get("provider_name"),
                "account_number": demographics.get("account_number"),
                "predicted_categories": ", ".join(predicted_categories),
                "icd_codes": ", ".join(demographics.get("icd_codes", [])),
                "cpt_codes_extracted": ", ".join(demographics.get("cpt_codes", [])),
                "final_cpt_codes": ", ".join(sorted(set(final_cpts))),
            }
            st.session_state.patient_data.append(record)

            # -------------------------
            # Save results immediately (crash-safe)
            # -------------------------
            tmp_path = RESULTS_CURRENT_PATH.with_suffix(".tmp")
            try:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(st.session_state.patient_data, f, indent=2)
                tmp_path.replace(RESULTS_CURRENT_PATH)
            except PermissionError:
                # Retry a few times if file is temporarily locked
                for _ in range(3):
                    time.sleep(0.1)
                    try:
                        tmp_path.replace(RESULTS_CURRENT_PATH)
                        break
                    except PermissionError:
                        continue

            progress_bar.progress(idx / total_files)

        status_text.text("All files in this batch processed successfully!")

        # -------------------------
        # Optionally archive this batch and reset for next batch
        # -------------------------
        RESULTS_CURRENT_PATH.replace(RESULTS_LAST_BATCH_PATH)
        st.session_state.patient_data = []

    # =========================
    # DISPLAY RESULTS
    # =========================
    if st.session_state.patient_data:
        st.subheader("Prediction Results")
        df = pd.DataFrame(st.session_state.patient_data)
        st.dataframe(df, width=1200)

        # Excel download
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Results")

        filename = st.text_input(
            "Enter filename for Excel download:", value="pcol_results.xlsx"
        )
        if not filename.lower().endswith(".xlsx"):
            filename += ".xlsx"

        st.download_button(
            label="Download Results as Excel",
            data=buffer.getvalue(),
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
