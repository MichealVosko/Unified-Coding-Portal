def run():
    import pandas as pd
    import io
    import streamlit as st
    from cognitive.utils.utils import extract_patient_info, load_pdf

    st.title("Cognitive Works")

    uploaded_files = st.file_uploader(
        "Upload one or more SOAP notes (PDFs) of Cognitive Practice patients",
        type="pdf",
        accept_multiple_files=True,
    )
    if "patient_data" not in st.session_state:
        st.session_state.patient_data = []

    if uploaded_files and not st.session_state.patient_data:
        progress_bar = st.progress(0)
        status_text = st.empty()

        total_files = len(uploaded_files)

        for idx, uploaded_file in enumerate(uploaded_files, start=1):
            status_text.text(
                f"📄 Processing file {idx}/{total_files}: {uploaded_file.name}"
            )

            text = load_pdf(uploaded_file)
            patient_info = extract_patient_info(text)
            st.session_state.patient_data.append(patient_info)

            # Update progress bar after each file
            progress = idx / total_files
            progress_bar.progress(progress)

        status_text.text("✅ All files processed successfully!")

    if st.session_state.patient_data:
        st.subheader("Results Summary")
        df = pd.DataFrame(st.session_state.patient_data)
        df.insert(0, "Facility Name", "Cognitive Works")
        df = df.sort_values(by="DOS", ascending=True)
        st.dataframe(df, width="stretch")

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Cognitive Works Patients")

        # Ask user for filename (default provided)
        custom_filename = st.text_input(
            "Enter filename for Excel download:",
            value="cognitive_works_coding_results.xlsx",
        )
        # Ensure the filename ends with .xlsx
        if not custom_filename.lower().endswith(".xlsx"):
            custom_filename += ".xlsx"

        st.download_button(
            label="📥 Download Results as Excel",
            data=buffer.getvalue(),
            file_name=custom_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
