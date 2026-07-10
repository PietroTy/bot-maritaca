"""
modules/generator.py — Módulo 3: Pipeline de Geração Agêntica
Escriba

ESTADO ATUAL: Funcional — geração real via API Maritaca (sabiazinho-4).
ROADMAP: Implementar Chain-of-Verification (CoVe) completo
"""

import json
import os
from typing import Optional, Callable

try:
    import openai
    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False


class GeneratorResult:
    """Resultado de geração de uma seção."""
    def __init__(self, secao_id: str, secao_titulo: str, texto: str, modelo_usado: str, cove_ativo: bool = False):
        self.secao_id = secao_id
        self.secao_titulo = secao_titulo
        self.texto = texto
        self.modelo_usado = modelo_usado
        self.cove_ativo = cove_ativo


def _build_system_prompt() -> str:
    """
    TRAVA MESTRA — Escriba v7.1
    Instruções de comportamento rigoroso para escrita de teses de Doutorado.
    """
    return (
        "Você é um assistente acadêmico rigoroso auxiliando na escrita de uma tese de Doutorado em Educação.\n\n"
        "**REGRAS INQUEBRÁVEIS:**\n"
        "1. **Voz e Persona:** Escreva na primeira pessoa do singular com tom acadêmico reflexivo. "
        "É ESTRITAMENTE PROIBIDO inventar cargos biográficos (ex: 'como supervisor'), anedotas, metáforas poéticas ou falas de terceiros.\n"
        "2. **Verbatim (Citação Exata):** Toda afirmação extraída diretamente de autores ou leis deve ser citada no corpo do texto utilizando aspas duplas de forma literal.\n"
        "3. **Inferência Zero — REGRA CRÍTICA E ABSOLUTA:** NUNCA adicione marcos históricos, contextos políticos ou conclusões que extrapolem os dados fornecidos. "
        "É ABSOLUTAMENTE PROIBIDO utilizar seu conhecimento prévio de mundo para citar eventos históricos (ex: enchentes, desastres) ou datas estatísticas que não estejam escritos de forma literal no documento fornecido. Restrinja-se 100% aos dados do payload. "
        "PROIBIÇÃO TOTAL DE ALUCINAÇÃO NORMATIVA: É TERMINANTEMENTE PROIBIDO inventar, inferir, completar ou 'ganhar confiança' para preencher qualquer lacuna "
        "normativa — incluindo: números de leis, decretos, portarias, resoluções, artigos específicos, datas de aprovação (dia, mês ou ano) e códigos de planos "
        "governamentais. Esta regra se aplica MESMO quando o contexto parece sugerir o dado: se o número ou a data não estiver LITERALMENTE transcrito no "
        "material-fonte fornecido, cite a norma de forma genérica (ex: 'nos termos da legislação vigente', 'conforme o plano nacional de educação em vigor', "
        "'segundo a política nacional de educação ambiental') e JAMAIS fabrique um identificador. A violação desta regra invalida toda a seção.\n"
        "4. **Isolamento de Escopo:** Concentre-se EXCLUSIVAMENTE em desenvolver os dados do prompt atual. Nunca antecipe ou nomeie os assuntos do próximo capítulo no final do texto gerado, nem antecipe metodologias ou tópicos futuros.\n"
        "5. **Limpeza de Assinatura:** NUNCA inclua cabeçalhos, rodapés ou metadados como 'Escriba', 'Página X' ou tags de sistema. "
        "O texto deve começar e terminar com conteúdo acadêmico puro.\n"
        "6. **Anti-Tique de Persona — REGRA DE ESTILO CRÍTICA:** É TERMINANTEMENTE PROIBIDO iniciar qualquer parágrafo com verbos mentais ou declarativos "
        "na primeira pessoa, tais como: 'Compreendo que', 'Reconheço que', 'Analiso que', 'Observo que', 'Percebo que', 'Constato que', 'Noto que', "
        "'Entendo que', 'Verifico que'. Esses padrões são tiques de persona artificiais que denunciam geração automática. "
        "Use a primeira pessoa de forma NATURAL e INVISÍVEL no meio da argumentação teórica "
        "(ex: 'A minha trajetória como pesquisador indica que...', 'Ao investigar esse cenário, torna-se evidente que...', "
        "'O exame dos dados revela que...'). A primeira pessoa deve emergir da reflexão, não anunciá-la."
    )


