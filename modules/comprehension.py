"""
modules/comprehension.py — Módulo 2: Motor de Compreensão e Grounding
Escriba v2.0

ESTADO ATUAL: Placeholder estruturado.
ROADMAP: Implementar Self-RAG com embeddings (ChromaDB/Pinecone) para:
         - Chunking semântico do texto
         - Indexação de evidências por página/parágrafo
         - Busca vetorial para Grounding anti-alucinação

Responsabilidades:
- Receber o IngestorResult
- Construir o "mapa de evidências" (chunks com ID de origem)
- Retornar ComprehensionResult para uso pelo Generator
"""

import re
from typing import Optional


class EvidenceChunk:
    """Representa um trecho indexado com rastreabilidade de origem."""
    def __init__(self, chunk_id: str, texto: str, pagina: Optional[int], paragrafo: int):
        self.chunk_id = chunk_id
        self.texto = texto
        self.pagina = pagina
        self.paragrafo = paragrafo

    def ref(self) -> str:
        """Referência de origem formatada para citação."""
        if self.pagina:
            return f"[Ref: pág {self.pagina}, parágrafo {self.paragrafo}]"
        return f"[Ref: parágrafo {self.paragrafo}]"


class ComprehensionResult:
    """Resultado padronizado da compreensão acadêmica e qualitativa."""
    def __init__(
        self,
        texto_completo: str,
        chunks: list[EvidenceChunk],
        resumo_semantico: str,
        resumo_academico: str,
        classificacao: str,
        temas: list[dict],
        citacoes_chave: list[dict]
    ):
        self.texto_completo = texto_completo
        self.chunks = chunks
        self.resumo_semantico = resumo_semantico
        self.resumo_academico = resumo_academico
        self.classificacao = classificacao
        self.temas = temas
        self.citacoes_chave = citacoes_chave

    def to_dict(self) -> dict:
        return {
            "total_chunks": len(self.chunks),
            "resumo_semantico_preview": self.resumo_semantico[:500],
            "resumo_academico": self.resumo_academico,
            "classificacao": self.classificacao,
            "total_temas": len(self.temas),
            "total_citacoes": len(self.citacoes_chave),
            "status": "funcional — análise qualitativa ativa",
        }


def _split_em_chunks(texto: str, tamanho: int = 1500) -> list[tuple[int, Optional[int], str]]:
    """
    Divide o texto em chunks respeitando quebras de parágrafo.
    """
    paragrafos = [p.strip() for p in texto.split("\n\n") if p.strip()]
    chunks = []
    buffer = ""
    para_num = 0

    # Detecta marcadores de página inseridos pelo ingestor
    pagina_atual = None

    for para in paragrafos:
        page_match = re.match(r"\[PÁGINA (\d+)\]", para)
        if page_match:
            pagina_atual = int(page_match.group(1))
            continue

        buffer += " " + para
        if len(buffer) >= tamanho:
            chunks.append((para_num, pagina_atual, buffer.strip()))
            buffer = ""
            para_num += 1

    if buffer.strip():
        chunks.append((para_num, pagina_atual, buffer.strip()))

    return chunks


