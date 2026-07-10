/**
 * app.js — Escriba v2.0 (Tese de Doutorado)
 */

const state = {
    config: null,
    templates: [],
    filesFatos: [],
    filesModelo: [],
    activeJobId: null,
    pollingInterval: null,
    currentTemplate: null
};

document.addEventListener('DOMContentLoaded', () => {
    initApp();
    setupEvents();
});

async function initApp() {
    try {
        const [cfgRes, tplRes] = await Promise.all([
            fetch('/api/config'),
            fetch('/api/templates')
        ]);
        state.config = await cfgRes.json();
        state.templates = await tplRes.json();

        updateHeaderStatus(state.config.has_api_key);
        populateConfigOptions(state.config);
        document.getElementById('memoryCount').textContent = state.config.memoria_salva_count;
        document.getElementById('footerAutor').textContent = state.config.app_autor;
        document.getElementById('footerAno').textContent = state.config.app_ano;
        populateTemplates(state.templates);
    } catch (err) {
        alert('Erro ao conectar com o servidor. Verifique se server.py esta rodando.');
    }
}

function updateHeaderStatus(hasKey) {
    const ind = document.querySelector('.status-indicator');
    const txt = document.querySelector('.status-text');
    if (hasKey) {
        ind.classList.add('active');
        txt.textContent = 'API Key Ativa';
        document.getElementById('apiKeyContainer').style.display = 'none';
    } else {
        txt.textContent = 'Requer API Key';
        document.getElementById('apiKeyContainer').style.display = 'block';
    }
}

function populateConfigOptions(cfg) {
    const modelSel = document.getElementById('modelSelect');
    modelSel.innerHTML = '';
    Object.keys(cfg.modelos).forEach(k => {
        const o = document.createElement('option');
        o.value = k;
        o.textContent = cfg.modelos[k].nome_exibicao;
        if (k === cfg.modelo_padrao) o.selected = true;
        modelSel.appendChild(o);
    });
    updateModelCaption(modelSel.value);

    const idSel = document.getElementById('idiomaSelect');
    idSel.innerHTML = '';
    cfg.idiomas.forEach(l => {
        const o = document.createElement('option');
        o.value = o.textContent = l;
        idSel.appendChild(o);
    });

    const fmtSel = document.getElementById('formatoSelect');
    fmtSel.innerHTML = '';
    cfg.formatos_exportacao.forEach(f => {
        const o = document.createElement('option');
        o.value = f;
        o.textContent = f.toUpperCase();
        if (f === 'docx') o.selected = true;
        fmtSel.appendChild(o);
    });
}

function updateModelCaption(key) {
    if (!state.config) return;
    const m = state.config.modelos[key];
    if (!m) return;
    document.getElementById('modelCaption').textContent =
        `${m.contexto_tokens.toLocaleString()} tokens | R$ ${m.custo_output_por_milhao_brl.toFixed(2)}/1M`;
}

function populateTemplates(templates) {
    const sel = document.getElementById('templateSelect');
    sel.innerHTML = '';
    templates.forEach(t => {
        const o = document.createElement('option');
        o.value = t.id;
        o.textContent = t.nome;
        sel.appendChild(o);
    });
    const first = templates[0];
    if (first) { sel.value = first.id; selectTemplate(first); }
}

function selectTemplate(template) {
    state.currentTemplate = template;

    const badge = document.getElementById('templateBadge');
    badge.className = 'badge';
    const s = template.status || 'funcional';
    badge.classList.add(s === 'funcional' ? 'badge-funcional' : s === 'placeholder' ? 'badge-placeholder' : 'badge-roadmap');
    badge.textContent = s === 'funcional' ? 'Ativo' : s === 'placeholder' ? 'Em desenvolvimento' : 'Planejado';

    document.getElementById('templateDesc').textContent = template.descricao || '';
    document.getElementById('templateNorma').textContent = template.norma || '';
    document.getElementById('requirementText').textContent = template.requisitos || '';

    renderSections(template.secoes || []);
}

