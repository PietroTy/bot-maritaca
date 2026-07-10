import sys

with open("/home/pit/Programas/Scripts/Escriba/modules/generator.py", "r") as f:
    code = f.read()

start_anchor = '        skeleton_expansion = secao.get("skeleton_expansion", False)'
end_anchor = '        resultados.append(GeneratorResult('

start_idx = code.find(start_anchor)
end_idx = code.find(end_anchor, start_idx)

new_logic = """        skeleton_expansion = secao.get("skeleton_expansion", False)
        sub_prompts = secao.get("sub_prompts", [secao.get("prompt", "")])
        texto_gerado_acc = []
        contexto_interno = contexto_anterior or ""
        
        for idx_sub, base_prompt in enumerate(sub_prompts):
            if not base_prompt: continue
            
            # NLP Extractor (NER)
            from .extractor import extract_required_entities_from_prompt
            entidades_obrig = extract_required_entities_from_prompt(base_prompt, api_key)
            
            # Preparação de injestão comum
            material_inj = ""
            if custom_system_prompt:
                material_inj += f"\\n\\nMATERIAL DE ORIGEM (FATOS):\\n\\\"\\\"\\\"\\n{texto_fatos[:10000]}\\n\\\"\\\"\\\"\\n"
                if texto_modelo:
                     material_inj += f"\\nMATERIAL DE REFERÊNCIA (ESTILO):\\n\\\"\\\"\\\"\\n{texto_modelo[:8000]}\\n\\\"\\\"\\\""
            
            # --- FLUXO SKELETON EXPANSION ---
            if skeleton_expansion:
                if status_callback: status_callback(f"⚙️ Mapeando Esqueleto do Tópico {i+1}...")
                
                req_esqueleto = (
                    "GERAÇÃO DE ESQUELETO MESTRE (DRAFT):\\n"
                    "Crie um índice fático enumerado de 3 a 5 tópicos principais que você abordaria para resolver a seguinte instrução.\\n"
                    "Responda APENAS com os bullets (iniciando com '- '), não escreva o texto final.\\n\\n"
                    f"INSTRUÇÃO:\\n{base_prompt}"
                )
                
                esqueleto_bruto = _chamar_api(client, modelo_geracao, system_prompt, req_esqueleto + material_inj)
                linhas_esqueleto = [l.strip() for l in esqueleto_bruto.split('\\n') if l.strip().startswith('-')]
                if not linhas_esqueleto:
                    linhas_esqueleto = [l.strip() for l in esqueleto_bruto.split('\\n') if len(l.strip()) > 10][:4]
                
                for idx_linha, linha_index in enumerate(linhas_esqueleto):
                    if status_callback: status_callback(f"⚙️ Deep Render ({idx_linha+1}/{len(linhas_esqueleto)}): {linha_index[:30]}...")
                    
                    user_prompt = (
                        f"Você está expandindo UMA ÚNICA LINHA de um índice maior. Escreva de 3 a 5 parágrafos DENSOS "
                        f"abortando OBRIGATÓRIA E EXCLUSIVAMENTE o seguinte tópico: '{linha_index}'.\\n"
                        "Proibido iniciar conclusões finais ou pular de assunto.\\n\\n"
                        f"Contexto Macro da Seção: {base_prompt}"
                    )
                    
                    if contexto_interno:
                        user_prompt = (
                            "CONTEXTO DE CONTINUIDADE (Acompanhe o fluxo do que você já escreveu logo acima):\\n"
                            f"{contexto_interno}\\n--- FIM DO CONTEXTO ---\\n\\n" + user_prompt
                        )
                    
                    # Retry
                    tentativas = 0
                    max_retries = 1
                    texto_gerado_sub = ""
                    while tentativas <= max_retries:
                        texto_gerado_sub = _chamar_api(client, modelo_geracao, system_prompt, user_prompt + material_inj)
                        falhas = [e for e in entidades_obrig if e.lower() not in texto_gerado_sub.lower()]
                        if not falhas: break
                        tentativas += 1
                        user_prompt += f"\\n\\n[ERRO DE VALIDAÇÃO]: Inclua impreterivelmente estes fatos/autores: {falhas}."
                        
                    texto_gerado_acc.append(texto_gerado_sub)
                    contexto_interno = texto_gerado_sub
            
            # --- FLUXO NORMAL OU COMUM MICRO-CHUNKING ---
            else:
                if status_callback: status_callback(f"⚙️ Gerando: {secao['titulo']} (Pedaço {idx_sub+1}/{len(sub_prompts)})...")
                user_prompt = base_prompt
                if contexto_interno:
                    user_prompt = (
                        "CONTEXTO DE CONTINUIDADE (Acompanhe o fluxo do que você já escreveu logo acima):\\n"
                        f"{contexto_interno}\\n--- FIM DO CONTEXTO ---\\n\\n" + user_prompt
                    )
                
                tentativas = 0
                max_retries = 2
                texto_gerado_sub = ""
                while tentativas <= max_retries:
                    texto_gerado_sub = _chamar_api(client, modelo_geracao, system_prompt, user_prompt + material_inj)
                    falhas = [e for e in entidades_obrig if e.lower() not in texto_gerado_sub.lower()]
                    if not falhas: break
                    tentativas += 1
                    user_prompt += f"\\n\\n[ERRO DE VALIDAÇÃO]: Inclua obrigatoriamente estes autores/leis no texto: {falhas}."
                    
                texto_gerado_acc.append(texto_gerado_sub)
                contexto_interno = texto_gerado_sub

        texto_gerado = "\\n\\n".join(texto_gerado_acc)

"""

final_code = code[:start_idx] + new_logic + code[end_idx:]

with open("/home/pit/Programas/Scripts/Escriba/modules/generator.py", "w") as f:
    f.write(final_code)
