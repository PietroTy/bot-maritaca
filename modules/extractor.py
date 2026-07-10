"""
modules/extractor.py — Injeção de NER (Named Entity Recognition)
Escriba v5.0

Ponto central para extrair dados rígidos e nomes do material fonte utilizando um modelo 
rápido de extração, visando munir e trancar o pipeline gerador.
"""
import json
from typing import List, Callable, Optional

try:
    import openai
except ImportError:
    pass

def extract_entities(texto: str, api_key: str, status_callback: Optional[Callable] = None) -> List[str]:
    """
    Extrai as entidades principais (nomes, leis, locais, numéricos-chave) 
    do texto bruto fornecido, isolando-as como um buffer factual a ser 
    passado ao Generator.
    """
    if not api_key:
        return []
        
    client = openai.OpenAI(api_key=api_key, base_url="https://chat.maritaca.ai/api")
    
    if status_callback:
        status_callback("Efetuando NLP Extraction (NER) dos fatos...")

    prompt_extracao = (
        "Leia o texto com absoluta atenção e atue como um bot de Named Entity Recognition.\n"
        "Liste, em formato JSON (uma array simples de strings), estritamente os seguintes grupos sem divagações:\n"
        "1) Nomes de Autores mencionados\n"
        "2) Leis, Pactos ou Políticas Públicas\n"
        "3) Cidades, Biomas e Demografia Exata\n"
        "4) Citações qualitativas marcantes\n\n"
        "Exemplo de saída: [\"Paulo Freire\", \"PNAIC\", \"Lei 9.394/96\", \"Goiás\", \"Cerrado\"]\n\n"
        "Texto:\n"
        "...\n"
        f"{texto[:15000]}\n"
        "...\n"
        "Apenas liste a Array JSON, nenhuma frase adicional."
    )

    try:
        response = client.chat.completions.create(
            model="sabiazinho-3",  # Modelo leve e rápido perfeito pra NER
            messages=[
                {"role": "user", "content": prompt_extracao},
            ],
            temperature=0.0,   # Determinístico
            max_tokens=600,
        )
        
        saida_bruta = response.choices[0].message.content
        # Tratamento seguro caso a IA coloque blocos markdown de json
        saida_bruta = saida_bruta.replace('```json', '').replace('```', '').strip()
        
        entidades = json.loads(saida_bruta)
        if isinstance(entidades, list):
            return [str(e) for e in entidades]
        return []
        
    except Exception as e:
        if status_callback:
            status_callback(f"⚠️ Alerta NER Extractor: Falha na listagem determinística ({e}).")
        return []

def extract_required_entities_from_prompt(prompt_usuario: str, api_key: str) -> List[str]:
    """
    NLP extraindo autores e leis nominais exigidas NO PRÓPRIO prompt para a 
    validação de Loop Pós-Geração.
    """
    if not api_key:
        return []
    try:
        client = openai.OpenAI(api_key=api_key, base_url="https://chat.maritaca.ai/api")
        p = (
            "Como assistente de NER restrito, leia o comando abaixo e extraia estritamente "
            "Nomes de Autores, Teorias ou Leis Específicas que foram citados.\n"
            "Retorne APENAS um Array JSON estrito. Ex: [\"Paulo Freire\", \"LDB\", \"Loureiro\"].\n"
            "Se o comando não obrigar nominalmente nenhum autor/lei, retorne [].\n\n"
            f"Comando:\n{prompt_usuario}"
        )
        response = client.chat.completions.create(
            model="sabiazinho-3",
            messages=[{"role": "user", "content": p}],
            temperature=0.0,
            max_tokens=200,
        )
        sbruta = response.choices[0].message.content.replace('```json', '').replace('```', '').strip()
        e = json.loads(sbruta)
        if isinstance(e, list):
            return [str(x) for x in e]
        return []
    except Exception:
        return []

