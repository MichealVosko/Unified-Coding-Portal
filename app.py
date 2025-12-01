import streamlit as st
from robertson.robertson_app import run as run_robertson_app
from cognitive.cognitive_app import run as run_cognitive_app

st.set_page_config(page_title="Coding Portal")

tab = st.sidebar.radio("Select App", ["Robertson", "Cognitive"])

if tab == "Robertson":
    run_robertson_app()
elif tab == "Cognitive":
    run_cognitive_app()