function renderSections(secoes) {
    const list = document.getElementById('sectionsChecklist');
    list.innerHTML = '';
    secoes.forEach((sec, idx) => {
        const item = document.createElement('div');
        item.className = 'section-check-item';
        item.dataset.idx = idx;

        const hasSubchunks = Array.isArray(sec.sub_prompts) && sec.sub_prompts.length > 0;
        const isChecked = sec.obrigatorio || [0,1].includes(idx);

        item.innerHTML = `
            <div class="section-check-main">
                <input type="checkbox" id="sec_${sec.id}" value="${sec.id}" ${isChecked ? 'checked' : ''}>
                <label class="section-check-label" for="sec_${sec.id}">
                    ${sec.numero !== undefined ? `Secao ${sec.numero}: ` : ''}${sec.titulo}
                </label>
                ${sec.obrigatorio ? '<span class="sec-req-badge">Obrigatoria</span>' : ''}
                ${hasSubchunks ? `<button class="sec-expand-btn" data-sec="${sec.id}">ver sub-topicos ▾</button>` : ''}
            </div>
            ${hasSubchunks ? `<div class="section-subchunks" id="sub_${sec.id}">
                ${sec.sub_prompts.map((sp, i) => {
                    const txt = typeof sp === 'string' ? sp : sp.comando || '';
                    const preview = txt.length > 120 ? txt.slice(0, 120) + '...' : txt;
                    return `<div class="subchunk-item"><span class="subchunk-num">Chunk ${i+1}</span>${preview}</div>`;
                }).join('')}
            </div>` : ''}
        `;
        list.appendChild(item);
    });
}

function setupEvents() {
    document.getElementById('templateSelect').addEventListener('change', e => {
        const t = state.templates.find(x => x.id === e.target.value);
        if (t) selectTemplate(t);
    });

    document.getElementById('modelSelect').addEventListener('change', e => updateModelCaption(e.target.value));

    document.getElementById('toggleAdvancedBtn').addEventListener('click', () => {
        const adv = document.getElementById('advancedSettings');
        const btn = document.getElementById('toggleAdvancedBtn');
        const hidden = adv.classList.toggle('hidden');
        btn.textContent = hidden ? 'Configuracoes avancadas ▾' : 'Ocultar configuracoes ▴';
    });

    // Upload duplo
    setupDropzone('dropzoneFatos', 'fileInputFatos', 'fileListFatos', 'fatos');
    setupDropzone('dropzoneModelo', 'fileInputModelo', 'fileListModelo', 'modelo');

    // Selecionar todas / nenhuma secao
    document.getElementById('selectAllSecs').addEventListener('click', () => {
        document.querySelectorAll('#sectionsChecklist input[type=checkbox]').forEach(cb => cb.checked = true);
    });
    document.getElementById('selectNoneSecs').addEventListener('click', () => {
        document.querySelectorAll('#sectionsChecklist input[type=checkbox]').forEach(cb => {
            const item = cb.closest('.section-check-item');
            if (!cb.closest('.section-check-main').querySelector('.sec-req-badge')) cb.checked = false;
        });
    });

    // Expand sub-chunks
    document.getElementById('sectionsChecklist').addEventListener('click', e => {
        if (e.target.classList.contains('sec-expand-btn')) {
            const secId = e.target.dataset.sec;
            const sub = document.getElementById(`sub_${secId}`);
            const item = e.target.closest('.section-check-item');
            if (sub.classList.toggle('open')) {
                item.classList.add('expanded');
                e.target.textContent = 'ocultar ▴';
            } else {
                item.classList.remove('expanded');
                e.target.textContent = 'ver sub-topicos ▾';
            }
        }
    });

    // Limpar memoria
    document.getElementById('clearMemoryBtn').addEventListener('click', async () => {
        if (!confirm('Limpar toda a memoria salva?')) return;
        const r = await fetch('/api/clear-memory', { method: 'POST' });
        const d = await r.json();
        if (d.status === 'success') { document.getElementById('memoryCount').textContent = '0'; }
    });

    // Log: limpar
    document.getElementById('clearLogBtn').addEventListener('click', () => {
        document.getElementById('logConsole').innerHTML = '';
        lastLogCount = 0;
    });

    // Nav tabs resultado
    document.querySelectorAll('.result-nav-tab').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.result-nav-tab').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.result-nav-panel').forEach(p => p.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(`panel${capitalize(btn.dataset.panel)}`).classList.add('active');
        });
    });

    document.getElementById('btnProcessar').addEventListener('click', startPipeline);
}

