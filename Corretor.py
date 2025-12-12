import hashlib
import openai
import PyPDF2
import docx
import streamlit as st
from io import BytesIO
from docx import Document

MARITACA_API_KEY = st.secrets.get("MARITACA_API_KEY")
client = None
if MARITACA_API_KEY:
    client = openai.OpenAI(api_key=MARITACA_API_KEY, base_url="https://chat.maritaca.ai/api")


def ler_pdf(arquivo):

    texto = ""
    leitor = PyPDF2.PdfReader(arquivo)
    for pagina in leitor.pages:
        texto_pagina = pagina.extract_text()
        if texto_pagina:
            texto += texto_pagina + "\n"
    return texto.strip()


def ler_txt(arquivo):

    arquivo.seek(0)
    return arquivo.read().decode("utf-8").strip()


def ler_docx(arquivo):

    arquivo.seek(0)
    doc = docx.Document(arquivo)
    return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])


def criar_preprompt(texto, idioma):

    idioma_text = f"Idioma de saída: {idioma}.\n\n"
    return {
        "role": "system",
        "content": (
            "Você é um assistente especialista em revisão ortográfica, gramatical e de coerência. "
            + idioma_text
            + f"{texto}"
        )
    }


def chat_with_bot(user_input, preprompt):

    try:
        if client is None:
            return "MARITACA_API_KEY não configurada. Defina-a em .streamlit/secrets.toml."
        response = client.chat.completions.create(
            model="sabiazim-3",
            messages=[preprompt, {"role": "user", "content": user_input}],
            temperature=0.7,
            max_tokens=2048
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Erro na comunicação com a API: {e}"


def revisar_texto(conteudo, preprompt):

    prompt_revisao = (
        "Revisão ortográfica e de coerência\n\n"
        "Revise o texto abaixo corrigindo erros ortográficos, gramaticais e problemas de coerência. "
        "Mantenha o sentido original, melhore a fluidez e entregue apenas o texto revisado.\n\nTexto:\n"
        + conteudo
    )
    return chat_with_bot(prompt_revisao, preprompt)


def corretor_ui():

    if client is None:
        st.error("A variável MARITACA_API_KEY não foi definida em .streamlit/secrets.toml.")
        return

    st.title("Corretor — Ferramenta de Revisão de Texto")
    st.markdown(
        "Carregue um arquivo (PDF, TXT, DOCX) ou cole um texto para revisão ortográfica, "
        "gramatical e de coerência."
    )

    if "corretor_texto_revisado" not in st.session_state:
        st.session_state["corretor_texto_revisado"] = None
    if "corretor_texto_original" not in st.session_state:
        st.session_state["corretor_texto_original"] = None
    if "corretor_cache" not in st.session_state:
        st.session_state["corretor_cache"] = {}

    tab1, tab2 = st.tabs(["Carregar Arquivo", "Colar Texto"])

    with tab1:
        st.subheader("Carregar Arquivo")
        arquivo = st.file_uploader(
            "Envie um arquivo (.pdf, .txt, .docx)",
            type=["pdf", "txt", "docx"],
            key="corretor_arquivo"
        )

    with tab2:
        st.subheader("Colar Texto Diretamente")
        texto_colado = st.text_area(
            "Cole seu texto aqui para revisão:",
            height=300,
            key="corretor_texto_colado"
        )

    st.markdown("---")
    col1, col2 = st.columns([3, 1])

    with col1:
        idioma = st.selectbox(
            "Idioma de saída",
            ["Português", "Inglês"],
            key="corretor_idioma"
        )

    with col2:
        revisar_btn = st.button("Revisar Texto", use_container_width=True, key="corretor_revisar")

    if revisar_btn:

        if arquivo is not None:
            arquivo.seek(0)
            file_bytes = arquivo.read()
            file_hash = hashlib.sha256(file_bytes).hexdigest()
            file_like = BytesIO(file_bytes)
            ext = arquivo.name.split(".")[-1].lower()

            if ext == "pdf":
                texto_origem = ler_pdf(file_like)
            elif ext == "txt":
                texto_origem = ler_txt(file_like)
            elif ext == "docx":
                texto_origem = ler_docx(file_like)
            else:
                st.error("Formato de arquivo não suportado.")
                return

            cache_key = f"{file_hash}__{idioma}"
        elif texto_colado and texto_colado.strip():
            texto_origem = texto_colado.strip()
            file_hash = hashlib.sha256(texto_origem.encode()).hexdigest()
            cache_key = f"{file_hash}__{idioma}"
        else:
            st.error("Por favor, carregue um arquivo ou cole um texto para revisar.")
            return

        if cache_key in st.session_state["corretor_cache"]:
            st.success("Conteúdo carregado do cache.")
            st.session_state["corretor_texto_revisado"] = st.session_state["corretor_cache"][cache_key]
            st.session_state["corretor_texto_original"] = texto_origem
        else:

            with st.spinner("Revisando texto..."):
                preprompt = criar_preprompt(f"Contexto: revisão de texto\n\n{texto_origem}", idioma)
                texto_revisado = revisar_texto(texto_origem, preprompt)
                st.session_state["corretor_texto_revisado"] = texto_revisado
                st.session_state["corretor_texto_original"] = texto_origem
                st.session_state["corretor_cache"][cache_key] = texto_revisado
                st.success("Revisão concluída com sucesso!")

    if st.session_state.get("corretor_texto_revisado"):
        st.markdown("---")
        st.subheader("Resultado da Revisão")

        result_tab1, result_tab2 = st.tabs(["Texto Revisado", "Texto Original"])

        with result_tab1:
            st.text_area(
                "Texto revisado:",
                st.session_state["corretor_texto_revisado"],
                height=400,
                disabled=True,
                key="corretor_result_revisado"
            )
            st.download_button(
                "Baixar Texto Revisado (TXT)",
                st.session_state["corretor_texto_revisado"],
                file_name="texto_revisado.txt",
                mime="text/plain",
                key="corretor_download_revisado"
            )

        with result_tab2:
            st.text_area(
                "Texto original:",
                st.session_state["corretor_texto_original"],
                height=400,
                disabled=True,
                key="corretor_result_original"
            )

    st.markdown("---")
    st.markdown(
        "<div style='position: fixed; bottom: 8px; right: 16px; font-size: 10px; color: #888;'>"
        "Corretor — Ferramenta de Revisão de Texto | Feito por: PietroTy, 2025"
        "</div>",
        unsafe_allow_html=True
    )
