"""
config.py — Configuração Central do Escriba
Gerencia modelos, custos, variáveis de ambiente e constantes do projeto.
"""

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv opcional; em produção usa st.secrets

# ──────────────────────────────────────────
# Modelos Maritaca disponíveis
# ──────────────────────────────────────────
MODELOS = {
    "sabiazinho-3": {
        "nome_exibicao": "Sabiazinho 3 (econômico)",
        "descricao": "Ideal para tarefas leves: extração de metadados, separação de parágrafos.",
        "contexto_tokens": 32_000,
        "custo_output_por_milhao_brl": 3.00,
        "uso_recomendado": ["metadados", "limpeza"],
    },
    "sabiazinho-4": {
        "nome_exibicao": "Sabiazinho 4 (recomendado)",
        "descricao": "Motor principal de geração. Melhor custo-benefício com 128k de contexto.",
        "contexto_tokens": 128_000,
        "custo_output_por_milhao_brl": 4.00,
        "uso_recomendado": ["geracao", "comprehension"],
    },
    "sabia-4": {
        "nome_exibicao": "Sabiá 4 (premium)",
        "descricao": "Auditoria e polimento final. Máxima performance. Use com parcimônia.",
        "contexto_tokens": 128_000,
        "custo_output_por_milhao_brl": 20.00,
        "uso_recomendado": ["polimento", "auditoria"],
    },
}

MODELO_PADRAO_GERACAO = "sabiazinho-4"
MODELO_PADRAO_AUDITORIA = "sabia-4"
MODELO_PADRAO_LEVE = "sabiazinho-3"

# ──────────────────────────────────────────
# API
# ──────────────────────────────────────────
MARITACA_BASE_URL = "https://chat.maritaca.ai/api"

def get_api_key() -> str | None:
    """
    Retorna a chave da API Maritaca.
    Ordem de prioridade:
    1. st.secrets (Streamlit Cloud)
    2. Variável de ambiente MARITACA_API_KEY
    3. Arquivo .env (via python-dotenv)
    """
    # Tenta via streamlit secrets (produção)
    try:
        import streamlit as st
        key = st.secrets.get("MARITACA_API_KEY")
        if key:
            return key
    except Exception:
        pass
    # Fallback: variável de ambiente / .env
    return os.environ.get("MARITACA_API_KEY")


# ──────────────────────────────────────────
# Templates disponíveis
# ──────────────────────────────────────────
import json
import pathlib

TEMPLATES_DIR = pathlib.Path(__file__).parent / "templates"


def listar_templates() -> list[dict]:
    """Retorna lista de todos os templates disponíveis, ordenados por prioridade."""
    templates = []
    for arquivo in sorted(TEMPLATES_DIR.glob("*.json")):
        try:
            with open(arquivo, encoding="utf-8") as f:
                t = json.load(f)
                templates.append(t)
        except Exception:
            pass
    return sorted(templates, key=lambda t: t.get("prioridade", 99))


def carregar_template(template_id: str) -> dict:
    """Carrega um template específico pelo ID."""
    caminho = TEMPLATES_DIR / f"{template_id}.json"
    if not caminho.exists():
        raise FileNotFoundError(f"Template '{template_id}' não encontrado em {TEMPLATES_DIR}")
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


# ──────────────────────────────────────────
# Constantes de UI
# ──────────────────────────────────────────
APP_NOME = "Escriba"
APP_SUBTITULO = "Central modular de processamento acadêmico com IA"
APP_AUTOR = "PietroTy"
APP_ANO = "2025"

IDIOMAS = ["Português", "Inglês", "Espanhol"]
FORMATOS_EXPORTACAO = ["pdf", "txt", "docx", "tex"]
