def run():
    import pandas as pd
    import io
    import streamlit as st
    from cognitive.utils.utils import extract_patient_info, load_pdf
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    @st.cache_data(show_spinner=False)
    def cached_load_pdf(file_bytes):
        import io
        return load_pdf(io.BytesIO(file_bytes))

    def process_file_wrapper(uploaded_file):
        text = cached_load_pdf(uploaded_file.getvalue())
        return extract_patient_info(text)

    st.title("Cognitive Works")

    uploaded_files = st.file_uploader(
        "Upload one or more SOAP notes (PDFs) of Cognitive Practice patients",
        type="pdf",
        accept_multiple_files=True,
    )

    # Clear session if uploaded files changed
    if uploaded_files and st.session_state.get("last_files") != [f.name for f in uploaded_files]:
        st.session_state.pop("patient_data", None)
        st.session_state["last_files"] = [f.name for f in uploaded_files]

    if uploaded_files and "patient_data" not in st.session_state:
        st.session_state["patient_data"] = []

        total_files = len(uploaded_files)
        progress_bar = st.progress(0)
        status_text = st.empty()
        results = []

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(process_file_wrapper, f): f.name for f in uploaded_files}
            completed = 0
            for future in as_completed(futures):
                results.append(future.result())
                completed += 1
                progress_bar.progress(completed / total_files)
                status_text.text(f"Processed {completed} of {total_files} files...")

        st.session_state["patient_data"].extend(results)
        status_text.text("✅ All files processed successfully!")

    if st.session_state.get("patient_data"):
        df = pd.DataFrame(st.session_state["patient_data"])
        df.insert(0, "Facility Name", "Cognitive Works")
        st.subheader("Results Summary")
        st.dataframe(df, width="stretch")

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Cognitive Works Patients")

        filename = st.text_input("Enter filename for Excel download:", value="cognitive_works_coding_results.xlsx")
        if not filename.lower().endswith(".xlsx"):
            filename += ".xlsx"

        st.download_button(
            label="Download Results as Excel",
            data=buffer.getvalue(),
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