def _chamar_api(client, modelo: str, system_prompt: str, user_prompt: str, max_tokens: int = 2048) -> str:
    """Chama a API Maritaca com o modelo especificado."""
    try:
        response = client.chat.completions.create(
            model=modelo,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.5,   # Temperatura baixa para maior fidelidade
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"[ERRO NA API] {e}"


def generate(
    texto_fatos: str,
    texto_modelo: str,
    template: dict,
    secoes_selecionadas: list[str],
    tema: str,
    idioma: str,
    api_key: str,
    modelo_geracao: str = "sabiazinho-4",
    incluir_markers: bool = False,
    contexto_anterior: Optional[str] = None,
    status_callback: Optional[Callable] = None,
    progress_callback: Optional[Callable] = None,
) -> list[GeneratorResult]:
    """
    Ponto de entrada principal do Generator.
    """
    if not _HAS_OPENAI:
        raise ImportError("openai não instalado. Execute: pip install openai")

    client = openai.OpenAI(api_key=api_key, base_url="https://chat.maritaca.ai/api")
    
    from .extractor import extract_required_entities_from_prompt, extract_mandatory_keys_from_context, categorize_knowledge_base
    
    # [Passo 1] Agente Classificador Global
    contexto_estruturado = categorize_knowledge_base(texto_fatos, api_key, status_callback)
    
    # Trava Mestra Injetada + max_tokens do template (default 2048)
    system_prompt = template.get("system_prompt", _build_system_prompt())
    max_tokens_template = int(template.get("max_tokens_geracao", 2048))
    
    secoes_template = {s["id"]: s for s in template.get("secoes", [])}
    resultados = []
    total = len(secoes_selecionadas)

    for i, secao_id in enumerate(secoes_selecionadas):
        secao = secoes_template.get(secao_id)
        if not secao:
            continue

        if status_callback:
            status_callback(f"⚙️ Gerando: {secao['titulo']} ({i+1}/{total})...")

        sub_prompts = secao.get("sub_prompts", [secao.get("prompt", "")])
        texto_gerado_acc = []
        contexto_interno = contexto_anterior or ""
        
        # [Passo 2, 3 e 4] Loop de Sub-Prompts fatiados com Micro-Chunking Hardcoded
        for idx_sub, sub_item in enumerate(sub_prompts):
            if isinstance(sub_item, dict):
                comando_atual = sub_item.get("comando", "")
                required_keys = sub_item.get("required_keys", [])
            else:
                comando_atual = sub_item
                # Heurística de Fallback para chaves se o sub_prompt for apenas string
                titulo_lower = secao["titulo"].lower()
                id_lower = secao["id"].lower()
                if any(x in titulo_lower for x in ["metod", "procedimento"]):
                    required_keys = ["metodologia_e_instrumentos"]
                elif any(x in titulo_lower for x in ["trajet", "apresent"]):
                    required_keys = ["biografia_pesquisador", "contexto_global"]
                elif any(x in titulo_lower for x in ["revis", "teoric", "desenvolvimento"]):
                    required_keys = ["referencial_teorico", "legislacao"]
                else:
                    required_keys = ["contexto_global", "referencial_teorico"]

            # [Passo 3] Montagem Blindada do Payload Isolado
            present_keys = [k for k in required_keys if k in contexto_estruturado and contexto_estruturado[k].strip()]
            if not present_keys:
                # Se não mapeou chaves, envia um resumo teórico padrão
                bloco_fatos = contexto_estruturado.get("referencial_teorico", texto_fatos[:5000])
                current_labels = ["referencial_teorico (auto)"]
            else:
                bloco_fatos = "\n\n".join([contexto_estruturado[k] for k in present_keys])
                current_labels = present_keys

            if status_callback:
                status_callback(f"⚙️ Expandindo Chamada {idx_sub+1}/{len(sub_prompts)} de '{secao['titulo']}' (Fatores: {current_labels})")

            # Construção da Ingestão Material (Hard Isolation)
            material_inj = f"\n\nMATERIAL-FONTE ISOLADO (DADOS PERMITIDOS PARA ESTA CHAMADA):\n\"\"\"\n{bloco_fatos}\n\"\"\"\n"
            if texto_modelo:
                material_inj += f"\nMATERIAL DE REFERÊNCIA (ESTILO):\n\"\"\"\n{texto_modelo[:8000]}\n\"\"\""

            user_prompt = (
                f"TAREFA ESPECÍFICA:\n{comando_atual}\n\n"
                "Lembre-se: Use APENAS o material-fonte isolado acima. Ignore metodologias se elas não estiverem listadas."
            )

            # Cláusula Anti-Transição Robótica: proíbe o modelo de usar fórmulas
            # mecânicas de abertura ("Prosseguindo...", "Dando continuidade...", etc.)
            # que denunciam que o texto foi gerado em pedaços via API.
            regra_transicao = (
                "REGRA DE COSTURA INVISÍVEL (OBRIGATÓRIA): "
                "Este bloco é a continuação direta do texto anterior. "
                "É TERMINANTEMENTE PROIBIDO iniciar com fórmulas mecânicas de transição, "
                "tais como: 'Prosseguindo na análise', 'Dando continuidade', 'Aprofundando a discussão', "
                "'Continuando a análise', 'Em continuidade', 'Retomando', 'Como vimos' ou similares. "
                "O primeiro parágrafo DEVE começar diretamente com a argumentação teórica, "
                "como se o texto fosse um único fluxo contínuo de escrita. "
                "A costura entre os blocos deve ser COMPLETAMENTE INVISÍVEL ao leitor.\n\n"
            )

            if contexto_interno:
                user_prompt = (
                    "TEXTO JÁ REDIGIDO (referência de continuidade — não repita, apenas prossiga o raciocínio):\n"
                    f"{contexto_interno}\n--- FIM DA REFERÊNCIA ---\n\n"
                    + regra_transicao
                    + user_prompt
                )
            else:
                # Mesmo no primeiro chunk, aplica a regra para blocos únicos
                user_prompt = regra_transicao + user_prompt

            # Extração de Chaves Anti-Omissão deste bloco
            ent_prompt = extract_required_entities_from_prompt(comando_atual, api_key)
            ent_contexto = extract_mandatory_keys_from_context(bloco_fatos, api_key)
            entidades_obrig = list(set(ent_prompt + ent_contexto))
            
            # Retry Anti-Omissão e [Passo 5] Sanitização progressiva
            tentativas = 0
            max_retries = 2
            texto_gerado_sub = ""
            while tentativas <= max_retries:
                texto_gerado_sub = _chamar_api(client, modelo_geracao, system_prompt, user_prompt + material_inj, max_tokens=max_tokens_template)
                falhas = [e for e in entidades_obrig if str(e).lower() not in texto_gerado_sub.lower()]
                if not falhas: break
                
                if status_callback and falhas:
                    status_callback(f"⚠️ Omissão em {secao['titulo']} (Chamada {idx_sub+1}). Reforçando: {', '.join(falhas)[:30]}...")
                
                tentativas += 1
                user_prompt += f"\n\n[ALERTA ANTI-OMISSÃO]: Você omitiu dados cruciais: {falhas}. Reescreva incluindo-os."
                
            texto_gerado_acc.append(texto_gerado_sub)
            contexto_interno = texto_gerado_sub

        texto_gerado = "\n\n".join(texto_gerado_acc)

        resultados.append(GeneratorResult(
            secao_id=secao_id,
            secao_titulo=secao["titulo"],
            texto=texto_gerado,
            modelo_usado=modelo_geracao,
            cove_ativo=False,
        ))

        if progress_callback:
            progress_callback((i + 1) / total)

    if status_callback:
        status_callback(f"✅ Geração concluída: {len(resultados)} seções geradas.")

    return resultados