function setupDropzone(dropId, inputId, listId, slot) {
    const drop = document.getElementById(dropId);
    const input = document.getElementById(inputId);

    drop.addEventListener('click', () => input.click());
    input.addEventListener('change', e => addFiles(e.target.files, slot, listId));
    drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('dragover'); });
    drop.addEventListener('dragleave', () => drop.classList.remove('dragover'));
    drop.addEventListener('drop', e => {
        e.preventDefault();
        drop.classList.remove('dragover');
        addFiles(e.dataTransfer.files, slot, listId);
    });
}

function addFiles(files, slot, listId) {
    const arr = slot === 'fatos' ? state.filesFatos : state.filesModelo;
    for (const f of files) {
        if (!arr.some(x => x.name === f.name && x.size === f.size)) arr.push(f);
    }
    renderFileList(arr, listId, slot);
}

function renderFileList(arr, listId, slot) {
    const list = document.getElementById(listId);
    list.innerHTML = '';
    arr.forEach((f, idx) => {
        const item = document.createElement('div');
        item.className = 'file-item';
        item.innerHTML = `<span class="file-name" title="${f.name}">${f.name}</span>
            <button class="btn-remove-file" data-idx="${idx}" data-slot="${slot}">&times;</button>`;
        list.appendChild(item);
    });
    list.querySelectorAll('.btn-remove-file').forEach(btn => {
        btn.addEventListener('click', () => {
            const i = parseInt(btn.dataset.idx);
            if (btn.dataset.slot === 'fatos') state.filesFatos.splice(i, 1);
            else state.filesModelo.splice(i, 1);
            renderFileList(btn.dataset.slot === 'fatos' ? state.filesFatos : state.filesModelo, listId, slot);
        });
    });
}

async function startPipeline() {
    const tema = document.getElementById('temaGeral').value.trim();
    if (state.filesFatos.length === 0 && !tema) {
        alert('Envie ao menos o arquivo de Fatos do Capitulo ou informe o tema.');
        return;
    }

    const selectedSecs = [...document.querySelectorAll('#sectionsChecklist input[type=checkbox]:checked')].map(cb => cb.value);
    if (selectedSecs.length === 0) { alert('Selecione ao menos uma secao.'); return; }

    if (state.config && !state.config.has_api_key) {
        const key = document.getElementById('apiKeyInput').value.trim();
        if (!key) { alert('Informe a chave API do Maritaca.'); return; }
    }

    // Troca de painel
    document.getElementById('emptyState').classList.add('hidden');
    document.getElementById('completedState').classList.add('hidden');
    document.getElementById('processingState').classList.remove('hidden');
    document.getElementById('logConsole').innerHTML = '';
    lastLogCount = 0;
    updateProgress(0, 'Iniciando...');
    resetPipelineSteps();

    const fd = new FormData();
    state.filesFatos.forEach(f => fd.append('arquivos', f));
    state.filesModelo.forEach(f => fd.append('arquivos', f));
    fd.append('tema', tema);
    fd.append('template_id', document.getElementById('templateSelect').value);
    fd.append('secoes_selecionadas', JSON.stringify(selectedSecs));
    fd.append('modelo_selecionado', document.getElementById('modelSelect').value);
    fd.append('idioma', document.getElementById('idiomaSelect').value);
    fd.append('formato_export', document.getElementById('formatoSelect').value);
    fd.append('incluir_markers', document.getElementById('incluirMarkers').checked);
    fd.append('usar_memoria', document.getElementById('usarMemoria').checked);
    const escopoSel = document.querySelector('input[name="escopoMemoria"]:checked');
    fd.append('escopo_memoria', escopoSel ? escopoSel.value : 'Tudo');
    if (state.config && !state.config.has_api_key) {
        fd.append('api_key_override', document.getElementById('apiKeyInput').value.trim());
    }

    document.getElementById('btnProcessar').disabled = true;
    try {
        const res = await fetch('/api/generate', { method: 'POST', body: fd });
        if (!res.ok) { const e = await res.json(); throw new Error(e.detail || 'Erro desconhecido'); }
        const data = await res.json();
        state.activeJobId = data.job_id;
        startPolling(data.job_id);
    } catch (err) {
        document.getElementById('btnProcessar').disabled = false;
        appendLog('ERRO: ' + err.message);
        alert('Falha ao iniciar: ' + err.message);
    }
}

