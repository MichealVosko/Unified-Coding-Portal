import pandas as pd
import streamlit as st

@st.cache_data
def load_mappings(file_path="robertson/data/Expanded_CPT_to_ICD_mapping.xlsx"):
    df = pd.read_excel(file_path)
    return df