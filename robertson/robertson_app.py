def run():
    import streamlit as st
    import pandas as pd
    import io
    import os
    from robertson.utils.file_utils import process_file
    from robertson.utils.data_utils import load_mappings
    from concurrent.futures import ThreadPoolExecutor, as_completed

    HEADERS = [
        "Date",
        "Appointment Type",
        "Client Name",
        "DOB",
        "Service Code",
        "Service Description",
        "Clinician Name",
        "POS",
        "Modifier",
        "Coding",
        "Note Status",
        "Status",
        "Comments",
    ]

    st.title("Robertson Practice")

    uploaded_files = st.file_uploader(
        "Upload one or more SOAP notes (PDFs)", type="pdf", accept_multiple_files=True
    )

    # Load CPT to ICD mapping (used only for CPT descriptions)
    cpt_icd_mapping_df = load_mappings()  # second value is ignored

    if uploaded_files:
        # Clear previous session if file list changes
        if st.session_state.get("last_files") != [f.name for f in uploaded_files]:
            st.session_state.pop("results_df", None)
            st.session_state.pop("last_files", None)

        if "results_df" not in st.session_state:
            results = []
            total_files = len(uploaded_files)
            progress_bar = st.progress(0)
            status_text = st.empty()

            def process_file_wrapper(uploaded_file):
                return process_file(uploaded_file, cpt_icd_mapping_df)

            # Parallel processing (limit workers to avoid resource spikes)
            max_workers = min(4, total_files)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(process_file_wrapper, f): f.name
                    for f in uploaded_files
                }
                completed = 0
                for future in as_completed(futures):
                    completed += 1
                    try:
                        # give each task an upper-bound timeout to avoid hanging
                        res = future.result(timeout=300)
                    except Exception as e:
                        # Record the error as a result row so the app doesn't crash
                        err_row = {h: "" for h in HEADERS}
                        err_row["Comments"] = f"Error processing file: {e}"
                        res = err_row

                    results.append(res)
                    progress_bar.progress(completed / total_files)
                    status_text.text(f"Processed {completed} of {total_files} files.")

            st.session_state.results_df = pd.DataFrame(results, columns=HEADERS)
            st.session_state.last_files = [f.name for f in uploaded_files]

        # Display results
        results_df = st.session_state.results_df
        st.subheader("Results Summary")
        st.dataframe(results_df, use_container_width=True)

        # Custom filename for download
        default_filename = "robertson_coding_solved.xlsx"
        custom_name = st.text_input("Rename Excel file:", value=default_filename)
        if not custom_name.endswith(".xlsx"):
            custom_name += ".xlsx"

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            results_df.to_excel(writer, index=False, sheet_name="Results")

        if st.download_button(
            label="Download Results as Excel",
            data=buffer.getvalue(),
            file_name=custom_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ):
            # Clear session state after download
            st.session_state.pop("results_df", None)
            st.session_state.pop("last_files", None)

            # Delete uploaded PDF files
            for f in os.listdir("data"):
                if f.endswith(".pdf"):
                    try:
                        os.remove(os.path.join("data", f))
                    except Exception:
                        pass