let lastLogCount = 0;

function startPolling(jobId) {
    if (state.pollingInterval) clearInterval(state.pollingInterval);
    state.pollingInterval = setInterval(async () => {
        try {
            const res = await fetch(`/api/status/${jobId}`);
            if (!res.ok) return;
            const job = await res.json();
            updateProgress(job.progress, job.progress_text);
            renderLogs(job.logs);
            updatePipelineSteps(job.progress);
            updateChunkTracker(job);

            if (job.status === 'completed') {
                clearInterval(state.pollingInterval);
                document.getElementById('btnProcessar').disabled = false;
                showCompleted(jobId, job.results);
            } else if (job.status === 'failed') {
                clearInterval(state.pollingInterval);
                document.getElementById('btnProcessar').disabled = false;
                appendLog('ERRO: ' + job.error);
                alert('Processamento falhou: ' + job.error);
            }
        } catch (e) { appendLog('Erro de comunicacao: ' + e.message); }
    }, 1000);
}

function updateProgress(p, text) {
    const pct = Math.round(p * 100);
    document.getElementById('progressBarFill').style.width = pct + '%';
    document.getElementById('progressPercent').textContent = pct + '%';
    document.getElementById('progressText').textContent = stripEmojis(text || '');
}

function appendLog(line) {
    const c = document.getElementById('logConsole');
    const d = document.createElement('div');
    d.className = 'log-line';
    d.textContent = stripEmojis(line);
    c.appendChild(d);
    c.scrollTop = c.scrollHeight;
}

function renderLogs(logs) {
    if (!logs) return;
    for (let i = lastLogCount; i < logs.length; i++) appendLog(logs[i]);
    lastLogCount = logs.length;
}

function resetPipelineSteps() {
    ['card_ingestor','card_comprehension','card_generator','card_polisher','card_exporter'].forEach(id => {
        const el = document.getElementById(id);
        el.className = 'pipeline-step';
        el.querySelector('.step-status-badge').textContent = 'Aguardando';
    });
    lastLogCount = 0;
}

function updatePipelineSteps(p) {
    const steps = [
        { id: 'card_ingestor',     start: 0.05, end: 0.20, label: 'Lendo fonte' },
        { id: 'card_comprehension',start: 0.25, end: 0.40, label: 'Analisando' },
        { id: 'card_generator',    start: 0.45, end: 0.75, label: 'Redigindo' },
        { id: 'card_polisher',     start: 0.78, end: 0.88, label: 'Auditando' },
        { id: 'card_exporter',     start: 0.90, end: 1.00, label: 'Exportando' },
    ];
    steps.forEach(s => {
        const el = document.getElementById(s.id);
        const badge = el.querySelector('.step-status-badge');
        if (p >= s.end) {
            el.className = 'pipeline-step done';
            badge.textContent = 'Concluido';
        } else if (p >= s.start) {
            el.className = 'pipeline-step active';
            badge.textContent = s.label;
        }
    });
}

function updateChunkTracker(job) {
    const counter = document.getElementById('chunkCounter');
    const container = document.getElementById('chunkBarContainer');
    const eta = document.getElementById('pipelineEta');

    if (job.chunk_atual !== undefined && job.total_chunks !== undefined) {
        counter.textContent = `${job.chunk_atual}/${job.total_chunks}`;
        eta.textContent = job.eta || '';
        // Barra de segmentos
        if (container.children.length !== job.total_chunks) {
            container.innerHTML = '';
            for (let i = 0; i < job.total_chunks; i++) {
                const seg = document.createElement('div');
                seg.className = 'chunk-bar-segment';
                container.appendChild(seg);
            }
        }
        [...container.children].forEach((seg, i) => {
            seg.className = 'chunk-bar-segment' + (i < job.chunk_atual - 1 ? ' done' : i === job.chunk_atual - 1 ? ' active' : '');
        });
    }
}

