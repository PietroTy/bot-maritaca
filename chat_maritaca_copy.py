import os
import json
from dotenv import load_dotenv
import openai
import PyPDF2
import docx

load_dotenv()

MARITACA_API_KEY = os.getenv("MARITACA_API_KEY")

def ler_pdf(caminho_pdf):
    texto = ""
    try:
        with open(caminho_pdf, "rb") as f:
            leitor = PyPDF2.PdfReader(f)
            if not leitor.pages:
                print("Aviso: O PDF não contém páginas.")
                return ""
            for pagina in leitor.pages:
                texto_pagina = pagina.extract_text()
                if texto_pagina:
                    texto += texto_pagina + "\n"
    except FileNotFoundError:
        print(f"Erro: O arquivo '{caminho_pdf}' não foi encontrado.")
        return None
    except Exception as e:
        print(f"Erro ao ler o PDF: {e}")
        return None
    return texto.strip()

def ler_txt(caminho_txt):
    try:
        with open(caminho_txt, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"Erro: O arquivo '{caminho_txt}' não foi encontrado.")
        return None
    except Exception as e:
        print(f"Erro ao ler o TXT: {e}")
        return None

def ler_docx(caminho_docx):
    try:
        doc = docx.Document(caminho_docx)
        texto = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        return texto.strip()
    except FileNotFoundError:
        print(f"Erro: O arquivo '{caminho_docx}' não foi encontrado.")
        return None
    except Exception as e:
        print(f"Erro ao ler o DOCX: {e}")
        return None

def criar_preprompt(texto):
    return {
        "role": "system",
        "content": (
            "Você é um assistente especialista em design educacional e criação de conteúdo. "
            "Considere o seguinte conteúdo base para todas as respostas:\n\n"
            f"{texto}"
        )
    }

if not MARITACA_API_KEY:
    raise ValueError("A variável de ambiente MARITACA_API_KEY não foi definida.")

client = openai.OpenAI(
    api_key=MARITACA_API_KEY,
    base_url="https://chat.maritaca.ai/api"
)

def chat_with_bot(user_input, preprompt):
    try:
        response = client.chat.completions.create(
            model="sabiazim-3",
            messages=[preprompt, {"role": "user", "content": user_input}],
            temperature=0.7,
            max_tokens=2048
        )
        assistant_reply = response.choices[0].message.content
        return assistant_reply
    except Exception as e:
        return f"❌ Erro na comunicação com a API: {e}"

def gerar_glossario(conteudo, preprompt):
    prompt_glossario = f"""
    Seção 3. Glossário geral

    Com base no texto abaixo, identifique as palavras ou termos difíceis, técnicos ou pouco usuais para o público geral. 
    Para cada termo, forneça uma explicação clara e objetiva. 
    Apresente o glossário no seguinte formato, sem linhas em branco e sem repetições:

    N°:\tTermo:\tDefinição / significado:
    1\tpalavra\tdefinição
    2\tpalavra\tdefinição
    3\t...

    Texto base:
    {conteudo}
    """
    return chat_with_bot(prompt_glossario, preprompt)

def gerar_links_anexos(texto, preprompt):
    prompt_links = f"""
    Seção 4. Links de materiais complementares e anexos

    Analise o conteúdo abaixo, extraindo apenas os links e anexos citados no texto. 
    Organize-os em uma seção chamada "Links complementares e anexos", seguindo os exemplos de formatação abaixo. 
    Não invente links, use apenas os que realmente aparecem no texto.

    Exemplos de formato:

    Vídeos do youtube
    TÍTULO DA PARTE. Autor da postagem (duração do arquivo): idioma. Endereço disponível da web. Data de acesso.

    Blog
    TÍTULO DA PUBLICAÇÃO. Título da parte. Data de publicação. Endereço disponível da web. Data de acesso.

    Podcast
    SOBRENOME DO AUTOR, Nome. Título da parte. Duração da mídia. Data de publicação. Endereço disponível da web. Data de acesso.

    Conteúdo base:
    {texto}
    """
    return chat_with_bot(prompt_links, preprompt)

