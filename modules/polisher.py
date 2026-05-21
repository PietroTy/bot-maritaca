import json
import re
from typing import Optional, Callable

try:
    import openai
    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False


class PolishResult:
    """Resultado do polimento e auditoria de uma seção."""
    def __init__(
        self,
        secao_id: str,
        secao_titulo: str,
        texto_original: str,
        texto_polido: str,
        aprovada: bool,
        fidelidade: dict,
        omissao: dict,
        voz: dict,
        relatorio: str,
    ):
        self.secao_id = secao_id
        self.secao_titulo = secao_titulo
        self.texto_original = texto_original
        self.texto_polido = texto_polido
        self.aprovada = aprovada
        self.fidelidade = fidelidade
        self.omissao = omissao
        self.voz = voz
        self.relatorio = relatorio


def _double_check(client, texto_gerado: str, texto_fonte: str, modelo_auditoria: str) -> dict:
    """
    Realiza a auditoria de alucinação (Double-Check) confrontando o gerado com a fonte.
    Utiliza o modelo de auditoria de forma 'Pessimista' e exige retorno em JSON.
    """
    system_prompt = (
        "Você é o Auditor Científico 'Pessimista' do sistema Escriba. Sua única missão é garantir a integridade absoluta da tese de doutorado.\n\n"
        "REGRAS DE OURO:\n"
        "1. NA DÚVIDA, ALERTE: Se uma afirmação no [TEXTO_GERADO] não puder ser rastreada diretamente ao [TEXTO_FONTE], marque como alucinação.\n"
        "2. RIGOR DOCUMENTAL: Nomes, datas, locais e números devem ser conferidos com precisão cirúrgica.\n"
        "3. VERBATIM: Verifique se as falas de professores mantêm as aspas e o texto original.\n\n"
        "OUTPUT OBRIGATÓRIO (JSON estrito):\n"
        "{\n"
        "  \"aprovada\": boolean,\n"
        "  \"fidelidade\": {\"status\": \"OK/ALERTA\", \"detalhes\": \"...\"},\n"
        "  \"omissao\": {\"status\": \"OK/ALERTA\", \"detalhes\": \"...\"},\n"
        "  \"voz\": {\"status\": \"OK/ALERTA\", \"detalhes\": \"...\"},\n"
        "  \"relatorio\": \"Resumo executivo do veredito\"\n"
        "}"
    )

    user_prompt = (
        f"[TEXTO_FONTE]:\n\"\"\"\n{texto_fonte[:12000]}\n\"\"\"\n\n"
        f"[TEXTO_GERADO]:\n\"\"\"\n{texto_gerado}\n\"\"\"\n\n"
        "Realize a auditoria técnica agora."
    )

    try:
        response = client.chat.completions.create(
            model=modelo_auditoria,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,  # Rigor máximo
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        return {
            "aprovada": False,
            "fidelidade": {"status": "ERRO", "detalhes": f"Falha na auditoria: {str(e)}"},
            "omissao": {"status": "ERRO", "detalhes": "Processo interrompido"},
            "voz": {"status": "ERRO", "detalhes": "Processo interrompido"},
            "relatorio": "Falha crítica na API de Auditoria."
        }


def polish(
    secoes_geradas: list,
    texto_fonte: str,
    api_key: Optional[str] = None,
    modelo_auditoria: str = "sabia-4",
    status_callback: Optional[Callable] = None,
    progress_callback: Optional[Callable] = None,
) -> list[PolishResult]:
    """
    Ponto de entrada principal do Polisher.
    """
    if not _HAS_OPENAI or not api_key:
        # Fallback se não houver API key ou biblioteca
        return [PolishResult(
            secao_id=s.secao_id,
            secao_titulo=s.secao_titulo,
            texto_original=s.texto,
            texto_polido=s.texto,
            aprovada=True,
            fidelidade={"status": "OFFLINE", "detalhes": "Auditoria não realizada (falta API key)"},
            omissao={"status": "OFFLINE", "detalhes": "N/A"},
            voz={"status": "OFFLINE", "detalhes": "N/A"},
            relatorio="Modo offline: Auditoria ignorada."
        ) for s in secoes_geradas]

    client = openai.OpenAI(api_key=api_key, base_url="https://chat.maritaca.ai/api")
    resultados = []
    total = len(secoes_geradas)

    for i, secao in enumerate(secoes_geradas):
        if status_callback:
            status_callback(f"🔬 Auditando integridade: {secao.secao_titulo}...")

        audit_report = _double_check(client, secao.texto, texto_fonte, modelo_auditoria)

        # Sanitização HOSTIL de LLM-speak, cabeçalhos de IA e Alertas vazados
        # Corta frases típicas de co-autoria:
        padroes_conversa = r'^(Aqui est[áa]|Abaixo est[áa]|Segue|Com base nos|Sugiro que|Podemos notar|Espero ter ajudado|Conforme solicitado).*?:?\s*(\n+|$)'
        clean_text = re.sub(padroes_conversa, '', secao.texto, flags=re.IGNORECASE|re.DOTALL)
        # Limpa colchetes de sistema
        clean_text = re.sub(r'\[\s*(ALERTA|Ref).*?\]', '', clean_text, flags=re.IGNORECASE|re.DOTALL)
        # Limpa Markdown headings brutas (#)
        clean_text = re.sub(r'#{1,6}\s+', '', clean_text)

        # ── FILTRO 1: Assinatura do Sistema (Metadados Vazados) ──────────────
        # Remove qualquer linha que contenha a assinatura do Escriba ou número de página gerado pelo sistema.
        # CORREÇÃO: v\d+ não capturava 'v2.0' pois o ponto interrompe \d+.
        # O padrão correto captura versões com decimais: v2.0, v2.1, v10.3, etc.
        clean_text = re.sub(
            r'^.*Escriba\s+v\d+(?:[\.,]\d+)*[^\n]*$',
            '',
            clean_text,
            flags=re.IGNORECASE | re.MULTILINE
        )
        # Remove linhas que são apenas "Página N" ou "Page N" isoladas (rodapés)
        clean_text = re.sub(
            r'^\s*P[áa]gina\s+\d+\s*$',
            '',
            clean_text,
            flags=re.IGNORECASE | re.MULTILINE
        )

        # ── FILTRO 2: Alucinação Normativa (Números de Leis Fabricados) ─────
        # CORREÇÃO: "15.388/2026" usa ponto como separador de milhar (formato BR).
        # O padrão anterior só capturava \d{5,}, que não faz match de "15.388".
        # A nova regex captura tanto "15388" quanto "15.388" e normaliza para comparar o valor.
        def _substituir_lei_suspeita(match):
            numero_raw = match.group(1)          # ex: "15.388" ou "15388"
            ano_raw    = match.group(2)          # ex: "2026"
            numero_int = int(numero_raw.replace('.', '').replace(',', ''))
            ano_int    = int(ano_raw)
            # Leis acima de 14500 com anos >= 2024 são altamente prováveis de alucinação
            if numero_int >= 14500 and ano_int >= 2024:
                return f"[LEI {numero_raw}/{ano_raw} — VERIFICAR FONTE]"
            return match.group(0)

        # Captura: "Lei n. 15.388/2026", "Lei nº 15388/2026", "Lei 15.388/2026", etc.
        clean_text = re.sub(
            r'Lei\s+(?:n[\.\u00ba°]?\s*)?([\d][\d\.]{3,}[\.\d]*)[\/\-](\d{4})',
            _substituir_lei_suspeita,
            clean_text,
            flags=re.IGNORECASE
        )

        # Normaliza linhas em branco múltiplas geradas pelos filtros
        clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)
        clean_text = clean_text.strip()


        resultados.append(PolishResult(
            secao_id=secao.secao_id,
            secao_titulo=secao.secao_titulo,
            texto_original=secao.texto,
            texto_polido=clean_text,
            aprovada=audit_report.get("aprovada", False),
            fidelidade=audit_report.get("fidelidade", {}),
            omissao=audit_report.get("omissao", {}),
            voz=audit_report.get("voz", {}),
            relatorio=audit_report.get("relatorio", "Sem relatório disponível.")
        ))

        if progress_callback:
            progress_callback((i + 1) / total)

    return resultados
