def run():
    import streamlit as st
    import pandas as pd
    import io
    from medical_wealth_ambition.utils.pdf_utils import load_pdf
    from medical_wealth_ambition.utils.extract_utils import extract_session_info

    st.title("Medical Wealth Ambition")

    uploaded_files = st.file_uploader(
        "Upload one or more SOAP notes (PDFs)", type="pdf", accept_multiple_files=True
    )

    if "patient_data" not in st.session_state:
        st.session_state.patient_data = []

    if uploaded_files and not st.session_state.patient_data:
        progress_bar = st.progress(0)
        status_text = st.empty()
        total_files = len(uploaded_files)

        for idx, uploaded_file in enumerate(uploaded_files, start=1):
            status_text.text(f"Processing file {idx}/{total_files}: {uploaded_file.name}")

            text = load_pdf(uploaded_file)
            patient_info = extract_session_info(text)
            st.session_state.patient_data.append(patient_info)

            progress_bar.progress(idx / total_files)

        status_text.text("All files processed successfully!")

    if st.session_state.patient_data:
        st.subheader("Results Summary")
        df = pd.DataFrame(st.session_state.patient_data)
        st.dataframe(df, width="stretch")

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Patients")

        filename = st.text_input(
            "Enter filename for Excel download:",
            value="medical_wealth_ambition_results.xlsx",
        )
        if not filename.lower().endswith(".xlsx"):
            filename += ".xlsx"

        st.download_button(
            label="Download Results as Excel",
            data=buffer.getvalue(),
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