def comprehend(texto: str, status_callback=None) -> ComprehensionResult:
    """
    Ponto de entrada principal do Motor de Compreensão e Mapeamento Semântico.
    Realiza análise qualitativa/temática do texto usando o Sabiázinho-4.
    """
    import config
    api_key = config.get_api_key()

    if status_callback:
        status_callback("🧠 Analisando estrutura do documento e mapeando evidências...")

    # Chunking preliminar para indexação local
    chunks_raw = _split_em_chunks(texto)
    chunks = [
        EvidenceChunk(
            chunk_id=f"chunk_{i:04d}",
            texto=c_texto,
            pagina=pagina,
            paragrafo=para_num,
        )
        for i, (para_num, pagina, c_texto) in enumerate(chunks_raw)
    ]

    # Se não houver API key, executa análise heurística offline
    if not api_key:
        if status_callback:
            status_callback("⚠️ Sem chave de API. Executando análise qualitativa simplificada (modo offline)...")
        
        # Heurística offline
        resumo_academico = (
            f"Análise offline concluída para o material fornecido. O texto possui {len(texto.split())} palavras "
            f"distribuídas em {len(chunks)} blocos de evidência. "
            f"Configure sua MARITACA_API_KEY para obter o mapeamento semântico completo via inteligência artificial."
        )
        classificacao = "Documento de Referência (Offline)"
        temas = [
            {
                "titulo": "Estrutura Geral do Material",
                "resumo_tema": "Visão estrutural dos tópicos abordados no texto base.",
                "pontos_chave": ["Mapeamento de parágrafos realizado com sucesso.", "Rastreabilidade de origem ativa."]
            }
        ]
        citacoes_chave = []
        
        # Tenta extrair algumas citações heurísticas entre aspas
        aspas_matches = re.findall(r'“([^”]+)”|"[^"]+"', texto)
        for match in aspas_matches[:5]:
            if match and len(match.strip()) > 30:
                citacoes_chave.append({
                    "texto": match.strip(),
                    "contexto_autor": "Autor citado na fonte",
                    "pagina_paragrafo": "Localizado via busca léxica"
                })

        resumo_semantico = f"Modo offline ativo. {len(chunks)} chunks gerados."
        
        return ComprehensionResult(
            texto_completo=texto,
            chunks=chunks,
            resumo_semantico=resumo_semantico,
            resumo_academico=resumo_academico,
            classificacao=classificacao,
            temas=temas,
            citacoes_chave=citacoes_chave
        )

    # Modo Online: Análise Semântica Qualitativa via Maritaca Sabiázinho-4
    try:
        import openai
        client = openai.OpenAI(api_key=api_key, base_url=config.MARITACA_BASE_URL)
        
        if status_callback:
            status_callback("🧠 Enviando material para mapeamento semântico (sabiazinho-4)...")

        # Limita o texto para não estourar contexto, caso seja gigantesco (poupando tokens e custos)
        # Sabiázinho-4 aguenta 128k, mas fatiar em 100k caracteres (cerca de 20k tokens) é seguro e rápido.
        texto_analise = texto[:120000]

        system_prompt = (
            "Você é o Analista Qualitativo e Especialista em Metodologia de Pesquisa do sistema Escriba.\n"
            "Sua tarefa é analisar o material-fonte fornecido e gerar uma compreensão estruturada para auxiliar "
            "na escrita de uma tese de doutorado. Toda a análise deve se basear estritamente no texto fornecido.\n\n"
            "RETORNO OBRIGATÓRIO EM JSON (estrito, sem markdown ou blocos de código adicionais):\n"
            "{\n"
            "  \"resumo_academico\": \"Um parágrafo de síntese formal do foco, escopo e principais contribuições do material.\",\n"
            "  \"classificacao\": \"Classificação metodológica do documento (ex: Teórico/Referencial, Empírico/Pesquisa de Campo, Normativo/Legal, Metodológico, ou Misto) seguida de justificativa curta.\",\n"
            "  \"temas\": [\n"
            "    {\n"
            "      \"titulo\": \"Título do Tema/Categoria (curto e acadêmico)\",\n"
            "      \"resumo_tema\": \"Explicação resumida de como esta categoria se expressa no texto.\",\n"
            "      \"pontos_chave\": [\n"
            "        \"Argumento ou dado principal 1\",\n"
            "        \"Argumento ou dado principal 2\"\n"
            "      ]\n"
            "    }\n"
            "  ],\n"
            "  \"citacoes_chave\": [\n"
            "    {\n"
            "      \"texto\": \"A frase exata contida no texto (verbatim) entre aspas, ideal para ser citada.\",\n"
            "      \"contexto_autor\": \"Quem disse a frase (ex: Paulo Freire, Professor Ipê, a PNEA, etc.) e o contexto.\",\n"
            "      \"pagina_paragrafo\": \"Localização aproximada no texto se houver menção a páginas (ex: pág 53) ou parágrafos.\"\n"
            "    }\n"
            "  ]\n"
            "}"
        )

        user_prompt = (
            "Analise o seguinte material de referência para a tese e construa o mapa semântico qualitativo.\n\n"
            f"[MATERIAL DE REFERÊNCIA]:\n\"\"\"\n{texto_analise}\n\"\"\"\n\n"
            "Gere o JSON estruturado agora."
        )

        response = client.chat.completions.create(
            model="sabiazinho-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        dados = json.loads(response.choices[0].message.content)
        
        resumo_academico = dados.get("resumo_academico", "Não foi possível gerar o resumo.")
        classificacao = dados.get("classificacao", "Misto / Referência")
        temas = dados.get("temas", [])
        citacoes_chave = dados.get("citacoes_chave", [])
        
        resumo_semantico = (
            f"Análise inteligente concluída. Foram extraídos {len(temas)} temas principais "
            f"e {len(citacoes_chave)} citações de alta relevância acadêmica."
        )

        if status_callback:
            status_callback(f"✅ Compreensão concluída: {len(temas)} temas e {len(citacoes_chave)} citações catalogadas!")

        return ComprehensionResult(
            texto_completo=texto,
            chunks=chunks,
            resumo_semantico=resumo_semantico,
            resumo_academico=resumo_academico,
            classificacao=classificacao,
            temas=temas,
            citacoes_chave=citacoes_chave
        )

    except Exception as e:
        if status_callback:
            status_callback(f"❌ Erro na análise com IA: {e}. Rebatendo para modo offline...")
        
        # Fallback se a API falhar
        resumo_academico = f"Erro na análise de IA: {e}. Processamento de contingência concluído."
        classificacao = "Misto (Fallback)"
        temas = [{"titulo": "Erro de Processamento", "resumo_tema": "Ocorreu um erro ao comunicar com a IA da Maritaca.", "pontos_chave": [str(e)]}]
        return ComprehensionResult(
            texto_completo=texto,
            chunks=chunks,
            resumo_semantico="Erro no processamento online.",
            resumo_academico=resumo_academico,
            classificacao=classificacao,
            temas=temas,
            citacoes_chave=[]
        )