function showCompleted(jobId, results) {
    document.getElementById('processingState').classList.add('hidden');
    document.getElementById('completedState').classList.remove('hidden');

    const fmt = document.getElementById('formatoSelect').value.toUpperCase();
    document.getElementById('downloadFormatText').textContent = fmt;
    document.getElementById('resultTitle').textContent = state.currentTemplate ? state.currentTemplate.nome : 'Capitulo gerado';
    document.getElementById('downloadBtn').onclick = () => window.open(`/api/download/${jobId}`, '_blank');

    // Reset nav para Texto
    document.querySelectorAll('.result-nav-tab').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.result-nav-panel').forEach(p => p.classList.remove('active'));
    document.getElementById('navTabTexto').classList.add('active');
    document.getElementById('panelTexto').classList.add('active');

    // Mapa semantico
    const map = results?.comprehension_result;
    if (map) {
        document.getElementById('classificationValue').textContent = map.classificacao || 'Analise de Conteudo (Bardin)';
        document.getElementById('academicSummaryValue').textContent = map.resumo_academico || '';
        renderCategories(map.temas || []);
        renderEvidences(map.citacoes_chave || []);
    }

    // Tabs de secoes
    renderSectionTabs(results?.polish_results || []);

    // Auditoria consolidada
    renderAuditSummary(results?.polish_results || []);
}

function renderCategories(temas) {
    const list = document.getElementById('categoriesList');
    list.innerHTML = '';
    if (!temas.length) { list.innerHTML = '<p class="field-help">Nenhuma categoria identificada.</p>'; return; }
    temas.forEach((t, i) => {
        const card = document.createElement('div');
        card.className = 'category-card';
        card.innerHTML = `<div class="category-title">Categoria ${i+1}: ${t.titulo||''}</div>
            <div class="category-summary">${t.resumo_tema||''}</div>
            <div class="category-points">${(t.pontos_chave||[]).map(p=>`<div class="category-point-item">- ${p}</div>`).join('')}</div>`;
        list.appendChild(card);
    });
}

function renderEvidences(cits) {
    const list = document.getElementById('evidenceList');
    list.innerHTML = '';
    if (!cits.length) { list.innerHTML = '<p class="field-help">Nenhuma citacao extraida.</p>'; return; }
    cits.forEach(c => {
        const d = document.createElement('div');
        d.className = 'evidence-item';
        d.innerHTML = `<p class="evidence-text">"${(c.texto||'').replace(/["""']/g,'').trim()}"</p>
            <small class="evidence-meta">— <strong>${c.contexto_autor||'N/D'}</strong> | ${c.pagina_paragrafo||'N/D'}</small>`;
        list.appendChild(d);
    });
}