def categorize_knowledge_base(texto_fatos: str, api_key: str, status_callback: Optional[Callable] = None) -> dict:
    """
    Passo 1: Agente Classificador (Pre-processing).
    Lê o documento inteiro e o estrutura em um formato JSON isolando
    teoria, biografia, legislação e metodologia.
    """
    modelo_json = {
        "contexto_global": "",
        "legislacao": "",
        "biografia_pesquisador": "",
        "referencial_teorico": "",
        "metodologia_e_instrumentos": "",
        "praticas_curriculares": ""
    }
    
    if not api_key or not texto_fatos.strip():
        return modelo_json

    if status_callback:
        status_callback("Mapeando e Categorizando Fatos do Documento (Agente Classificador)...")

    try:
        client = openai.OpenAI(api_key=api_key, base_url="https://chat.maritaca.ai/api")
        p = (
            "Você é um Agente Classificador Estrutural de Dados de Pesquisa.\n"
            "Sua missão é ler o documento de pesquisa fornecido e categorizar seus parágrafos em um JSON ESTRITO.\n"
            "As chaves obrigatórias do JSON são:\n"
            "1. \"contexto_global\" — Contexto histórico, social e ambiental geral\n"
            "2. \"legislacao\" — Leis, políticas públicas, planos e marcos normativos\n"
            "3. \"biografia_pesquisador\" — Trajetória pessoal e profissional do autor\n"
            "4. \"referencial_teorico\" — Conceitos e teorias de autores acadêmicos (Freire, Sacristán, Giroux, etc.)\n"
            "5. \"metodologia_e_instrumentos\" — Métodos de pesquisa, técnicas e instrumentos\n"
            "6. \"praticas_curriculares\" — Práticas docentes, currículo vivido, currículo prescrito, prática pedagógica, justiça curricular\n\n"
            "Valores: Cada chave deve conter uma ARRAY de strings. Insira os parágrafos relevantes EXATAMENTE como estão na fonte (transcrição literal).\n"
            "Se o documento não contiver informações para alguma categoria, deixe a array vazia [].\n"
            "Responda APENAS com o JSON, sem nenhum outro tipo de texto.\n\n"
            f"[DOCUMENTO DE PESQUISA]:\n{texto_fatos[:18000]}"
        )
        response = client.chat.completions.create(
            model="sabiazinho-4",
            messages=[{"role": "user", "content": p}],
            temperature=0.0,
            max_tokens=4000,
            response_format={"type": "json_object"}
        )
        
        filtrado = response.choices[0].message.content.strip()
        filtrado = filtrado.replace('```json', '').replace('```', '').strip()
        dados_categorizados = json.loads(filtrado)
        
        # Garante que todas as chaves existam e sejam strings agregadas para uso posterior
        for key in modelo_json.keys():
            if key in dados_categorizados:
                # Se for lista de strings, junta em um único texto para facilitar. Se já for string, deixa.
                valor = dados_categorizados[key]
                if isinstance(valor, list):
                    modelo_json[key] = "\n\n".join(str(item) for item in valor)
                else:
                    modelo_json[key] = str(valor)
            else:
                modelo_json[key] = ""
                
        return modelo_json
    except Exception as e:
        if status_callback:
            status_callback(f"⚠️ Alerta: Falha no Agente Classificador ({e}). Retornando contexto bruto.")
        
        # Fallback: se falhar, enfia o texto inteiro na chave teórica pra não estourar o sistema
        modelo_json["referencial_teorico"] = texto_fatos
        return modelo_json

def extract_mandatory_keys_from_context(contexto_filtrado: str, api_key: str) -> List[str]:
    """
    Varre o contexto recortado e obriga que o Escriba retenha as "Palavras-Chave Frias" 
    mais importamentes na geração final (numéricos, siglas de leis, anos, nomes teóricos).
    """
    if not api_key or not contexto_filtrado.strip():
        return []
    try:
        client = openai.OpenAI(api_key=api_key, base_url="https://chat.maritaca.ai/api")
        p = (
            "Abaixo está um fragmento de texto de pesquisa.\n"
            "Extraia as 3 a 6 entidades MAIS CRÍTICAS que formam a espinha dorsal fática desse fragmento.\n"
            "Foque exclusivamente em ANOS (ex: 2026), SIGLAS/LEIS (ex: PNE), AUTORES TEÓRICOS, e TERMOS-CHAVE ÚNICOS.\n"
            "Retorne APENAS um Array JSON estrito. Ex: [\"2026\", \"PNE\", \"Paulo Freire\"].\n\n"
            f"Texto:\n{contexto_filtrado[:3000]}"
        )
        response = client.chat.completions.create(
            model="sabiazinho-3",
            messages=[{"role": "user", "content": p}],
            temperature=0.0,
            max_tokens=200,
        )
        sbruta = response.choices[0].message.content.replace('```json', '').replace('```', '').strip()
        e = json.loads(sbruta)
        if isinstance(e, list):
            return [str(x) for x in e]
        return []
    except Exception:
        return []
