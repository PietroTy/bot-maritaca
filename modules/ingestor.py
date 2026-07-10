"""
modules/ingestor.py — Módulo 1: Ingestão Inteligente de Documentos
Escriba v2.0

ESTADO ATUAL: Funcional (usando PyPDF2/python-docx).
ROADMAP: Substituir extração de PDF pela biblioteca Marker (Datalab) para
         preservação superior de tabelas, fórmulas e referências.

Responsabilidades:
- Extrair texto de PDF, DOCX, TXT
- Gerar hash SHA-256 do conteúdo para Semantic Cache
- Retornar texto limpo + metadados preliminares
"""

import hashlib
import io
import time
from typing import Optional

try:
    import PyPDF2
    _HAS_PYPDF2 = True
except ImportError:
    _HAS_PYPDF2 = False

try:
    import docx as python_docx
    _HAS_DOCX = True
except ImportError:
    _HAS_DOCX = False


class IngestorResult:
    """Resultado padronizado da ingestão."""
    def __init__(self, texto: str, hash_conteudo: str, metadados: dict, formato: str):
        self.texto = texto
        self.hash_conteudo = hash_conteudo
        self.metadados = metadados
        self.formato = formato

    def to_dict(self) -> dict:
        return {
            "texto_preview": self.texto[:300] + "..." if len(self.texto) > 300 else self.texto,
            "total_chars": len(self.texto),
            "hash": self.hash_conteudo,
            "formato": self.formato,
            "metadados": self.metadados,
        }


def _extrair_pdf(file_bytes: bytes) -> str:
    """Extrai texto de PDF usando PyPDF2. (ROADMAP: Migrar para Marker)"""
    if not _HAS_PYPDF2:
        raise ImportError("PyPDF2 não está instalado. Execute: pip install PyPDF2")
    texto = ""
    leitor = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    for i, pagina in enumerate(leitor.pages):
        texto_pagina = pagina.extract_text()
        if texto_pagina:
            # Marcador de página para rastreabilidade (track-back)
            texto += f"\n[PÁGINA {i + 1}]\n{texto_pagina}\n"
    return texto.strip()


def _extrair_docx(file_bytes: bytes) -> str:
    """Extrai texto de DOCX usando python-docx."""
    if not _HAS_DOCX:
        raise ImportError("python-docx não está instalado. Execute: pip install python-docx")
    doc = python_docx.Document(io.BytesIO(file_bytes))
    return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])


def _extrair_txt(file_bytes: bytes) -> str:
    """Extrai texto de TXT."""
    return file_bytes.decode("utf-8", errors="ignore").strip()


def ingest_document(file_bytes: bytes, nome_arquivo: str, status_callback=None) -> IngestorResult:
    """
    Ponto de entrada principal do Ingestor.

    Args:
        file_bytes: Conteúdo bruto do arquivo.
        nome_arquivo: Nome do arquivo com extensão.
        status_callback: Função opcional para reportar progresso (ex: st.status).

    Returns:
        IngestorResult com texto, hash, metadados e formato detectado.
    """
    if status_callback:
        status_callback("Detectando formato e extraindo texto...")

    extensao = nome_arquivo.rsplit(".", 1)[-1].lower()

    if extensao == "pdf":
        texto = _extrair_pdf(file_bytes)
        formato = "PDF"
    elif extensao == "docx":
        texto = _extrair_docx(file_bytes)
        formato = "DOCX"
    elif extensao == "txt":
        texto = _extrair_txt(file_bytes)
        formato = "TXT"
    else:
        raise ValueError(f"Formato '{extensao}' não suportado. Use PDF, DOCX ou TXT.")

    # Hash para Semantic Cache (evitar reprocessamento pago)
    hash_conteudo = hashlib.sha256(file_bytes).hexdigest()

    # Metadados preliminares (futuramente: extração via sabiazinho-3)
    metadados = {
        "arquivo": nome_arquivo,
        "formato": formato,
        "total_caracteres": len(texto),
        "total_palavras": len(texto.split()),
        "hash": hash_conteudo,
    }

    if status_callback:
        status_callback(f"✅ Ingestão concluída: {len(texto)} caracteres extraídos de {nome_arquivo}.")

    return IngestorResult(
        texto=texto,
        hash_conteudo=hash_conteudo,
        metadados=metadados,
        formato=formato,
    )