function renderSectionTabs(polishResults) {
    const header = document.getElementById('tabsHeader');
    const content = document.getElementById('tabsContent');
    header.innerHTML = '';
    content.innerHTML = '';
    if (!polishResults.length) { content.innerHTML = '<p style="padding:1.5rem">Nenhuma secao gerada.</p>'; return; }

    polishResults.forEach((res, idx) => {
        const btn = document.createElement('button');
        btn.className = 'tab-btn' + (idx === 0 ? ' active' : '');
        btn.id = `tab_btn_${idx}`;
        btn.textContent = res.secao_titulo || `Secao ${idx+1}`;
        btn.addEventListener('click', () => switchTab(idx, polishResults.length));
        header.appendChild(btn);

        const pane = document.createElement('div');
        pane.className = 'tab-pane' + (idx === 0 ? ' active' : '');
        pane.id = `tab_pane_${idx}`;

        const verdictClass = res.aprovada ? 'verdict-success' : 'verdict-alert';
        const verdictMsg = res.aprovada ? 'Veredito: Aprovado' : 'Veredito: Alertas Detectados';
        const fidC = (res.fidelidade?.status==='OK') ? 'ok' : 'alerta';
        const omiC = (res.omissao?.status==='OK') ? 'ok' : 'alerta';
        const vozC = (res.voz?.status==='OK') ? 'ok' : 'alerta';

        pane.innerHTML = `
            <div class="secao-preview-text">${markdownToHtml(res.texto_polido)}</div>
            <div class="audit-accordion">
                <div class="audit-accordion-header" onclick="toggleAudit(${idx})">
                    <span class="audit-header-title">Auditoria de fidelidade — ${res.aprovada ? 'Aprovado' : 'Revisar'}</span>
                    <span id="audit_arrow_${idx}">▾</span>
                </div>
                <div class="audit-accordion-content hidden" id="audit_content_${idx}">
                    <div class="audit-verdict-box ${verdictClass}"><strong>${verdictMsg}</strong><p>${res.relatorio||''}</p></div>
                    <div class="audit-metrics-grid">
                        <div class="audit-metric-card"><span class="metric-name">Fidelidade</span>
                            <span class="metric-status"><span class="status-dot ${fidC}"></span>${res.fidelidade?.status||'N/A'}</span></div>
                        <div class="audit-metric-card"><span class="metric-name">Omissao</span>
                            <span class="metric-status"><span class="status-dot ${omiC}"></span>${res.omissao?.status||'N/A'}</span></div>
                        <div class="audit-metric-card"><span class="metric-name">Voz</span>
                            <span class="metric-status"><span class="status-dot ${vozC}"></span>${res.voz?.status||'N/A'}</span></div>
                    </div>
                </div>
            </div>`;
        content.appendChild(pane);
    });
}

function switchTab(idx, total) {
    for (let i = 0; i < total; i++) {
        document.getElementById(`tab_btn_${i}`)?.classList.toggle('active', i === idx);
        document.getElementById(`tab_pane_${i}`)?.classList.toggle('active', i === idx);
    }
}

window.toggleAudit = function(idx) {
    const c = document.getElementById(`audit_content_${idx}`);
    const a = document.getElementById(`audit_arrow_${idx}`);
    c.classList.toggle('hidden');
    a.textContent = c.classList.contains('hidden') ? '▾' : '▴';
};

function renderAuditSummary(polishResults) {
    const panel = document.getElementById('auditSummary');
    panel.innerHTML = '';
    if (!polishResults.length) { panel.innerHTML = '<p>Nenhum resultado de auditoria disponivel.</p>'; return; }
    polishResults.forEach(res => {
        const item = document.createElement('div');
        item.className = 'audit-summary-item';
        item.innerHTML = `
            <div class="audit-summary-title">${res.secao_titulo || 'Secao'}</div>
            <span class="audit-verdict-pill ${res.aprovada ? 'aprovado' : 'alerta'}">${res.aprovada ? 'Aprovado' : 'Alerta'}</span>
            <div class="audit-summary-detail">${res.relatorio || ''}</div>`;
        panel.appendChild(item);
    });
}

function markdownToHtml(text) {
    if (!text) return '';
    let h = text
        .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
        .replace(/^### (.*?)$/gm,'<h3>$1</h3>')
        .replace(/^## (.*?)$/gm,'<h2>$1</h2>')
        .replace(/^# (.*?)$/gm,'<h1>$1</h1>')
        .replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>')
        .replace(/\*(.*?)\*/g,'<em>$1</em>');
    return h.split(/\n\n+/).map(p => {
        const t = p.trim();
        if (!t) return '';
        if (t.startsWith('<h')) return t;
        return `<p>${t.replace(/\n/g,'<br>')}</p>`;
    }).join('');
}

function stripEmojis(text) {
    if (!text) return '';
    return text.replace(/[\u2700-\u27BF]|[\uE000-\uF8FF]|\uD83C[\uDC00-\uDFFF]|\uD83D[\uDC00-\uDFFF]|[\u2011-\u26FF]|\uD83E[\uDD00-\uDFFF]/g,'').trim();
}

function capitalize(s) { return s.charAt(0).toUpperCase() + s.slice(1); }
