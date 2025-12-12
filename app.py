import streamlit as st

st.set_page_config(page_title="Escriba + Corretor", layout="wide")

st.markdown("# Escriba + Corretor")
st.markdown("Escolha a aba para usar o gerador de módulos (Escriba) ou o corretor de texto.")

from Escriba import escriba_ui
from Corretor import corretor_ui

tab_escriba, tab_corretor = st.tabs(["Escriba", "Corretor"])

with tab_escriba:
    escriba_ui()

with tab_corretor:
    corretor_ui()