def main():
    print("Maritaca AI Terminal Chatbot (modelo sabiazim-3)")

    tema_geral = input("Digite uma breve descrição do tema geral abordado: ").strip()

    caminho_arquivo = input("Digite o caminho do arquivo (.pdf, .txt, .docx) para processar: ").strip()
    extensao = os.path.splitext(caminho_arquivo)[1].lower()

    if extensao == ".pdf":
        texto = ler_pdf(caminho_arquivo)
    elif extensao == ".txt":
        texto = ler_txt(caminho_arquivo)
    elif extensao == ".docx":
        texto = ler_docx(caminho_arquivo)
    else:
        print("❌ Formato de arquivo não suportado. Use PDF, TXT ou DOCX.")
        return

    if not texto:
        print("❌ Não foi possível ler o arquivo ou ele está vazio.")
        return

    preprompt = criar_preprompt(f"Tema geral: {tema_geral}\n\n{texto}")

    prompt_introducao = """
    Seção 1. Introdução ao conteúdo

    Aja como um conteudista educacional experiente. Com base no conteúdo do sistema, redija um texto introdutório para um módulo educacional. Siga estas regras:

    - O texto deve ter **pelo menos 3 parágrafos**, totalizando **no máximo 1.200 caracteres sem espaço**.
    - Instigue o leitor a estudar o tema abordado.
    - Use o seguinte modelo estrutural:

    1. Parágrafo inicial com uma introdução envolvente sobre o tema geral do módulo.
    2. "Neste módulo, você vai aprender…" seguido de um resumo claro dos conteúdos abordados e sua importância para profissionais ou interessados na área.
    3. "Outro tema relevante é…" e depois "Por fim, você terá a oportunidade de…", encerrando com a ampliação de repertório do estudante.

    Finalize com: **Bons estudos!**
    """
    print("\n===== SEÇÃO 1. INTRODUÇÃO AO CONTEÚDO =====\n")
    resposta_introducao = chat_with_bot(prompt_introducao, preprompt)
    print(resposta_introducao)
    print("===============================================\n")

    prompt_unidades = """
    Seção 2. Unidades de aprendizagem do Módulo

    Atue como um especialista em design instrucional. Sua tarefa é desenvolver o conteúdo detalhado de um módulo educacional com base no conteúdo do sistema. Siga estritamente as diretrizes abaixo:

    1.  **Estrutura em Unidades:** Subdivida os temas principais do conteúdo em Unidades de aprendizagem. Dê um título claro e descritivo para cada Unidade (exemplo: "Unidade 1: A EaD e a Legislação Brasileira").
    
    2.  **Elaboração do Conteúdo:** Para cada unidade, elabore um texto didático que explique os conceitos essenciais do tema. O texto deve ser claro, objetivo e aprofundado.
    
    3.  **Fundamentação e Referências:** Fundamente os conceitos com referências (como livros, artigos, leis, ou outras fontes de credibilidade, preferencialmente disponíveis online). Cite as fontes diretamente no texto ou ao final de cada unidade.
    
    4.  **Sugestão de Elementos Visuais:** Onde for pertinente, sugira elementos visuais para enriquecer a aprendizagem. Use marcadores como `[Sugestão de Imagem: descrição da imagem]` ou `[Caixa de Destaque: texto a ser destacado]`.
    
    5.  **Restrições:**
        * Cada unidade deve ter, no máximo, **3.000 caracteres sem espaço**.
        * Ignore quaisquer menções a formatação de fonte (Arial, tamanho 12) ou termos específicos como "RAE". O foco é exclusivamente na qualidade e estrutura do conteúdo textual.

    Desenvolva a quantidade de unidades que julgar necessária para cobrir os tópicos centrais do material de base.
    """
    print("\n===== SEÇÃO 2. UNIDADES DE APRENDIZAGEM DO MÓDULO =====\n")
    resposta_unidades = chat_with_bot(prompt_unidades, preprompt)
    print(resposta_unidades)
    print("==========================================================\n")

    print("\n===== SEÇÃO 3. GLOSSÁRIO GERAL =====\n")
    conteudo_para_glossario = f"{resposta_introducao}\n{resposta_unidades}"
    glossario = gerar_glossario(conteudo_para_glossario, preprompt)
    print(glossario)
    print("=======================================\n")

    print("\n===== SEÇÃO 4. LINKS DE MATERIAIS COMPLEMENTARES E ANEXOS =====\n")
    links_anexos = gerar_links_anexos(texto, preprompt)
    print(links_anexos)
    print("===================================================================\n")

    prompt_conclusao = """
    Seção 5. Unidade de conclusão do módulo

    Atue como um conteudista educacional experiente. Com base no conteúdo do sistema, escreva a unidade de conclusão do módulo, utilizando o mesmo formato da apresentação, mas agora recapitulando tudo o que a pessoa aprendeu. Siga estas orientações:

    - O texto deve ter pelo menos 3 parágrafos, totalizando no máximo 1.200 caracteres sem espaço.
    - Faça uma síntese dos principais pontos e temas abordados no módulo, destacando o que o estudante aprendeu.
    - Use frases como "Neste módulo, você aprendeu...", "Além disso, foi possível compreender...", "Por fim, você está apto a...".
    - Finalize com uma mensagem de incentivo ao estudante para aplicar o conhecimento adquirido.

    Finalize com: **Parabéns por concluir o módulo!**
    """
    print("\n===== SEÇÃO 5. UNIDADE DE CONCLUSÃO DO MÓDULO =====\n")
    resposta_conclusao = chat_with_bot(prompt_conclusao, preprompt)
    print(resposta_conclusao)
    print("======================================================\n")

    prompt_referencias = """
    Seção 6. Referências do Módulo

    Com base no conteúdo do sistema, extraia e organize todas as referências bibliográficas citadas no texto do módulo. 
    Utilize o seguinte formato para cada referência:

    SOBRENOME, Nome do autor. Título. Edição. Local: Editora, data publicação.

    Liste apenas referências realmente presentes no conteúdo, sem inventar. 
    Caso não haja referências explícitas, retorne apenas: "Nenhuma referência encontrada no conteúdo."

    Apresente a lista de forma clara e sem repetições.
    """
    print("\n===== SEÇÃO 6. REFERÊNCIAS DO MÓDULO =====\n")
    referencias = chat_with_bot(prompt_referencias, preprompt)
    print(referencias)
    print("=============================================\n")

if __name__ == "__main__":
    main()