import hashlib
import os
import json
import openai
import PyPDF2
import docx
import streamlit as st
from io import BytesIO
from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch

MARITACA_API_KEY = st.secrets.get("MARITACA_API_KEY")
if not MARITACA_API_KEY:
    st.error("A variável MARITACA_API_KEY não foi definida em .streamlit/secrets.toml.")
    st.stop()

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
            "Você é um assistente especialista em design educacional e criação de conteúdo. "
            + idioma_text
            + f"{texto}"
        )
    }

def chat_with_bot(user_input, preprompt):
    try:
        response = client.chat.completions.create(
            model="sabiazim-3",
            messages=[preprompt, {"role": "user", "content": user_input}],
            temperature=0.7,
            max_tokens=2048
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Erro na comunicação com a API: {e}"

def gerar_glossario(conteudo, preprompt):
    prompt_glossario = (
        "Seção 3. Glossário geral\n\n"
        "Com base no texto abaixo, identifique as palavras ou termos difíceis, técnicos ou pouco usuais para o público geral. "
        "Apresente no formato: N°:\\tTermo:\\tDefinição / significado. Texto base:\n" + conteudo
    )
    return chat_with_bot(prompt_glossario, preprompt)

def gerar_links_anexos(conteudo, preprompt):
    prompt_links = (
        "Seção 4. Links de materiais complementares e anexos\n\n"
        "Extraia apenas os links e anexos citados no texto. Conteúdo base:\n" + conteudo
    )
    return chat_with_bot(prompt_links, preprompt)

def revisar_texto(conteudo, preprompt):
    prompt_revisao = (
        "Revisão ortográfica e de coerência\n\n"
        "Revise o texto abaixo corrigindo erros ortográficos, gramaticais e problemas de coerência. "
        "Mantenha o sentido original, melhore a fluidez e entregue apenas o texto revisado.\n\nTexto:\n"
        + conteudo
    )
    return chat_with_bot(prompt_revisao, preprompt)

st.set_page_config(page_title="Escriba - Gerador de Módulo", layout="wide")
st.title("Escriba - Gerador de Módulo Educacional")

if "conteudo_modulo" not in st.session_state:
    st.session_state["conteudo_modulo"] = []
if "texto_final" not in st.session_state:
    st.session_state["texto_final"] = None
if "cache" not in st.session_state:
    st.session_state["cache"] = {}

def build_texto_final(secoes):
    return "\n\n".join(secoes)

# coloque o uploader fora do form para que outros botões possam acessá-lo imediatamente
arquivo = st.file_uploader("Envie um arquivo (.pdf, .txt, .docx)", type=["pdf", "txt", "docx"], key="arquivo")

with st.form("generate_form"):
    st.header("Parâmetros")
    tema_geral = st.text_input("Digite uma breve descrição do tema geral:", key="tema")
    idioma = st.selectbox("Idioma de saída", ["Português", "Inglês"], key="idioma")

    st.markdown("**Seções a gerar (marque as que desejar):**")
    gerar_resumo = st.checkbox("Resumo geral aprofundado (Seção 0)", value=False, key="opt_resumo")
    gerar_introducao = st.checkbox("Introdução (Seção 1)", value=True, key="opt_introducao")
    gerar_unidades = st.checkbox("Unidades de aprendizagem (Seção 2)", value=True, key="opt_unidades")
    gerar_glossario_opt = st.checkbox("Glossário (Seção 3)", value=True, key="opt_glossario")
    gerar_links_opt = st.checkbox("Links e anexos (Seção 4)", value=True, key="opt_links")
    gerar_conclusao = st.checkbox("Conclusão (Seção 5)", value=True, key="opt_conclusao")
    gerar_referencias = st.checkbox("Referências (Seção 6)", value=True, key="opt_referencias")

    col1, col2 = st.columns([1,1])
    with col1:
        gerar_btn = st.form_submit_button("Gerar módulo")
    with col2:
        st.write("")  # espaço para alinhamento; botão de revisão fica fora do form

# botão de revisão usando o arquivo (fora do form para evitar conflito de submit)
revisar_pdf_btn = st.button("Revisar ortografia (usar PDF)")

if revisar_pdf_btn:
    if not arquivo:
        st.error("Envie um arquivo PDF para revisão.")
    else:
        arquivo.seek(0)
        ext = arquivo.name.split(".")[-1].lower()
        if ext != "pdf":
            st.error("A revisão via PDF exige um arquivo .pdf. Para outros formatos, use a revisão de texto.")
        else:
            file_bytes = arquivo.read()
            file_like = BytesIO(file_bytes)
            texto_pdf = ler_pdf(file_like)
            preprompt = criar_preprompt(f"Tema geral: {tema_geral}\n\n{texto_pdf}", idioma)
            revisado = revisar_texto(texto_pdf, preprompt)
            st.success("Revisão do PDF concluída.")
            st.text_area("Texto revisado (do PDF)", revisado, height=400)
            st.download_button(
                "📄 Baixar revisão (TXT)",
                revisado,
                file_name="revisao_pdf.txt",
                mime="text/plain"
            )

if gerar_btn:
    if not tema_geral and not arquivo:
        st.error("Preencha a descrição do tema geral ou envie um arquivo antes de processar.")
    else:
        if arquivo:
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
                st.stop()
        else:
            texto_origem = ""

        preprompt = criar_preprompt(f"Tema geral: {tema_geral}\n\n{texto_origem}", idioma)

        # usar o botão de revisão externo (revisar_pdf_btn)
        if revisar_pdf_btn:
            conteudo_base = texto_origem if texto_origem.strip() else tema_geral
            st.session_state["texto_revisado"] = revisar_texto(conteudo_base, preprompt)
            st.success("Revisão concluída.")
            st.text_area("Texto revisado", st.session_state["texto_revisado"], height=300)
            st.download_button(
                "📄 Baixar revisão (TXT)",
                st.session_state["texto_revisado"],
                file_name="texto_revisado.txt",
                mime="text/plain",
                key="download-revisado"
            )

        if gerar_btn:
            if not any([gerar_resumo, gerar_introducao, gerar_unidades, gerar_glossario_opt, gerar_links_opt, gerar_conclusao, gerar_referencias]):
                st.error("Selecione ao menos uma seção para gerar.")
            else:
                opts = [
                    ("R" if gerar_resumo else "-"),
                    ("I" if gerar_introducao else "-"),
                    ("U" if gerar_unidades else "-"),
                    ("G" if gerar_glossario_opt else "-"),
                    ("L" if gerar_links_opt else "-"),
                    ("C" if gerar_conclusao else "-"),
                    ("F" if gerar_referencias else "-"),
                ]
                opts_tag = "".join(opts)
                cache_key = f"{file_hash if arquivo else 'no_file'}__{tema_geral.strip()}__{idioma}__{opts_tag}"

                if cache_key in st.session_state["cache"]:
                    st.success("Conteúdo carregado do cache.")
                    st.session_state["texto_final"] = st.session_state["cache"][cache_key]
                else:
                    st.session_state["conteudo_modulo"] = []
                    progress = st.progress(0)
                    step = 0
                    total_steps = 1 + sum([gerar_resumo, gerar_introducao, gerar_unidades, gerar_glossario_opt, gerar_links_opt, gerar_conclusao, gerar_referencias])
                    step += 1
                    progress.progress(int(step / total_steps * 100))

                    if gerar_resumo:
                        prompt_resumo = (
                            "Seção 0. Resumo geral aprofundado\n\n"
                            "Faça um resumo aprofundado do material, sintetizando os pontos principais e destacando aplicações práticas."
                        )
                        conteudo_resumo = chat_with_bot(prompt_resumo, preprompt)
                        st.session_state["conteudo_modulo"].append("Seção 0. Resumo geral aprofundado\n" + conteudo_resumo)
                        step += 1
                        progress.progress(int(step / total_steps * 100))

                    if gerar_introducao:
                        prompt_introducao = (
                            "Seção 1. Introdução ao conteúdo\n\n"
                            "Redija um texto introdutório para um módulo educacional com pelo menos 3 parágrafos."
                        )
                        conteudo_introducao = chat_with_bot(prompt_introducao, preprompt)
                        st.session_state["conteudo_modulo"].append("Seção 1. Introdução ao conteúdo\n" + conteudo_introducao)
                        step += 1
                        progress.progress(int(step / total_steps * 100))

                    if gerar_unidades:
                        prompt_unidades = "Seção 2. Unidades de aprendizagem do Módulo\n\nDesenvolva as unidades principais."
                        conteudo_unidades = chat_with_bot(prompt_unidades, preprompt)
                        st.session_state["conteudo_modulo"].append("Seção 2. Unidades de aprendizagem do Módulo\n" + conteudo_unidades)
                        step += 1
                        progress.progress(int(step / total_steps * 100))

                    if gerar_glossario_opt:
                        conteudo_para_glossario = f"{tema_geral}\n{texto_origem}"
                        conteudo_glossario = gerar_glossario(conteudo_para_glossario, preprompt)
                        st.session_state["conteudo_modulo"].append("Seção 3. Glossário geral\n" + conteudo_gllossario if False else "Seção 3. Glossário geral\n" + conteudo_glossario)
                        step += 1
                        progress.progress(int(step / total_steps * 100))

                    if gerar_links_opt:
                        conteudo_links = gerar_links_anexos(texto_origem, preprompt)
                        st.session_state["conteudo_modulo"].append("Seção 4. Links de materiais complementares e anexos\n" + conteudo_links)
                        step += 1
                        progress.progress(int(step / total_steps * 100))

                    if gerar_conclusao:
                        prompt_conclusao = "Seção 5. Unidade de conclusão do módulo\n\nResuma e incentive a aplicação do conhecimento."
                        conteudo_conclusao = chat_with_bot(prompt_conclusao, preprompt)
                        st.session_state["conteudo_modulo"].append("Seção 5. Unidade de conclusão do módulo\n" + conteudo_conclusao)
                        step += 1
                        progress.progress(int(step / total_steps * 100))

                    if gerar_referencias:
                        prompt_referencias = "Seção 6. Referências do Módulo\n\nExtraia referências presentes no conteúdo."
                        conteudo_referencias = chat_with_bot(prompt_referencias, preprompt)
                        st.session_state["conteudo_modulo"].append("Seção 6. Referências do Módulo\n" + conteudo_referencias)
                        step += 1
                        progress.progress(int(step / total_steps * 100))

                    texto_final = build_texto_final(st.session_state["conteudo_modulo"])
                    st.session_state["texto_final"] = texto_final
                    st.session_state["cache"][cache_key] = texto_final
                    progress.progress(100)
                    st.success("Geração concluída.")

if st.session_state.get("texto_final"):
    st.markdown("---")
    texto_final = st.session_state["texto_final"]

    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import PageBreak

    buffer_pdf = BytesIO()
    doc_pdf = SimpleDocTemplate(
        buffer_pdf,
        pagesize=A4,
        rightMargin=48,
        leftMargin=48,
        topMargin=56,
        bottomMargin=56,
    )

    base_font = "Helvetica"
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="TitleMain",
        parent=styles["Title"],
        fontName=base_font,
        fontSize=20,
        leading=24,
        alignment=TA_CENTER,
        spaceAfter=18,
    ))
    styles.add(ParagraphStyle(
        name="ModuleMeta",
        parent=styles["Normal"],
        fontName=base_font,
        fontSize=10,
        leading=12,
        alignment=TA_CENTER,
        textColor="#666666",
        spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        name="HeadingSection",
        parent=styles["Heading2"],
        fontName=base_font,
        fontSize=14,
        leading=18,
        spaceBefore=12,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="EscribaBody",
        parent=styles["Normal"],
        fontName=base_font,
        fontSize=11,
        leading=15,
        spaceBefore=6,
        spaceAfter=6,
        alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name="FooterSmall",
        parent=styles["Normal"],
        fontName=base_font,
        fontSize=8,
        leading=10,
        alignment=TA_CENTER,
        textColor="#777777",
    ))

    def draw_page(canvas, doc):
        canvas.saveState()
        w, h = A4
        footer_text = "Escriba — Gerador de Módulo Educacional"
        page_num = f"Página {doc.page}"
        canvas.setFont(base_font, 8)
        canvas.setFillColorRGB(0.4, 0.4, 0.4)
        canvas.drawCentredString(w / 2.0, 20, footer_text + "    •    " + page_num)
        canvas.restoreState()

    story = []

    titulo_modulo = st.session_state.get("tema", "Módulo Gerado")
    idioma_meta = st.session_state.get("idioma", "Português")
    from datetime import datetime
    story.append(Paragraph("Escriba — Gerador de Módulo", styles["TitleMain"]))
    story.append(Paragraph(titulo_modulo, styles["HeadingSection"]))
    meta = f"Idioma: {idioma_meta} • Gerado: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    story.append(Paragraph(meta, styles["ModuleMeta"]))
    story.append(Spacer(1, 0.2 * inch))
    story.append(PageBreak())

    for sec in [s.strip() for s in texto_final.split("\n\n") if s.strip()]:
        linhas = sec.split("\n")
        heading = linhas[0].strip()
        body_lines = linhas[1:]
        story.append(Paragraph(heading, styles["HeadingSection"]))
        body_text = "\n".join(body_lines).strip()
        if body_text:
            paras = [p.strip() for p in body_text.split("\n\n") if p.strip()]
            for p in paras:
                story.append(Paragraph(p.replace("\n", "<br/>"), styles["EscribaBody"]))
        story.append(Spacer(1, 0.12 * inch))

    doc_pdf.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    buffer_pdf.seek(0)

    st.download_button("📕 Baixar PDF do módulo", buffer_pdf, "modulo.pdf", "application/pdf", key="download-pdf")

    st.markdown(
        "<div style='position: fixed; bottom: 8px; right: 16px; font-size: 10px; color: #888;'>"
        "Feito por: PietroTy, 2025"
        "</div>",
        unsafe_allow_html=True
    )