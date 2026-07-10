"""
server.py — Servidor Backend FastAPI para o Escriba
Orquestra o pipeline acadêmico e expõe APIs para a interface web.
"""

import os
import uuid
import threading
import hashlib
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
import io

import config
import modules.persistence as persistence
from modules.ingestor import ingest_document, IngestorResult
from modules.comprehension import comprehend
from modules.generator import generate
from modules.polisher import polish
from modules.exporter import export

# Inicializa diretórios de persistência
persistence.ensure_dir()

app = FastAPI(title="Escriba API", version="2.0")

# Dicionários em memória para gerenciar tarefas e arquivos exportados
jobs = {}
exported_files = {}

# Certifica-se de que a pasta static existe
os.makedirs("static", exist_ok=True)

def serialize_comprehension(comp_res):
    if not comp_res:
        return None
    return {
        "classificacao": getattr(comp_res, "classificacao", ""),
        "resumo_academico": getattr(comp_res, "resumo_academico", ""),
        "temas": getattr(comp_res, "temas", []),
        "citacoes_chave": getattr(comp_res, "citacoes_chave", [])
    }

def serialize_polish_results(polish_results):
    if not polish_results:
        return []
    serialized = []
    for r in polish_results:
        serialized.append({
            "secao_id": getattr(r, "secao_id", ""),
            "secao_titulo": getattr(r, "secao_titulo", ""),
            "texto_original": getattr(r, "texto_original", ""),
            "texto_polido": getattr(r, "texto_polido", ""),
            "aprovada": getattr(r, "aprovada", False),
            "fidelidade": getattr(r, "fidelidade", {}),
            "omissao": getattr(r, "omissao", {}),
            "voz": getattr(r, "voz", {}),
            "relatorio": getattr(r, "relatorio", "")
        })
    return serialized

