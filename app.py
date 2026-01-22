import streamlit as st
from robertson.robertson_app import run as run_robertson_app
from cognitive.cognitive_app import run as run_cognitive_app
from mental_wealth_ambition.mental_wealth_ambition_app import (
    run as run_mental_wealth_ambition_app,
)
from pcol.pcol_app import run as run_pcol_app

st.set_page_config(page_title="Coding Portal")

tab = st.sidebar.radio(
    "Select App", ["Robertson", "Cognitive", "Mental Wealth Ambition", "PCOL"]
)

if tab == "Robertson":
    run_robertson_app()
elif tab == "Cognitive":
    run_cognitive_app()
elif tab == "Mental Wealth Ambition":
    run_mental_wealth_ambition_app()
elif tab == "PCOL":
    run_pcol_app()
