"""
app.py — Orquestrador Principal / Interface Streamlit
Escriba v2.0

Pipeline:
    Upload → Ingestão → Compreensão → Geração → Polimento → Exportação
"""

import streamlit as st
import json

import sys

import config
import hashlib

import modules.persistence as persistence

# Inicializa diretórios
persistence.ensure_dir()

from modules.ingestor import ingest_document, IngestorResult
from modules.comprehension import comprehend
from modules.generator import generate
from modules.polisher import polish
from modules.exporter import export

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
# CSS Custom — Design premium escuro
# ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Background geral */
    .stApp {
        background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
        color: #e8e8f0;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: rgba(255,255,255,0.04);
        border-right: 1px solid rgba(255,255,255,0.08);
    }

    /* Header principal */
    .escriba-header {
        text-align: center;
        padding: 2rem 0 1rem;
    }
    .escriba-header h1 {
        font-size: 2.8rem;
        font-weight: 700;
        background: linear-gradient(135deg, #a78bfa, #60a5fa, #34d399);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0;
    }
    .escriba-header p {
        color: #94a3b8;
        font-size: 1rem;
        margin-top: 0.4rem;
    }

    /* Cards de módulo / pipeline */
    .pipeline-card {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.6rem;
        transition: all 0.2s ease;
    }
    .pipeline-card:hover {
        background: rgba(255,255,255,0.08);
        border-color: rgba(167,139,250,0.4);
    }
    .pipeline-card.active {
        border-color: #a78bfa;
        background: rgba(167,139,250,0.1);
    }
    .pipeline-card.done {
        border-color: #34d399;
        background: rgba(52,211,153,0.08);
    }

    /* Badges de status */
    .badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 999px;
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    .badge-placeholder { background: rgba(251,191,36,0.2); color: #fbbf24; }
    .badge-funcional  { background: rgba(52,211,153,0.2); color: #34d399; }
    .badge-roadmap    { background: rgba(96,165,250,0.2); color: #60a5fa; }

    /* Botões */
    .stButton > button {
        background: linear-gradient(135deg, #7c3aed, #2563eb);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.5rem 1.5rem;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #8b5cf6, #3b82f6);
        transform: translateY(-1px);
        box-shadow: 0 4px 15px rgba(124,58,237,0.4);
    }

    /* Download buttons */
    [data-testid="stDownloadButton"] button {
        background: rgba(52,211,153,0.15) !important;
        color: #34d399 !important;
        border: 1px solid rgba(52,211,153,0.4) !important;
        border-radius: 8px;
    }

    /* Selectbox e inputs */
    .stSelectbox > div > div,
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: rgba(255,255,255,0.06) !important;
        border-color: rgba(255,255,255,0.12) !important;
        color: #e8e8f0 !important;
    }

    /* Expanders */
    .streamlit-expanderHeader {
        background: rgba(255,255,255,0.04) !important;
        border-radius: 8px;
    }

    /* Rodapé */
    .escriba-footer {
        text-align: center;
        color: #475569;
        font-size: 0.75rem;
        padding: 2rem 0 1rem;
        border-top: 1px solid rgba(255,255,255,0.06);
        margin-top: 3rem;
    }

    /* Oculta rodapé padrão do Streamlit */
    footer { visibility: hidden; }

    /* Separador */
    hr { border-color: rgba(255,255,255,0.08); }
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
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# ──────────────────────────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="escriba-header">
    <h1>Escriba v2.0</h1>
    <p>Central modular de processamento acadêmico com IA • Maritaca Sabiá</p>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────
# Sidebar — Configurações
# ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Configurações")

    # API Key
    api_key = config.get_api_key()
    if not api_key:
        api_key = st.text_input(
            "Chave API Maritaca",
            type="password",
            placeholder="Cole sua chave aqui",
            help="Configure em .streamlit/secrets.toml para não precisar inserir manualmente.",
            key="api_key_input"
        )
    else:
        st.success("API Key carregada automaticamente")

    st.divider()

    # Seleção de Template
    templates_disponiveis = config.listar_templates()
    nomes_templates = {t["nome"]: t["id"] for t in templates_disponiveis}
    lista_nomes = list(nomes_templates.keys())
    
    # Define o índice padrão como "Módulo Educacional" (se existir)
    default_idx = next((i for i, name in enumerate(lista_nomes) if "Módulo Educacional" in name), 0)

    template_nome_selecionado = st.selectbox(
        "Formato de Saída",
        lista_nomes,
        index=default_idx,
        key="template_selecionado",
        help="O Módulo Educacional é o template principal e totalmente funcional."
    )
    template_id = nomes_templates[template_nome_selecionado]
    template_atual = config.carregar_template(template_id)

    # Badge de status do template
    status_template = template_atual.get("status", "funcional")
    badge_cor = "badge-funcional" if status_template == "funcional" else "badge-placeholder"
    st.markdown(f'<span class="badge {badge_cor}">{status_template}</span>', unsafe_allow_html=True)
    st.caption(template_atual.get("descricao", ""))

    # Requisitos dinâmicos
    requisitos = template_atual.get("requisitos", "Requer material-fonte estruturado.")
    st.info(f"**Requisito de Input:**\n{requisitos}")

    st.divider()

    # Modelo
    modelos_opcoes = list(config.MODELOS.keys())
    modelo_idx = modelos_opcoes.index(config.MODELO_PADRAO_GERACAO)
    modelo_selecionado = st.selectbox(
        "Modelo de Geração",
        modelos_opcoes,
        index=modelo_idx,
        format_func=lambda m: config.MODELOS[m]["nome_exibicao"],
        key="modelo_selecionado",
    )
    info_modelo = config.MODELOS[modelo_selecionado]
    st.caption(
        f"Contexto: {info_modelo['contexto_tokens']:,} tokens | "
        f"Custo: R$ {info_modelo['custo_output_por_milhao_brl']:.2f}/1M tokens"
    )

    st.divider()

    # Idioma
    idioma = st.selectbox("Idioma de Saída", config.IDIOMAS, key="idioma_selecionado")

    st.divider()

    # Formato de exportação
    formato_export = st.selectbox(
        "Formato de Download",
        config.FORMATOS_EXPORTACAO,
        index=0,
        format_func=lambda f: f.upper(),
        key="formato_export",
    )

    st.divider()

    # Marcadores de Mídia (Modular)
    incluir_markers = st.checkbox(
        "Sugestões de Mídia",
        value=True,
        help="Inclui marcadores [VÍDEO], [ÁUDIO], [FIGURA] no texto gerado para design instrucional.",
        key="incluir_markers"
    )

    st.divider()
    
    # Memória de Sessão
    st.markdown("### Memória de Tese")
    usar_memoria = st.checkbox("Usar contexto de sessões anteriores", value=True)
    escopo_memoria = st.radio("Escopo da Memória", ["Tudo", "Última seção"], horizontal=True)
    if st.button("Limpar Memória"):
        persistence.clear_session()
        st.session_state["memoria_tese"] = []
        st.rerun()

    st.divider()
    st.markdown(f"""
    <div style="font-size: 0.75rem; color: #475569; text-align: center;">
        <strong>Escriba v2.0</strong><br>
        Desenvolvido por {config.APP_AUTOR} • {config.APP_ANO}
    </div>
    """, unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────
# Corpo Principal — Layout em colunas
# ──────────────────────────────────────────────────────────────────
col_esq, col_dir = st.columns([1.1, 1], gap="large")

# ── COLUNA ESQUERDA: Upload + Parâmetros + Seções ──
with col_esq:
    st.warning("**Zero Alucinação**: O Escriba foi projetado para seguir **estritamente** o seu material de referência. O que não estiver na fonte, não estará no texto final.")

    st.markdown("#### Documento Fonte")
    arquivos = st.file_uploader(
        "Envie um ou mais arquivos (PDF, DOCX ou TXT)",
        type=["pdf", "txt", "docx"],
        accept_multiple_files=True,
        key="arquivo_upload",
        label_visibility="collapsed",
    )
    if arquivos:
        if len(arquivos) == 1:
            st.success(f"**{arquivos[0].name}** carregado")
        else:
            st.success(f"**{len(arquivos)}** arquivos carregados")

    st.divider()

    st.markdown("#### Tema Geral")
    tema = st.text_input(
        "Descreva brevemente o tema do documento:",
        placeholder="Ex: Introdução à Programação em Python para iniciantes",
        key="tema_geral",
        label_visibility="collapsed",
    )

    st.divider()

    # Seleção de seções
    st.markdown(f"#### Seções — *{template_nome_selecionado}*")
    secoes_template = template_atual.get("secoes", [])
    secoes_selecionadas = []

    for secao in secoes_template:
        obrigatorio = secao.get("obrigatorio", False)
        selecionada = st.checkbox(
            f"{'Obrigatório ' if obrigatorio else ''}Seção {secao['numero']}: {secao['titulo']}",
            value=obrigatorio or (not obrigatorio and secao['numero'] in [1, 2, 5]),
            key=f"sec_{secao['id']}",
            disabled=False,
        )
        if selecionada:
            secoes_selecionadas.append(secao["id"])

    st.divider()

    # Botão principal
    gerar_btn = st.button(
        "Processar Documento",
        use_container_width=True,
        type="primary",
        key="btn_processar",
        disabled=not api_key,
    )
    if not api_key:
        st.warning("Configure a API Key na barra lateral para processar.")

# ── COLUNA DIREITA: Pipeline + Resultado ──
with col_dir:
    st.markdown("#### Pipeline de Processamento")

    # Status cards do pipeline
    etapas = [
        ("ingestor", "Módulo 1 — Ingestão", "Funcional", "badge-funcional"),
        ("comprehension", "Módulo 2 — Compreensão", "Placeholder (CoVe roadmap)", "badge-placeholder"),
        ("generator", "Módulo 3 — Geração", "Funcional", "badge-funcional"),
        ("polisher", "Módulo 4 — Polimento", "Placeholder (sabia-4 roadmap)", "badge-placeholder"),
        ("exporter", "Módulo 5 — Exportação", "Funcional", "badge-funcional"),
    ]

    for etapa_id, etapa_nome, etapa_status, badge_class in etapas:
        estado = ""
        if st.session_state.get("pipeline_rodou"):
            estado = "done"
        st.markdown(f"""
        <div class="pipeline-card {estado}">
            <strong>{etapa_nome}</strong>
            <span class="badge {badge_class}" style="float:right">{etapa_status}</span>
        </div>
        """, unsafe_allow_html=True)

    # Log do pipeline
    if st.session_state["pipeline_log"]:
        with st.expander("Log de Execução", expanded=True):
            for linha in st.session_state["pipeline_log"]:
                st.markdown(f"- {linha}")

# ──────────────────────────────────────────────────────────────────
# Execução do Pipeline
# ──────────────────────────────────────────────────────────────────
if gerar_btn:
    if not tema and not arquivos:
        st.error("Informe o tema geral ou envie pelo menos um arquivo para processar.")
        st.stop()
    if not secoes_selecionadas:
        st.error("Selecione ao menos uma seção para gerar.")
        st.stop()

    log = []
    st.session_state["pipeline_log"] = log
    st.session_state["pipeline_rodou"] = False

    # Barra de progresso central
    st.markdown("---")
    st.markdown("#### Processando...")
    progress_bar = st.progress(0, text="Iniciando pipeline...")
    status_area = st.empty()

    def log_status(msg: str):
        log.append(msg)
        status_area.info(msg)

    try:
        # ─── Módulo 1: Ingestão ───────────────────────────
        progress_bar.progress(5, text="Módulo 1: Ingestão...")
        if arquivos:
            texto_fatos_list = []
            texto_modelo_list = []
            hashes = []
            metadados_gerais = []
            for idx, arg in enumerate(arquivos):
                arg_bytes = arg.read()
                i_res = ingest_document(arg_bytes, arg.name, status_callback=log_status)
                
                bloco = f"\n--- INÍCIO DO DOCUMENTO {idx+1}: {arg.name} ---\n{i_res.texto}\n--- FIM DO DOCUMENTO {idx+1} ---\n"
                
                nome_lower = arg.name.lower()
                if "modelo" in nome_lower or "formato" in nome_lower or "tese" in nome_lower:
                    texto_modelo_list.append(bloco)
                else:
                    texto_fatos_list.append(bloco)
                    
                hashes.append(i_res.hash_conteudo)
                metadados_gerais.append(i_res.metadados)
            
            texto_fatos = "\n".join(texto_fatos_list)
            texto_modelo = "\n".join(texto_modelo_list)
            texto_fonte = texto_fatos + "\n" + texto_modelo
            hash_total = hashlib.sha256("".join(hashes).encode()).hexdigest()
            from modules.ingestor import IngestorResult
            ingestor_result = IngestorResult(
                texto=texto_fonte,
                hash_conteudo=hash_total,
                metadados={"arquivos": metadados_gerais},
                formato="MULTIPLO"
            )
            cache_key = f"{hash_total}__{tema}__{modelo_selecionado}__{idioma}__{'-'.join(sorted(secoes_selecionadas))}__{incluir_markers}"
        else:
            texto_fatos = ""
            texto_modelo = ""
            texto_fonte = ""
            cache_key = f"no_file__{tema}__{modelo_selecionado}__{idioma}__{incluir_markers}"
            log_status("Sem arquivo — usando apenas o tema informado.")
            log_status("Módulo 1 concluído")

        st.session_state["ingestor_result"] = ingestor_result if arquivos else None
        progress_bar.progress(20, text="Módulo 1 concluído")

        # Cache check
        if cache_key in st.session_state["cache"]:
            log_status("Conteúdo idêntico encontrado no cache! Reutilizando resultado anterior.")
            polish_results = st.session_state["cache"][cache_key]
            log_status("Cache carregado")
            progress_bar.progress(90, text="Cache carregado")
        else:
            # ─── Módulo 2: Compreensão ──────────────────────────
            progress_bar.progress(25, text="Módulo 2: Compreensão...")
            comp_result = comprehend(texto_fonte, status_callback=log_status)
            st.session_state["comprehension_result"] = comp_result
            log_status("Módulo 2 concluído")
            progress_bar.progress(40, text="Módulo 2 concluído")

            # ─── Módulo 3: Geração ──────────────────────────────
            progress_bar.progress(45, text="Módulo 3: Geração com IA...")
            total_secoes = len(secoes_selecionadas)

            def gen_progress(frac):
                val = int(45 + frac * 30)
                progress_bar.progress(val, text=f"Gerando seções... {int(frac * 100)}%")

            # Prepara contexto anterior se a memória estiver ativa
            contexto_anterior = None
            if usar_memoria and st.session_state["memoria_tese"]:
                scope_key = "tudo" if escopo_memoria == "Tudo" else "ultima"
                contexto_anterior = persistence.build_context(st.session_state["memoria_tese"], scope=scope_key)

            generator_results = generate(
                texto_fatos=texto_fatos,
                texto_modelo=texto_modelo,
                template=template_atual,
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
            progress_bar.progress(75, text="Módulo 3 concluído")

            # ─── Módulo 4: Polimento ────────────────────────────
            progress_bar.progress(78, text="Módulo 4: Polimento e auditoria...")
            polish_results = polish(
                secoes_geradas=generator_results,
                texto_fonte=texto_fatos,
                api_key=api_key,
                status_callback=log_status,
            )
            st.session_state["polish_results"] = polish_results
            st.session_state["cache"][cache_key] = polish_results
            progress_bar.progress(88, text="Módulo 4 concluído")

        # ─── Módulo 5: Exportação ───────────────────────────
        progress_bar.progress(90, text="Módulo 5: Exportação...")
        
        # Gera estritamente O FORMATO que o usuário pediu na barra lateral 
        # (PDF gera timeout no ReportLab se o gerador Deep Chunking criar mais de 30 páginas com Regex pesadas, então poupamos processamento).
        export_bytes, export_nome, export_mime = export(
            polish_results=polish_results,
            formato=formato_export,
            tema=tema or "Documento Gerado",
            idioma=idioma,
            status_callback=None
        )
        
        st.session_state["export_bytes"] = export_bytes
        st.session_state["export_nome"] = export_nome
        st.session_state["export_mime"] = export_mime
        st.session_state["export_format"] = formato_export
        # Salva na memória persistente (Tese)
        for res in polish_results:
            # Evita duplicatas se rodar a mesma seção
            st.session_state["memoria_tese"] = [m for m in st.session_state["memoria_tese"] if m["secao_id"] != res.secao_id]
            st.session_state["memoria_tese"].append({
                "secao_id": res.secao_id,
                "secao_titulo": res.secao_titulo,
                "texto": res.texto_polido,
            })
        
        persistence.save_session(st.session_state["memoria_tese"])
        
        progress_bar.progress(100, text="Pipeline concluído!")
        st.session_state["pipeline_rodou"] = True

    except Exception as e:
        progress_bar.progress(0, text="Erro no pipeline")
        st.error(f"**Erro durante o processamento:** {e}")
        log_status(f"ERRO: {e}")

# ──────────────────────────────────────────────────────────────────
# Resultado — Preview e Downloads
# ──────────────────────────────────────────────────────────────────
if st.session_state.get("export_bytes") and st.session_state.get("pipeline_rodou"):
    st.markdown("---")
    
    # ─── MAPA SEMÂNTICO (ANÁLISE QUALITATIVA DE BARDIN) ──────────────────
    if st.session_state.get("comprehension_result"):
        comp_res = st.session_state["comprehension_result"]
        with st.expander("🧠 Análise de Conteúdo & Mapa Semântico (Bardin)", expanded=True):
            st.markdown("#### 📋 Caracterização e Síntese")
            c1, c2 = st.columns([1, 2])
            with c1:
                st.markdown(f"""
                <div style="background: rgba(255,255,255,0.04); padding: 1rem; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08); height: 100%;">
                    <small style="color: #a78bfa; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Classificação Metodológica</small>
                    <p style="font-size: 1.1rem; margin-top: 0.5rem; font-weight: 500; color: #f8fafc;">{comp_res.classificacao}</p>
                </div>
                """, unsafe_allow_html=True)
            with c2:
                st.markdown(f"""
                <div style="background: rgba(255,255,255,0.02); padding: 1rem; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); height: 100%;">
                    <small style="color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Resumo Acadêmico da Fonte</small>
                    <p style="font-size: 0.95rem; margin-top: 0.5rem; line-height: 1.6; color: #cbd5e1;">{comp_res.resumo_academico}</p>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("#### 📂 Categorias Temáticas Extraídas")
            if comp_res.temas:
                for idx, tema in enumerate(comp_res.temas):
                    st.markdown(f"""
                    <div style="background: rgba(255,255,255,0.02); padding: 1rem; border-radius: 8px; margin-bottom: 0.8rem; border: 1px solid rgba(255,255,255,0.05);">
                        <strong style="color: #38bdf8; font-size: 1.1rem;">Categoria {idx+1}: {tema.get('titulo', 'Sem Título')}</strong><br>
                        <p style="font-style: italic; font-size: 0.95rem; color: #94a3b8; margin: 0.4rem 0 0.8rem 0;">{tema.get('resumo_tema', '')}</p>
                        <div style="padding-left: 1rem; border-left: 2px solid #38bdf8;">
                            {"".join([f"<div style='margin-bottom: 0.4rem; color: #e2e8f0; font-size: 0.95rem;'>• {pt}</div>" for pt in tema.get("pontos_chave", [])])}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Nenhuma categoria temática detectada automaticamente.")

            if comp_res.citacoes_chave:
                st.markdown("---")
                st.markdown("#### 💬 Banco de Evidências (Citações Verbatim para a Tese)")
                for cit in comp_res.citacoes_chave:
                    st.markdown(f"""
                    <div style="background: rgba(167,139,250,0.04); border-left: 4px solid #a78bfa; padding: 0.8rem 1.2rem; border-radius: 0 8px 8px 0; margin-bottom: 0.8rem; border-top: 1px solid rgba(167,139,250,0.08); border-right: 1px solid rgba(167,139,250,0.08); border-bottom: 1px solid rgba(167,139,250,0.08);">
                        <span style="font-style: italic; font-size: 1.05rem; color: #f1f5f9; line-height: 1.6;">“{cit.get('texto', '').replace('“', '').replace('”', '').strip()}”</span><br>
                        <small style="color: #94a3b8; display: inline-block; margin-top: 0.4rem;">— <strong>{cit.get('contexto_autor', 'N/D')}</strong> | {cit.get('pagina_paragrafo', 'N/D')}</small>
                    </div>
                    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Texto da Tese Gerado")

    polish_results = st.session_state.get("polish_results", [])

    # Preview das seções
    tabs_secoes = [r.secao_titulo for r in polish_results if hasattr(r, 'secao_titulo')]
    if not tabs_secoes:
        tabs_secoes = [f"Seção {i+1}" for i in range(len(polish_results))]

    if polish_results:
        tabs = st.tabs(tabs_secoes)
        for tab, resultado in zip(tabs, polish_results):
            with tab:
                st.markdown(resultado.texto_polido)
                
                # Relatório Detalhado de Auditoria (Módulo 4 — Auditoria Pessimista)
                if hasattr(resultado, 'aprovada'):
                    status_cor = "green" if resultado.aprovada else "red"
                    status_texto = "✅ APROVADA" if resultado.aprovada else "⚠️ ALERTAS DETECTADOS"
                    
                    with st.expander(f"🔍 Auditoria de Integridade: {status_texto}", expanded=not resultado.aprovada):
                        if not resultado.aprovada:
                            st.error(f"**Veredito:** {resultado.relatorio}")
                        else:
                            st.success(f"**Veredito:** {resultado.relatorio}")
                        
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            f_status = resultado.fidelidade.get('status', 'N/A')
                            st.markdown(f"**Fidelidade**\n\n{'🟢' if f_status == 'OK' else '🔴'} {f_status}")
                        with c2:
                            o_status = resultado.omissao.get('status', 'N/A')
                            st.markdown(f"**Omissão**\n\n{'🟢' if o_status == 'OK' else '🔴'} {o_status}")
                        with c3:
                            v_status = resultado.voz.get('status', 'N/A')
                            st.markdown(f"**Voz (Verbatim)**\n\n{'🟢' if v_status == 'OK' else '🔴'} {v_status}")
                        
                        if not resultado.aprovada:
                            st.warning(f"**Detalhes dos Alertas:**\n\n"
                                       f"- **Fidelidade:** {resultado.fidelidade.get('detalhes', 'N/D')}\n"
                                       f"- **Omissão:** {resultado.omissao.get('detalhes', 'N/D')}\n"
                                       f"- **Voz:** {resultado.voz.get('detalhes', 'N/D')}")
                elif resultado.relatorio and "[PLACEHOLDER]" not in resultado.relatorio:
                    with st.expander("Relatório de Auditoria"):
                        st.info(resultado.relatorio)

    st.divider()

    # O Escriba fará o download unicamente do formato cacheado para não congelar o Streamlit
    st.markdown(f"#### Download (Formato: {st.session_state.get('export_format', 'N/D').upper()})")
    
    eb = st.session_state.get("export_bytes")
    en = st.session_state.get("export_nome", "documento")
    em = st.session_state.get("export_mime", "text/plain")
    
    st.download_button(
        f"Baixar Arquivo Final",
        eb,
        en,
        em,
        use_container_width=True,
        key="dl_main"
    )

# ──────────────────────────────────────────────────────────────────
# Rodapé
# ──────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="escriba-footer">
    <strong>Escriba v2.0</strong> — Central modular de processamento acadêmico com IA<br>
    Desenvolvido por <strong>{config.APP_AUTOR}</strong> • {config.APP_ANO} •
    Powered by <strong>Maritaca Sabiá</strong>
</div>
""", unsafe_allow_html=True)