def run_pipeline_worker(
    job_id: str,
    arquivos_bytes_e_nomes: List[tuple],
    tema: str,
    template_id: str,
    secoes_selecionadas: List[str],
    modelo_selecionado: str,
    idioma: str,
    formato_export: str,
    incluir_markers: bool,
    usar_memoria: bool,
    escopo_memoria: str,
    api_key_override: Optional[str]
):
    job = jobs[job_id]
    
    def log_status(msg: str):
        job["logs"].append(msg)
        job["progress_text"] = msg

    try:
        # Resolve chave da API
        api_key = api_key_override or config.get_api_key()
        if not api_key:
            raise ValueError("Configure a chave da API para iniciar a geração.")

        template_atual = config.carregar_template(template_id)
        
        # ─── Módulo 1: Ingestão ───────────────────────────
        job["progress"] = 0.05
        log_status("Lendo e normalizando o material-fonte...")
        
        if arquivos_bytes_e_nomes:
            texto_fatos_list = []
            texto_modelo_list = []
            hashes = []
            metadados_gerais = []
            
            for idx, (arg_bytes, arg_name) in enumerate(arquivos_bytes_e_nomes):
                i_res = ingest_document(arg_bytes, arg_name, status_callback=log_status)
                bloco = f"\n--- INÍCIO DO DOCUMENTO {idx+1}: {arg_name} ---\n{i_res.texto}\n--- FIM DO DOCUMENTO {idx+1} ---\n"
                
                nome_lower = arg_name.lower()
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
            cache_key = f"{hash_total}__{tema}__{modelo_selecionado}__{idioma}__{'-'.join(sorted(secoes_selecionadas))}__{incluir_markers}"
        else:
            texto_fatos = ""
            texto_modelo = ""
            texto_fonte = ""
            cache_key = f"no_file__{tema}__{modelo_selecionado}__{idioma}__{incluir_markers}"
            log_status("Sem material-fonte — usando apenas o tema informado.")
            log_status("Leitura da fonte concluída")

        job["progress"] = 0.20
        
        # Cache check (usando um cache compartilhado ou local da thread)
        # O backend gerencia o cache no dicionário global jobs ou similar
        global_cache = jobs.get("_global_cache", {})
        if cache_key in global_cache:
            log_status("Conteúdo idêntico encontrado no cache. Reutilizando resultado anterior.")
            cached = global_cache[cache_key]
            
            comprehension_result = cached["comprehension_result"]
            generator_results = cached["generator_results"]
            polish_results = cached["polish_results"]
            
            job["progress"] = 0.90
            log_status("Cache carregado")
        else:
            # ─── Módulo 2: Compreensão ──────────────────────────
            job["progress"] = 0.25
            log_status("Organizando temas, conceitos e evidências...")
            comp_result = comprehend(texto_fonte, status_callback=log_status)
            comprehension_result = serialize_comprehension(comp_result)
            log_status("Módulo 2 concluído")
            job["progress"] = 0.40
            
            # ─── Módulo 3: Geração ──────────────────────────────
            log_status("Redigindo as seções selecionadas...")
            
            def gen_progress(frac):
                job["progress"] = 0.45 + (frac * 0.30)
                log_status(f"Gerando seções... {int(frac * 100)}%")

            contexto_anterior = None
            memoria_carregada = persistence.load_session()
            if usar_memoria and memoria_carregada:
                scope_key = "tudo" if escopo_memoria == "Tudo" else "ultima"
                contexto_anterior = persistence.build_context(memoria_carregada, scope=scope_key)

            gen_res = generate(
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
            
            # Mapeia generator_results para dicionários
            generator_results = []
            for g in gen_res:
                generator_results.append({
                    "secao_id": g.secao_id,
                    "secao_titulo": g.secao_titulo,
                    "texto": g.texto,
                    "modelo_usado": g.modelo_usado
                })
            
            job["progress"] = 0.75
            log_status("Redação acadêmica concluída")

            # ─── Módulo 4: Polimento ────────────────────────────
            job["progress"] = 0.78
            log_status("Auditando fidelidade e consistência textual...")
            
            # Recria objetos temporários para polisher
            from modules.generator import GeneratorResult
            gen_objects = [GeneratorResult(g["secao_id"], g["secao_titulo"], g["texto"], g["modelo_usado"]) for g in generator_results]
            
            pol_res = polish(
                secoes_geradas=gen_objects,
                texto_fonte=texto_fatos,
                api_key=api_key,
                status_callback=log_status,
            )
            polish_results = serialize_polish_results(pol_res)
            
            # Atualiza o cache global
            global_cache[cache_key] = {
                "comprehension_result": comprehension_result,
                "generator_results": generator_results,
                "polish_results": polish_results
            }
            jobs["_global_cache"] = global_cache
            
            job["progress"] = 0.88
            log_status("Auditoria de fidelidade concluída")

        # ─── Módulo 5: Exportação ───────────────────────────
        job["progress"] = 0.90
        log_status("Preparando o arquivo final...")
        
        # Reconstrói objetos de resultado polido para o exporter
        from modules.polisher import PolishResult
        polish_objects = []
        for r in polish_results:
            polish_objects.append(PolishResult(
                secao_id=r["secao_id"],
                secao_titulo=r["secao_titulo"],
                texto_original=r["texto_original"],
                texto_polido=r["texto_polido"],
                aprovada=r["aprovada"],
                fidelidade=r["fidelidade"],
                omissao=r["omissao"],
                voz=r["voz"],
                relatorio=r["relatorio"]
            ))

        export_bytes, export_nome, export_mime = export(
            polish_results=polish_objects,
            formato=formato_export,
            tema=tema or "Documento Gerado",
            idioma=idioma,
            status_callback=None
        )
        
        # Salva em cache de download
        exported_files[job_id] = (export_bytes, export_nome, export_mime)
        
        # Salva na memória persistente (Tese)
        memoria_tese = persistence.load_session()
        for res in polish_results:
            # Evita duplicatas
            memoria_tese = [m for m in memoria_tese if m["secao_id"] != res["secao_id"]]
            memoria_tese.append({
                "secao_id": res["secao_id"],
                "secao_titulo": res["secao_titulo"],
                "texto": res["texto_polido"],
            })
        persistence.save_session(memoria_tese)
        
        job["progress"] = 1.0
        log_status("Documento gerado com sucesso!")
        job["status"] = "completed"
        job["results"] = {
            "comprehension_result": comprehension_result,
            "polish_results": polish_results,
            "export_nome": export_nome,
            "export_mime": export_mime
        }

    except Exception as e:
        job["progress"] = 0.0
        log_status(f"ERRO: {str(e)}")
        job["status"] = "failed"
        job["error"] = str(e)


@app.get("/api/config")
def get_backend_config():
    """Retorna constantes de configuração para o frontend."""
    templates = config.listar_templates()
    modelos_info = {}
    for key, value in config.MODELOS.items():
        modelos_info[key] = {
            "nome_exibicao": value["nome_exibicao"],
            "descricao": value["descricao"],
            "contexto_tokens": value["contexto_tokens"],
            "custo_output_por_milhao_brl": value["custo_output_por_milhao_brl"]
        }
        
    return {
        "app_nome": "Escriba",
        "app_subtitulo": config.APP_SUBTITULO,
        "app_autor": config.APP_AUTOR,
        "app_ano": config.APP_ANO,
        "modelos": modelos_info,
        "modelo_padrao": config.MODELO_PADRAO_GERACAO,
        "idiomas": config.IDIOMAS,
        "formatos_exportacao": config.FORMATOS_EXPORTACAO,
        "has_api_key": bool(config.get_api_key()),
        "memoria_salva_count": len(persistence.load_session())
    }


@app.get("/api/templates")
def get_templates():
    """Retorna lista de templates disponíveis."""
    return config.listar_templates()


@app.post("/api/clear-memory")
def clear_memory():
    """Limpa a memória persistente da tese."""
    persistence.clear_session()
    return {"status": "success", "message": "Memória acadêmica limpa."}


@app.post("/api/generate")
async def start_generation(
    background_tasks: BackgroundTasks,
    api_key_override: Optional[str] = Form(None),
    template_id: str = Form(...),
    tema: str = Form(""),
    secoes_selecionadas: str = Form(...),  # JSON string contendo lista de IDs
    modelo_selecionado: str = Form(...),
    idioma: str = Form(...),
    formato_export: str = Form(...),
    incluir_markers: bool = Form(True),
    usar_memoria: bool = Form(True),
    escopo_memoria: str = Form("Tudo"),
    arquivos: List[UploadFile] = File([])
):
    # Desempacota seções selecionadas
    try:
        import json
        secoes_list = json.loads(secoes_selecionadas)
    except Exception:
        raise HTTPException(status_code=400, detail="secoes_selecionadas deve ser um array JSON válido.")
        
    if not tema and not arquivos:
        raise HTTPException(status_code=400, detail="Envie um material-fonte ou informe o tema do documento.")
        
    if not secoes_list:
        raise HTTPException(status_code=400, detail="Selecione pelo menos uma seção para gerar.")

    # Lê os arquivos de upload em bytes para passar para a thread
    arquivos_bytes_e_nomes = []
    for file in arquivos:
        if file.filename:
            content = await file.read()
            arquivos_bytes_e_nomes.append((content, file.filename))

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "running",
        "progress": 0.0,
        "progress_text": "Iniciando processo...",
        "logs": [],
        "error": None,
        "results": None
    }

    # Dispara a thread de worker em background para evitar timeouts HTTP
    background_tasks.add_task(
        run_pipeline_worker,
        job_id=job_id,
        arquivos_bytes_e_nomes=arquivos_bytes_e_nomes,
        tema=tema,
        template_id=template_id,
        secoes_selecionadas=secoes_list,
        modelo_selecionado=modelo_selecionado,
        idioma=idioma,
        formato_export=formato_export,
        incluir_markers=incluir_markers,
        usar_memoria=usar_memoria,
        escopo_memoria=escopo_memoria,
        api_key_override=api_key_override
    )

    return {"job_id": job_id}


@app.get("/api/status/{job_id}")
def get_job_status(job_id: str):
    """Obtém o status de processamento da tarefa."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    return jobs[job_id]


@app.get("/api/download/{job_id}")
def download_result(job_id: str):
    """Download do documento gerado no formato final."""
    if job_id not in exported_files:
        raise HTTPException(status_code=404, detail="Arquivo para download não encontrado.")
    
    export_bytes, export_nome, export_mime = exported_files[job_id]
    
    # Retorna o binário
    return Response(
        content=export_bytes,
        media_type=export_mime,
        headers={
            "Content-Disposition": f'attachment; filename="{export_nome}"'
        }
    )

# Serve arquivos estáticos (Frontend)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
