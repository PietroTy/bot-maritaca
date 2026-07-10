"""
app.py — Orquestrador Principal / Interface Streamlit (Tese de Doutorado)
Escriba v2.0
"""

import streamlit as st
import json
import hashlib
import importlib
import modules.persistence as persistence
import modules.ingestor as ingestor_mod
from modules.ingestor import ingest_document, IngestorResult
import modules.comprehension as comprehension_mod
from modules.comprehension import comprehend
import modules.generator as generator_mod
from modules.generator import generate
import modules.polisher as polisher_mod
from modules.polisher import polish
import modules.exporter as exporter_mod
from modules.exporter import export
import config

# Inicializa diretórios
persistence.ensure_dir()

# ──────────────────────────────────────────────────────────────────
# Configuração da página
# ──────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=config.APP_NOME,
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────
# CSS Custom — Identidade Institucional Verde & Branca (Zero Emojis)
# ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    :root {
        --verde-escriba: #0A5C2F;
        --verde-acao: #1D8E4B;
        --verde-lousa: #042918;
        --verde-papel: #E9F7EE;
        --vermelho-evidencia: #C62828;
        --vermelho-suave: #FDECEC;
        --grafite: #111827;
        --cinza-norma: #6B7280;
        --borda: #DDE7DF;
        --papel: #F8FAF7;
        --branco: #FFFFFF;
    }

    html, body, [class*="css"] {
        font-family: 'Open Sans', sans-serif;
    }

    .stApp {
        background-color: var(--papel) !important;
    }

    /* Força legibilidade de textos no modo escuro do navegador */
    .stApp, 
    .stApp p, 
    .stApp span, 
    .stApp label, 
    .stApp li, 
    .stApp strong, 
    .stApp small, 
    .stApp h1, 
    .stApp h2, 
    .stApp h3, 
    .stApp h4, 
    .stApp h5, 
    .stApp h6 {
        color: var(--grafite) !important;
    }

    /* Inputs e Selectboxes claros na área principal */
    .stSelectbox div, 
    .stTextInput input, 
    .stTextArea textarea, 
    [data-baseweb="select"] *, 
    .stMultiSelect div {
        color: var(--grafite) !important;
        background-color: var(--branco) !important;
    }

    /* Sidebar escura e contraste interno */
    [data-testid="stSidebar"] {
        background-color: var(--verde-lousa) !important;
        border-right: 1px solid rgba(255,255,255,0.08);
    }
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] span, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3, 
    [data-testid="stSidebar"] h4, 
    [data-testid="stSidebar"] h5, 
    [data-testid="stSidebar"] h6, 
    [data-testid="stSidebar"] li, 
    [data-testid="stSidebar"] strong,
    [data-testid="stSidebar"] small,
    [data-testid="stSidebar"] div,
    [data-testid="stSidebar"] code {
        color: #F8FAF7 !important;
    }
    [data-testid="stSidebar"] small {
        color: #C9DFD1 !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,0.12);
    }
    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] [data-baseweb="select"] > div,
    [data-testid="stSidebar"] [data-baseweb="select"] * {
        background-color: rgba(255,255,255,0.08) !important;
        border-color: rgba(255,255,255,0.18) !important;
        color: #F8FAF7 !important;
    }

    /* Header principal */
    .escriba-header {
        display: flex;
        align-items: center;
        gap: 1.2rem;
        padding: 2.2rem 0 1.4rem;
        border-bottom: 1px solid var(--borda);
        margin-bottom: 1.5rem;
    }
    .escriba-header h1 {
        font-size: 2.6rem;
        font-weight: 800;
        color: var(--verde-lousa) !important;
        margin: 0;
        letter-spacing: -0.03em;
        line-height: 1;
    }
    .escriba-header p {
        color: var(--cinza-norma) !important;
        font-size: 1.02rem;
        margin-top: 0.45rem;
        margin-bottom: 0;
    }

    /* Pipeline Step Box */
    .pipeline-step-box {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: var(--branco);
        border: 1px solid var(--borda);
        border-radius: 10px;
        padding: 0.7rem 1rem;
        margin-bottom: 0.5rem;
        transition: all 0.2s ease;
    }
    .pipeline-step-box.active {
        border-color: var(--verde-acao);
        background: var(--verde-papel);
    }
    .pipeline-step-box.done {
        border-color: var(--verde-escriba);
        background: #F1FBF4;
        opacity: 0.85;
    }

    /* Status Dot */
    .status-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 6px;
        vertical-align: middle;
    }
    .status-dot.ok {
        background-color: var(--verde-acao);
        box-shadow: 0 0 6px var(--verde-acao);
    }
    .status-dot.alerta {
        background-color: var(--vermelho-evidencia);
        box-shadow: 0 0 6px var(--vermelho-evidencia);
    }

    /* Badges */
    .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 0.68rem;
        font-weight: 800;
        letter-spacing: 0.06em;
        text-transform: uppercase;
    }
    .badge-placeholder { background: #F3F4F6; color: #4B5563; }
    .badge-funcional  { background: #E3F7E9; color: #0F7B3F; }
    .badge-roadmap    { background: #EEF2F7; color: #374151; }

    /* Botões */
    .stButton > button {
        background: var(--verde-escriba) !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
        padding: 0.6rem 1.5rem !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button,
    .stButton > button p,
    .stButton > button span,
    .stButton > button div {
        color: #ffffff !important;
    }
    .stButton > button:hover {
        background: #084724 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 8px 24px rgba(10,92,47,0.24) !important;
    }

    [data-testid="stDownloadButton"] button {
        background: var(--verde-acao) !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
    }
    [data-testid="stDownloadButton"] button,
    [data-testid="stDownloadButton"] button p,
    [data-testid="stDownloadButton"] button span,
    [data-testid="stDownloadButton"] button div {
        color: #ffffff !important;
    }

    /* Requisito box */
    .requisito-box {
        background-color: var(--verde-papel);
        border: 1px solid var(--borda);
        border-radius: 8px;
        padding: 0.7rem 0.9rem;
        font-size: 0.8rem;
        margin-top: 0.8rem;
        color: var(--verde-lousa);
    }

    /* Log console */
    .log-console-box {
        background-color: #111827;
        color: #e2e8f0 !important;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        padding: 1rem;
        border-radius: 8px;
        max-height: 200px;
        overflow-y: auto;
        border: 1px solid #1e293b;
        margin-top: 0.5rem;
    }

    /* Chunk tracker segments */
    .chunk-tracker-box {
        background-color: var(--branco);
        border: 1px solid var(--borda);
        border-radius: 10px;
        padding: 0.9rem 1rem;
        margin-bottom: 1rem;
    }
    .chunk-bar-container {
        display: flex;
        gap: 4px;
        margin-top: 0.4rem;
    }
    .chunk-bar-segment {
        height: 6px;
        border-radius: 3px;
        flex: 1;
        background-color: #E2E8F0;
    }
    .chunk-bar-segment.done {
        background-color: var(--verde-escriba);
    }
    .chunk-bar-segment.active {
        background-color: var(--verde-acao);
    }

    /* Empty state */
    .empty-state-box {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 3rem 1.5rem;
        background: var(--branco);
        border: 1px solid var(--borda);
        border-radius: 12px;
    }

    .escriba-footer {
        text-align: center;
        color: var(--cinza-norma);
        font-size: 0.78rem;
        padding: 2rem 0 1rem;
        border-top: 1px solid var(--borda);
        margin-top: 3rem;
    }

    /* Section Cards e blocos de info */
    .section-card-wrapper {
        background-color: var(--branco);
        border: 1px solid var(--borda);
        border-radius: 12px;
        padding: 1.1rem 1.3rem;
        margin-bottom: 0.9rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
        transition: all 0.25s ease;
        width: 100%;
    }
    .section-card-wrapper.active {
        border-color: var(--verde-acao);
        background-color: #F4FAF6;
        box-shadow: 0 4px 12px rgba(29,142,75,0.06);
    }
    .section-header-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.8rem;
        width: 100%;
    }
    .section-title-text {
        font-family: 'Open Sans', sans-serif;
        font-weight: 700;
        color: var(--verde-lousa) !important;
        font-size: 1.05rem;
    }
    .stApp .badge-obrigatoria {
        background-color: var(--verde-papel) !important;
        color: var(--verde-escriba) !important;
        font-size: 0.7rem;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 6px;
        border: 1px solid #C2E2CE;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }

    /* Sub-chunks container e cards */
    .subchunks-container {
        margin-top: 0.9rem;
        border-top: 1px dashed #C2E2CE;
        padding-top: 0.9rem;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }
    .subchunk-card {
        background-color: var(--branco);
        border: 1px solid #E6EFEA;
        border-radius: 8px;
        padding: 0.6rem 0.9rem;
        display: flex;
        align-items: center;
        gap: 0.8rem;
        transition: all 0.2s ease;
    }
    .subchunk-card:hover {
        border-color: var(--verde-acao);
        background-color: var(--verde-papel);
    }
    .stApp .subchunk-badge {
        background-color: var(--verde-escriba) !important;
        color: var(--branco) !important;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 6px;
        white-space: nowrap;
    }
    .stApp .subchunk-text {
        color: var(--grafite) !important;
        font-size: 0.84rem;
        line-height: 1.4;
    }
    .subchunk-card.inactive {
        opacity: 0.55;
        background-color: #fafafa !important;
        border-color: #e2e8f0 !important;
    }
    .subchunk-card.inactive .subchunk-badge {
        background-color: #a0aec0 !important;
    }
    
    /* Alinhamento dos checkboxes de secao */
    [data-testid="stCheckbox"] {
        margin-top: 1.3rem;
        margin-left: 0.5rem;
    }

    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────
# Session State — inicialização
# ──────────────────────────────────────────────────────────────────
def _init_state():
    defaults = {
        "cache": {},
        "ingestor_result": None,
        "comprehension_result": None,
        "generator_results": None,
        "polish_results": None,
        "export_bytes": None,
        "export_nome": None,
        "export_mime": None,
        "pipeline_log": [],
        "pipeline_rodou": False,
        "memoria_tese": persistence.load_session(),
        "show_advanced": False,
        "progress_frac": 0.0,
        "progress_text": "Aguardando...",
        "chunk_atual": 0,
        "total_chunks": 0,
        "eta": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# ──────────────────────────────────────────────────────────────────
# Header (Logotipo Dinâmico)
# ──────────────────────────────────────────────────────────────────
import base64
import pathlib

@st.cache_data
def get_logo_base64():
    logo_path = pathlib.Path("logo.png")
    if logo_path.exists():
        try:
            with open(logo_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception:
            pass
    return ""

logo_b64 = get_logo_base64()
if logo_b64:
    header_html = f"""
    <div class="escriba-header" style="display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; gap: 0.8rem; padding: 2.5rem 0 2rem;">
        <img src="data:image/png;base64,{logo_b64}" height="220" style="object-fit: contain;" />
        <p style="font-size: 1.25rem !important; font-weight: 600; color: var(--verde-lousa) !important; margin: 0.5rem 0 0 0; letter-spacing: -0.01em;">Redação acadêmica por micro-chunking iterativo e auditoria de fidelidade</p>
    </div>
    """
else:
    header_html = """
    <div class="escriba-header" style="display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; gap: 0.8rem; padding: 2.5rem 0 2rem;">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="#0A5C2F" />
            <path d="M2 17L12 22L22 17" stroke="#0A5C2F" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            <path d="M2 12L12 17L22 12" stroke="#0A5C2F" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <div>
            <h1 style="font-size: 3rem; font-weight: 800; color: var(--verde-lousa) !important; margin: 0;">Escriba</h1>
            <p style="font-size: 1.25rem !important; font-weight: 600; color: var(--cinza-norma) !important; margin-top: 0.5rem;">Redação acadêmica por micro-chunking iterativo e auditoria de fidelidade</p>
        </div>
    </div>
    """

st.markdown(header_html, unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────
# Configuração / Escolha do Template
# ──────────────────────────────────────────────────────────────────
templates_disponiveis = config.listar_templates()
nomes_templates = {t["nome"]: t["id"] for t in templates_disponiveis}
lista_nomes = list(nomes_templates.keys())

default_idx = next((i for i, name in enumerate(lista_nomes) if "Estrutura Completa" in name), 0)

template_nome_selecionado = st.selectbox(
    "Tipo de produção",
    lista_nomes,
    index=default_idx,
    key="template_selecionado",
)
template_id = nomes_templates[template_nome_selecionado]
template_atual = config.carregar_template(template_id)

def get_template_terms(template_id: str):
    terms = {
        "tese_doutorado_completa": {
            "upload_fatos": "Fatos da Tese (Base teórica, referencial bibliográfico, citações, dados de campo, legislação)",
            "upload_modelo": "Arquivo Modelo / Tese (Capítulos ou introdução já produzidos para guiar o estilo)",
            "tema_label": "Tema / Foco deste capítulo",
            "tema_placeholder": "Descreva o foco específico deste capítulo, não o tema geral da tese.",
            "chunk_tracker": "CHUNKS DO CAPÍTULO",
            "fatos_error": "Envie os fatos ou informe o tema do capítulo."
        },
        "tcc_monografia": {
            "upload_fatos": "Fatos do Trabalho (Base teórica, referencial bibliográfico, citações, dados e argumentos)",
            "upload_modelo": "Arquivo de Referência / TCC (Monografias já produzidas para guiar estilo)",
            "tema_label": "Tema do TCC / Monografia",
            "tema_placeholder": "Descreva o tema específico do seu trabalho de conclusão.",
            "chunk_tracker": "CHUNKS DO TRABALHO",
            "fatos_error": "Envie os fatos ou informe o tema do trabalho."
        },
        "modulo_educacional": {
            "upload_fatos": "Material de Apoio (Apostilas, slides, notas de aula ou base teórica)",
            "upload_modelo": "Arquivo de Referência / Modelo (Módulos anteriores para guiar o estilo, tom e ritmo)",
            "tema_label": "Tema / Foco do Módulo",
            "tema_placeholder": "Descreva o foco ou objetivos de aprendizagem deste módulo.",
            "chunk_tracker": "CHUNKS DO MÓDULO",
            "fatos_error": "Envie os materiais de apoio ou informe o tema do módulo."
        },
        "artigo_cientifico": {
            "upload_fatos": "Dados e Referências do Artigo (Base teórica, dados coletados, citações)",
            "upload_modelo": "Arquivo de Referência / Artigo Modelo (Para guiar o estilo de escrita da revista)",
            "tema_label": "Foco / Tema do Artigo",
            "tema_placeholder": "Descreva o foco específico do seu artigo.",
            "chunk_tracker": "CHUNKS DO ARTIGO",
            "fatos_error": "Envie os fatos ou informe o tema do artigo."
        },
        "resenha_critica": {
            "upload_fatos": "Obra Resenhada e Notas (Livro, artigo ou material a ser analisado)",
            "upload_modelo": "Arquivo de Referência / Resenha Modelo (Para guiar a estrutura crítica)",
            "tema_label": "Obra / Foco da Resenha",
            "tema_placeholder": "Insira o nome do livro/artigo e o foco da sua análise.",
            "chunk_tracker": "CHUNKS DA RESENHA",
            "fatos_error": "Envie a obra ou informe o foco da resenha."
        },
        "resumo_fichamento": {
            "upload_fatos": "Texto original a ser resumido",
            "upload_modelo": "Modelo de Fichamento (Caso queira seguir uma estrutura específica)",
            "tema_label": "Foco do Resumo",
            "tema_placeholder": "Descreva o foco ou tópicos de interesse no resumo.",
            "chunk_tracker": "CHUNKS DO RESUMO",
            "fatos_error": "Envie o texto original ou informe o foco do resumo."
        },
        "relatorio_tecnico": {
            "upload_fatos": "Dados, Métricas e Fatos do Relatório",
            "upload_modelo": "Modelo de Relatório Técnico (Para guiar o formato corporativo/acadêmico)",
            "tema_label": "Escopo do Relatório",
            "tema_placeholder": "Descreva a área técnica ou o objetivo principal deste relatório.",
            "chunk_tracker": "CHUNKS DO RELATÓRIO",
            "fatos_error": "Envie os fatos ou informe o tema do relatório."
        }
    }
    return terms.get(template_id, {
        "upload_fatos": "Material-fonte / Fatos (Base teórica, referencial bibliográfico, citações, dados e argumentos)",
        "upload_modelo": "Arquivo de Referência / Modelo (Para guiar o estilo, tom e ritmo)",
        "tema_label": "Tema / Foco da Produção",
        "tema_placeholder": "Descreva o foco específico deste documento.",
        "chunk_tracker": "CHUNKS DO DOCUMENTO",
        "fatos_error": "Envie o material-fonte ou informe o tema do documento."
    })

terms = get_template_terms(template_id)

# Layout em duas colunas (Esquerda: Upload e Parâmetros, Direita: Pipeline/Resultados)
col_esq, col_dir = st.columns([1.1, 1], gap="large")

# ──────────────────────────────────────────────────────────────────
# COLUNA ESQUERDA: Configurações, Uploads e Seções
# ──────────────────────────────────────────────────────────────────
with col_esq:
    status_template = template_atual.get("status", "funcional")
    mapa_badge = {
        "funcional": ("badge-funcional", "Ativo"),
        "placeholder": ("badge-placeholder", "Em desenvolvimento"),
        "roadmap": ("badge-roadmap", "Planejado"),
    }
    badge_cor, badge_texto = mapa_badge.get(status_template, ("badge-placeholder", status_template))
    
    st.markdown(f"""
    <div style="margin-bottom: 1rem;">
        <span class="badge {badge_cor}">{badge_texto}</span>
        <span style="font-size: 0.8rem; color: var(--cinza-norma); margin-left: 0.5rem; font-style: italic;">
            {template_atual.get('norma', '')}
        </span>
    </div>
    """, unsafe_allow_html=True)
    st.caption(template_atual.get("descricao", ""))

    # Caixa de requisitos
    st.markdown(f"""
    <div class="requisito-box">
        <strong>Requisito do template:</strong><br>
        {template_atual.get("requisitos", "")}
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Uploads separados
    st.markdown("#### Material-fonte")
    
    arquivos_fatos = st.file_uploader(
        terms["upload_fatos"],
        type=["pdf", "txt", "docx"],
        accept_multiple_files=True,
        key="upload_fatos_cap",
    )
    
    arquivos_modelo = st.file_uploader(
        terms["upload_modelo"],
        type=["pdf", "txt", "docx"],
        accept_multiple_files=True,
        key="upload_modelo_tom",
    )

    st.divider()

    # Contexto acadêmico
    st.markdown("#### Contexto acadêmico")
    tema = st.text_input(
        terms["tema_label"],
        placeholder=terms["tema_placeholder"],
        key="tema_geral_eja",
    )

    # Chave API
    api_key = config.get_api_key()
    if not api_key:
        api_key = st.text_input(
            "Chave API Maritaca",
            type="password",
            placeholder="Cole sua chave aqui",
            key="api_key_override_st"
        )

    # Configurações Avançadas Colapsáveis
    if st.button("Configurações avançadas ▾" if not st.session_state["show_advanced"] else "Ocultar configurações ▴"):
        st.session_state["show_advanced"] = not st.session_state["show_advanced"]
        st.rerun()

    if st.session_state["show_advanced"]:
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            modelos_opcoes = list(config.MODELOS.keys())
            modelo_idx = modelos_opcoes.index(config.MODELO_PADRAO_GERACAO)
            modelo_selecionado = st.selectbox(
                "Modelo de IA",
                modelos_opcoes,
                index=modelo_idx,
                format_func=lambda m: config.MODELOS[m]["nome_exibicao"],
                key="modelo_selecionado",
            )
        with col_c2:
            idioma = st.selectbox("Idioma", config.IDIOMAS, key="idioma_selecionado")
        with col_c3:
            formato_export = st.selectbox(
                "Formato",
                config.FORMATOS_EXPORTACAO,
                index=0,
                format_func=lambda f: f.upper(),
                key="formato_export",
            )
        
        col_c4, col_c5 = st.columns(2)
        with col_c4:
            incluir_markers = st.checkbox("Marcadores de mídia", value=True, key="incluir_markers")
        with col_c5:
            usar_memoria = st.checkbox("Usar memória", value=True, key="usar_memoria")
            if usar_memoria:
                escopo_memoria = st.radio("Escopo", ["Tudo", "Última seção"], horizontal=True, key="escopo_memoria")
    else:
        # Padrões se colapsado
        modelo_selecionado = config.MODELO_PADRAO_GERACAO
        idioma = "pt"
        formato_export = "docx"
        incluir_markers = True
        usar_memoria = True
        escopo_memoria = "Tudo"

    st.divider()

    # Seções checklist
    st.markdown("#### Seções do Capítulo")
    secoes_template = template_atual.get("secoes", [])
    secoes_selecionadas = []

    # Inicializar chaves no session_state antes dos botões para garantir consistência
    for sec in secoes_template:
        cb_key = f"sec_cb_{sec['id']}"
        widget_key = f"cb_widget_{sec['id']}"
        obrigatorio = sec.get("obrigatorio", False)
        if cb_key not in st.session_state:
            st.session_state[cb_key] = obrigatorio or sec['numero'] in [1, 2, 5]
        if widget_key not in st.session_state:
            st.session_state[widget_key] = st.session_state[cb_key]

    # Botões todas/nenhuma
    col_t1, col_t2 = st.columns([1, 4])
    with col_t1:
        if st.button("Todas", key="btn_todas_secs"):
            for sec in secoes_template:
                cb_key = f"sec_cb_{sec['id']}"
                widget_key = f"cb_widget_{sec['id']}"
                st.session_state[cb_key] = True
                st.session_state[widget_key] = True
                # Marcar todos os chunks da seção também
                for idx_sub, sp in enumerate(sec.get("sub_prompts", [])):
                    st.session_state[f"chunk_cb_{sec['id']}_{idx_sub}"] = True
            st.rerun()
    with col_t2:
        if st.button("Nenhuma", key="btn_nenhuma_secs"):
            for sec in secoes_template:
                cb_key = f"sec_cb_{sec['id']}"
                widget_key = f"cb_widget_{sec['id']}"
                st.session_state[cb_key] = False
                st.session_state[widget_key] = False
            st.rerun()

    for sec in secoes_template:
        cb_key = f"sec_cb_{sec['id']}"
        widget_key = f"cb_widget_{sec['id']}"
        obrigatorio = sec.get("obrigatorio", False)
        
        # Renderizar com colunas para uma aparência profissional
        col_cb, col_info = st.columns([0.06, 0.94])
        with col_cb:
            # Checkbox oculta o texto padrão e usa o alinhamento
            selecionada = st.checkbox(
                "",
                value=st.session_state[widget_key],
                disabled=False,
                key=widget_key,
                label_visibility="collapsed"
            )
            # Sincroniza a seleção
            st.session_state[cb_key] = selecionada

        with col_info:
            label_title = f"Seção {sec['numero']}: {sec['titulo']}" if sec.get('numero') != -1 else sec['titulo']
            badge_html = '<span class="badge-obrigatoria">Recomendada</span>' if obrigatorio else ''
            active_class = "active" if selecionada else ""
            
            if selecionada and "sub_prompts" in sec and len(sec["sub_prompts"]) > 0:
                # Cabeçalho da seção
                st.markdown(f'<div style="font-weight: 700; color: var(--verde-lousa); font-size: 1.05rem; margin-bottom: 0.6rem; display: flex; align-items: center; gap: 0.5rem; padding-left: 0.2rem;"><span>{label_title}</span>{badge_html}</div>', unsafe_allow_html=True)
                
                # Lista de chunks interativos
                for idx_sub, sp in enumerate(sec["sub_prompts"]):
                    chunk_key = f"chunk_cb_{sec['id']}_{idx_sub}"
                    if chunk_key not in st.session_state:
                        st.session_state[chunk_key] = True
                    
                    txt = sp["comando"] if isinstance(sp, dict) else sp
                    preview = txt[:140] + "..." if len(txt) > 140 else txt
                    
                    # Colunas para alinhar checkbox do sub-chunk e o card
                    col_sub_cb, col_sub_card = st.columns([0.07, 0.93])
                    with col_sub_cb:
                        chunk_sel = st.checkbox(
                            "",
                            value=st.session_state[chunk_key],
                            key=chunk_key,
                            label_visibility="collapsed"
                        )
                    with col_sub_card:
                        active_chunk_class = "" if chunk_sel else "inactive"
                        st.markdown(f'<div class="subchunk-card {active_chunk_class}" style="margin-top: 0.1rem; margin-bottom: 0.2rem;"><span class="subchunk-badge">Chunk {idx_sub+1}</span><span class="subchunk-text">{preview}</span></div>', unsafe_allow_html=True)
            else:
                # Se não selecionado, apenas exibe o cabeçalho como um card colapsado
                st.markdown(f'<div class="section-card-wrapper {active_class}"><div class="section-header-row"><span class="section-title-text">{label_title}</span>{badge_html}</div></div>', unsafe_allow_html=True)
            
            if selecionada:
                secoes_selecionadas.append(sec["id"])

    st.divider()

    # Botão principal
    gerar_btn = st.button(
        "Iniciar redação acadêmica",
        use_container_width=True,
        type="primary",
        key="btn_processar",
        disabled=not api_key,
    )
    if not api_key:
        st.warning("Insira a chave da API para iniciar.")

# ──────────────────────────────────────────────────────────────────
# COLUNA DIREITA: Pipeline e Resultados
# ──────────────────────────────────────────────────────────────────
with col_dir:
    # 1. Pipeline Status
    st.markdown("#### Status do pipeline")
    
    etapas = [
        ("ingestor", "Leitura e processamento da fonte", 0.05, 0.20),
        ("comprehension", "Organização e mapa semântico", 0.25, 0.40),
        ("generator", "Redação acadêmica micro-chunking", 0.45, 0.75),
        ("polisher", "Auditoria de fidelidade e ABNT", 0.78, 0.88),
        ("exporter", "Exportação final e download", 0.90, 1.00),
    ]

    p_frac = st.session_state["progress_frac"]
    p_text = st.session_state["progress_text"]

    if st.session_state["pipeline_rodou"] or p_frac > 0:
        # Progress bar
        st.progress(p_frac, text=p_text)

        # Pipeline steps
        for step_id, step_name, start, end in etapas:
            c_class = "pipeline-step-box"
            s_badge = "Aguardando"
            if p_frac >= end:
                c_class += " done"
                s_badge = "Concluído"
            elif p_frac >= start:
                c_class += " active"
                s_badge = "Processando"
            
            st.markdown(f"""
            <div class="{c_class}">
                <strong>{step_name}</strong>
                <span class="badge badge-funcional" style="font-size:0.65rem;">{s_badge}</span>
            </div>
            """, unsafe_allow_html=True)

        # Chunk Tracker
        c_atual = st.session_state["chunk_atual"]
        c_total = st.session_state["total_chunks"]
        c_eta = st.session_state["eta"]
        if c_total > 0:
            st.markdown(f"""
            <div class="chunk-tracker-box">
                <div style="display:flex; justify-content:space-between; font-size:0.8rem; font-weight:700;">
                    <span style="color:var(--verde-lousa);">{terms["chunk_tracker"]}</span>
                    <span style="font-family:monospace; color:var(--cinza-norma);">{c_atual}/{c_total} {c_eta}</span>
                </div>
                <div class="chunk-bar-container">
                    {"".join([f'<div class="chunk-bar-segment {"done" if i < c_atual-1 else "active" if i == c_atual-1 else ""}"></div>' for i in range(c_total)])}
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Logs
        if st.session_state["pipeline_log"]:
            with st.expander("Log do pipeline", expanded=False):
                log_html = "".join([f"<div style='margin-bottom:0.3rem;'>• {line}</div>" for line in st.session_state["pipeline_log"]])
                st.markdown(f'<div class="log-console-box">{log_html}</div>', unsafe_allow_html=True)
    else:
        # Empty State
        st.markdown("""
        <div class="empty-state-box">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#0A5C2F" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-bottom: 0.5rem;">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
                <polyline points="10 9 9 9 8 9"></polyline>
            </svg>
            <strong style="color: var(--verde-lousa); font-size: 1.1rem;">Aguardando material-fonte</strong>
            <p style="color: var(--cinza-norma); font-size: 0.85rem; max-width: 360px; margin-top:0.3rem;">
                Envie os arquivos na coluna esquerda, selecione as seções e clique em "Iniciar redação acadêmica" para iniciar o processamento.
            </p>
        </div>
        """, unsafe_allow_html=True)

    # ──────────────────────────────────────────────────────────────────
    # Execução do Pipeline
    # ──────────────────────────────────────────────────────────────────
    if gerar_btn:
        if not arquivos_fatos and not tema:
            st.error(terms["fatos_error"])
            st.stop()
        if not secoes_selecionadas:
            st.error("Selecione pelo menos uma seção para gerar.")
            st.stop()

        log = []
        st.session_state["pipeline_log"] = log
        st.session_state["pipeline_rodou"] = False
        st.session_state["progress_frac"] = 0.0
        st.session_state["progress_text"] = "Iniciando..."
        st.session_state["chunk_atual"] = 0
        st.session_state["total_chunks"] = 0
        st.session_state["eta"] = ""

        def log_status(msg: str):
            # Remove emojis do log
            cleaned = msg.replace("🤖", "").replace("📥", "").replace("🧠", "").replace("✍️", "").replace("🧹", "").replace("📝", "").replace("✅", "").replace("❌", "").strip()
            log.append(cleaned)
            st.session_state["progress_text"] = cleaned

        try:
            # 1. Ingestão
            st.session_state["progress_frac"] = 0.05
            log_status("Lendo e normalizando o material-fonte...")
            
            texto_fatos_list = []
            texto_modelo_list = []
            hashes = []
            metadados_gerais = []
            idx = 0
            
            if arquivos_fatos:
                for arg in arquivos_fatos:
                    arg_bytes = arg.read()
                    i_res = ingest_document(arg_bytes, arg.name, status_callback=log_status)
                    bloco = f"\n--- INÍCIO DO DOCUMENTO {idx+1}: {arg.name} ---\n{i_res.texto}\n--- FIM DO DOCUMENTO {idx+1} ---\n"
                    texto_fatos_list.append(bloco)
                    hashes.append(i_res.hash_conteudo)
                    metadados_gerais.append(i_res.metadados)
                    idx += 1
            
            if arquivos_modelo:
                for arg in arquivos_modelo:
                    arg_bytes = arg.read()
                    i_res = ingest_document(arg_bytes, arg.name, status_callback=log_status)
                    bloco = f"\n--- INÍCIO DO DOCUMENTO {idx+1}: {arg.name} ---\n{i_res.texto}\n--- FIM DO DOCUMENTO {idx+1} ---\n"
                    texto_modelo_list.append(bloco)
                    hashes.append(i_res.hash_conteudo)
                    metadados_gerais.append(i_res.metadados)
                    idx += 1

            texto_fatos = "\n".join(texto_fatos_list)
            texto_modelo = "\n".join(texto_modelo_list)
            texto_fonte = texto_fatos + "\n" + texto_modelo
            
            hash_total = hashlib.sha256(texto_fonte.encode()).hexdigest()
            ingestor_result = IngestorResult(
                texto=texto_fonte,
                hash_conteudo=hash_total,
                metadados={"arquivos": metadados_gerais},
                formato="MULTIPLO"
            )
            st.session_state["ingestor_result"] = ingestor_result
            st.session_state["progress_frac"] = 0.20
            log_status("Leitura da fonte concluída.")

            cache_key = f"{hash_total}__{tema}__{modelo_selecionado}__{idioma}__{'-'.join(sorted(secoes_selecionadas))}__{incluir_markers}"
            
            if cache_key in st.session_state["cache"]:
                log_status("Reutilizando resultado anterior do cache.")
                cached = st.session_state["cache"][cache_key]
                st.session_state["comprehension_result"] = cached.get("comprehension_result")
                st.session_state["generator_results"] = cached.get("generator_results")
                st.session_state["polish_results"] = cached.get("polish_results")
                st.session_state["progress_frac"] = 1.0
                st.session_state["pipeline_rodou"] = True
            else:
                # 2. Compreensão
                st.session_state["progress_frac"] = 0.25
                log_status("Organizando temas, conceitos e evidências (Bardin)...")
                comp_result = comprehend(texto_fonte, status_callback=log_status)
                st.session_state["comprehension_result"] = comp_result
                st.session_state["progress_frac"] = 0.40
                log_status("Mapa semântico concluído.")

                # 3. Geração
                st.session_state["progress_frac"] = 0.45
                log_status("Redigindo as seções selecionadas...")
                
                # Filtragem profunda do template para apenas chunks selecionados
                import copy
                template_exec = copy.deepcopy(template_atual)
                
                # Filtra os sub_prompts das seções
                for sec_obj in template_exec.get("secoes", []):
                    if sec_obj["id"] in secoes_selecionadas:
                        filtered_sub_prompts = []
                        for idx_sub, sp in enumerate(sec_obj.get("sub_prompts", [])):
                            chunk_key = f"chunk_cb_{sec_obj['id']}_{idx_sub}"
                            if st.session_state.get(chunk_key, True):
                                filtered_sub_prompts.append(sp)
                        sec_obj["sub_prompts"] = filtered_sub_prompts
                
                # Filtra seções selecionadas para conter apenas as que têm pelo menos 1 chunk marcado
                secoes_com_chunks = []
                for s_id in secoes_selecionadas:
                    sec_obj = next((s for s in template_exec.get("secoes", []) if s["id"] == s_id), None)
                    if sec_obj and len(sec_obj.get("sub_prompts", [])) > 0:
                        secoes_com_chunks.append(s_id)
                secoes_selecionadas = secoes_com_chunks
                
                if not secoes_selecionadas:
                    st.error("Selecione pelo menos uma seção com pelo menos um chunk ativo para gerar.")
                    st.stop()
                
                # Conta total de chunks filtrados para o tracker
                total_chunks = 0
                for s_id in secoes_selecionadas:
                    sec_obj = next((s for s in template_exec.get("secoes", []) if s["id"] == s_id), None)
                    if sec_obj:
                        total_chunks += len(sec_obj.get("sub_prompts", []))
                st.session_state["total_chunks"] = total_chunks
                st.session_state["chunk_atual"] = 1

                def gen_progress(frac):
                    st.session_state["progress_frac"] = 0.45 + frac * 0.30
                    # Atualiza chunk atual no tracker
                    curr = int(frac * total_chunks) + 1
                    st.session_state["chunk_atual"] = min(curr, total_chunks)
                    # Calcula ETA simples
                    eta_sec = int((total_chunks - curr + 1) * 20)
                    st.session_state["eta"] = f"| Restam ~{eta_sec}s" if eta_sec > 0 else ""

                # Memória
                contexto_anterior = None
                if usar_memoria and st.session_state["memoria_tese"]:
                    scope_key = "tudo" if escopo_memoria == "Tudo" else "ultima"
                    contexto_anterior = persistence.build_context(st.session_state["memoria_tese"], scope=scope_key)

                generator_results = generate(
                    texto_fatos=texto_fatos,
                    texto_modelo=texto_modelo,
                    template=template_exec,
                    secoes_selecionadas=secoes_selecionadas,
                    tema=tema,
                    idioma=idioma,
                    api_key=api_key,
                    modelo_geracao=modelo_selecionado,
                    incluir_markers=incluir_markers,
                    contexto_anterior=contexto_anterior,
                    status_callback=log_status,
                    progress_callback=gen_progress,
                )
                st.session_state["generator_results"] = generator_results
                st.session_state["progress_frac"] = 0.75
                log_status("Geração concluída.")

                # 4. Polimento / Auditoria
                st.session_state["progress_frac"] = 0.78
                log_status("Auditando fidelidade acadêmica e normas ABNT...")
                polish_results = polish(
                    secoes_geradas=generator_results,
                    texto_fonte=texto_fatos,
                    api_key=api_key,
                    status_callback=log_status,
                )
                st.session_state["polish_results"] = polish_results
                
                # Salva cache
                st.session_state["cache"][cache_key] = {
                    "comprehension_result": comp_result,
                    "generator_results": generator_results,
                    "polish_results": polish_results
                }
                st.session_state["progress_frac"] = 0.88
                log_status("Auditoria de fidelidade concluída.")

            # 5. Exportação
            st.session_state["progress_frac"] = 0.90
            log_status("Preparando o arquivo de exportação final...")
            
            polish_results = st.session_state["polish_results"]
            export_bytes, export_nome, export_mime = export(
                polish_results=polish_results,
                formato=formato_export,
                tema=tema or "Tese de Doutorado",
                idioma=idioma,
                status_callback=None
            )
            st.session_state["export_bytes"] = export_bytes
            st.session_state["export_nome"] = export_nome
            st.session_state["export_mime"] = export_mime
            st.session_state["export_format"] = formato_export

            # Memória persistente
            for res in polish_results:
                st.session_state["memoria_tese"] = [m for m in st.session_state["memoria_tese"] if m["secao_id"] != res.secao_id]
                st.session_state["memoria_tese"].append({
                    "secao_id": res.secao_id,
                    "secao_titulo": res.secao_titulo,
                    "texto": res.texto_polido,
                })
            persistence.save_session(st.session_state["memoria_tese"])

            st.session_state["progress_frac"] = 1.0
            st.session_state["pipeline_rodou"] = True
            log_status("Documento gerado com sucesso!")
            st.rerun()

        except Exception as e:
            st.session_state["progress_frac"] = 0.0
            st.error(f"Erro no processamento: {e}")
            log_status(f"ERRO: {e}")

    # ──────────────────────────────────────────────────────────────────
    # RESULTADOS / DASHBOARD
    # ──────────────────────────────────────────────────────────────────
    if st.session_state.get("pipeline_rodou") and st.session_state.get("polish_results"):
        st.markdown("---")
        st.markdown("### Painel de Resultados")

        tab_texto, tab_analise, tab_auditoria = st.tabs([
            "Texto do Capítulo",
            "Análise Semântica (Bardin)",
            "Auditoria ABNT (Consolidada)"
        ])

        # ABA 1: Texto do Capítulo
        with tab_texto:
            polish_results = st.session_state["polish_results"]
            tabs_secoes = [r.secao_titulo for r in polish_results]
            
            if polish_results:
                sec_tabs = st.tabs(tabs_secoes)
                for s_tab, res in zip(sec_tabs, polish_results):
                    with s_tab:
                        st.markdown(res.texto_polido)
                        
                        # Auditoria detalhada da seção
                        if hasattr(res, "aprovada"):
                            v_box_class = "verdict-success" if res.aprovada else "verdict-alert"
                            v_msg = "Aprovado" if res.aprovada else "Alertas Detectados"
                            
                            with st.expander(f"Relatório de Auditoria — {v_msg}", expanded=not res.aprovada):
                                st.markdown(f"**Veredito:** {res.relatorio}")
                                
                                # Métricas
                                f_status = res.fidelidade.get("status", "N/A")
                                o_status = res.omissao.get("status", "N/A")
                                v_status = res.voz.get("status", "N/A")
                                
                                dot_fid = '<span class="status-dot ok"></span>' if f_status == "OK" else '<span class="status-dot alerta"></span>'
                                dot_omi = '<span class="status-dot ok"></span>' if o_status == "OK" else '<span class="status-dot alerta"></span>'
                                dot_voz = '<span class="status-dot ok"></span>' if v_status == "OK" else '<span class="status-dot alerta"></span>'
                                
                                st.markdown(f"""
                                <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 1rem;">
                                    <div style="background:#F8FAF7; padding:0.6rem; border:1px solid var(--borda); border-radius:6px; text-align:center;">
                                        <small style="color:var(--cinza-norma); font-weight:600;">Fidelidade</small><br>
                                        {dot_fid} <strong>{f_status}</strong>
                                    </div>
                                    <div style="background:#F8FAF7; padding:0.6rem; border:1px solid var(--borda); border-radius:6px; text-align:center;">
                                        <small style="color:var(--cinza-norma); font-weight:600;">Omissão</small><br>
                                        {dot_omi} <strong>{o_status}</strong>
                                    </div>
                                    <div style="background:#F8FAF7; padding:0.6rem; border:1px solid var(--borda); border-radius:6px; text-align:center;">
                                        <small style="color:var(--cinza-norma); font-weight:600;">Voz (Verbatim)</small><br>
                                        {dot_voz} <strong>{v_status}</strong>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                if not res.aprovada:
                                    st.markdown(f"""
                                    <div style="margin-top: 1rem; padding: 0.8rem; background: #FFFbeb; border: 1px solid #F59e0b; border-radius: 6px;">
                                        <strong style="color: #b45309;">Detalhes dos Alertas:</strong><br>
                                        <span style="font-size:0.85rem; color:#78350f;">
                                            - <strong>Fidelidade:</strong> {res.fidelidade.get('detalhes', 'N/D')}<br>
                                            - <strong>Omissão:</strong> {res.omissao.get('detalhes', 'N/D')}<br>
                                            - <strong>Voz:</strong> {res.voz.get('detalhes', 'N/D')}
                                        </span>
                                    </div>
                                    """, unsafe_allow_html=True)

        # ABA 2: Análise Semântica (Bardin)
        with tab_analise:
            if st.session_state.get("comprehension_result"):
                comp_res = st.session_state["comprehension_result"]
                st.markdown("#### Classificação de Conteúdo")
                
                col_b1, col_b2 = st.columns([1, 2])
                with col_b1:
                    st.markdown(f"""
                    <div style="background: var(--verde-papel); padding: 1rem; border-radius: 10px; border: 1px solid var(--borda);">
                        <small style="color: var(--verde-escriba); font-weight: 700; text-transform: uppercase;">Classificação Bardin</small>
                        <p style="font-size: 1.1rem; margin-top: 0.4rem; font-weight: 700; color: var(--verde-lousa);">{comp_res.classificacao}</p>
                    </div>
                    """, unsafe_allow_html=True)
                with col_b2:
                    st.markdown(f"""
                    <div style="background: var(--branco); padding: 1rem; border-radius: 10px; border: 1px solid var(--borda);">
                        <small style="color: var(--cinza-norma); font-weight: 700; text-transform: uppercase;">Resumo Qualitativo</small>
                        <p style="font-size: 0.92rem; margin-top: 0.4rem; line-height: 1.5;">{comp_res.resumo_academico}</p>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("#### Categorias Temáticas Extraídas")
                if comp_res.temas:
                    for idx, tema_obj in enumerate(comp_res.temas):
                        st.markdown(f"""
                        <div style="background: var(--branco); padding: 1.2rem; border-radius: 10px; border: 1px solid var(--borda); margin-bottom: 0.8rem;">
                            <strong style="color: var(--verde-escriba); font-size: 1rem;">Categoria {idx+1}: {tema_obj.get('titulo', '')}</strong>
                            <p style="font-style: italic; font-size: 0.85rem; color: var(--cinza-norma); margin: 0.3rem 0 0.6rem 0;">{tema_obj.get('resumo_tema', '')}</p>
                            <div style="border-left: 2px solid var(--verde-acao); padding-left: 0.8rem; font-size:0.88rem;">
                                {"".join([f"<div style='margin-bottom:0.25rem;'>- {pt}</div>" for pt in tema_obj.get("pontos_chave", [])])}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                st.markdown("#### Banco de Evidências (Citações Diretas)")
                if comp_res.citacoes_chave:
                    for cit in comp_res.citacoes_chave:
                        st.markdown(f"""
                        <div style="background: var(--papel); border-left: 4px solid var(--verde-escriba); padding: 1rem; border-radius: 0 8px 8px 0; margin-bottom: 0.6rem; border-top: 1px solid var(--borda); border-right: 1px solid var(--borda); border-bottom: 1px solid var(--borda);">
                            <span style="font-style: italic; font-size: 0.92rem; color: var(--grafite);">“{cit.get('texto', '').strip()}”</span><br>
                            <small style="color: var(--cinza-norma); display: block; margin-top: 0.4rem;">— <strong>{cit.get('contexto_autor', 'N/D')}</strong> | {cit.get('pagina_paragrafo', 'N/D')}</small>
                        </div>
                        """, unsafe_allow_html=True)

        # ABA 3: Auditoria ABNT (Consolidada)
        with tab_auditoria:
            st.markdown("#### Relatório Consolidado de Seções")
            for res in st.session_state["polish_results"]:
                if hasattr(res, "aprovada"):
                    v_pill_class = "aprovado" if res.aprovada else "alerta"
                    v_pill_text = "Aprovado" if res.aprovada else "Alerta"
                    st.markdown(f"""
                    <div style="background: var(--papel); border: 1px solid var(--borda); border-radius: 10px; padding: 1rem; margin-bottom: 0.8rem; display: grid; grid-template-columns: 1fr auto; gap: 10px; align-items: center;">
                        <div>
                            <strong style="color: var(--grafite);">{res.secao_titulo}</strong><br>
                            <small style="color: var(--cinza-norma);">{res.relatorio}</small>
                        </div>
                        <span class="badge {'badge-funcional' if res.aprovada else 'badge-alerta'}" style="text-align:center;">{v_pill_text}</span>
                    </div>
                    """, unsafe_allow_html=True)

        # Ações de exportação/download
        st.markdown("---")
        st.markdown("#### Exportar documento final")
        eb = st.session_state.get("export_bytes")
        en = st.session_state.get("export_nome", "documento")
        em = st.session_state.get("export_mime", "text/plain")
        
        st.download_button(
            "Baixar documento final",
            eb,
            en,
            em,
            use_container_width=True,
            key="dl_main_dashboard"
        )

# ──────────────────────────────────────────────────────────────────
# Rodapé
# ──────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="escriba-footer">
    <strong>Escriba</strong> — Central acadêmica de geração com auditoria de fidelidade<br>
    Desenvolvido por <strong>{config.APP_AUTOR}</strong> • {config.APP_ANO} •
    Powered by <strong>Maritaca Sabiá</strong>
</div>
""", unsafe_allow_html=True)
