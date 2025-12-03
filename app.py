import streamlit as st
from robertson.robertson_app import run as run_robertson_app
from cognitive.cognitive_app import run as run_cognitive_app
from medical_wealth_ambition.medical_wealth_ambition_app import run as run_medical_wealth_ambition_app

st.set_page_config(page_title="Coding Portal")

tab = st.sidebar.radio("Select App", ["Robertson", "Cognitive", "Medical Wealth Ambition"])

if tab == "Robertson":
    run_robertson_app()
elif tab == "Cognitive":
    run_cognitive_app()
elif tab == "Medical Wealth Ambition":
    run_medical_wealth_ambition_app()