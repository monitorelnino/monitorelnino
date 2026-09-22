// ===== blog.html · quadros de situação do monitoramento + lista de textos (22/09/2026) =====
// Os quatro quadros leem os MESMOS arquivos que as páginas correspondentes (nenhum número próprio):
//   MARÉ Legal   → data/indice.json, data/estados.json, data/municipios.json, data/meta.json (rodada semanal)
//   MARÉ Saúde   → data/monitor_saude.json (resumo e resposta sanitária)
//   Defesa civil → data/resposta/por_uf.json (nacional) + alertas/avisos de data/sinais_risco.json (diário)
//   Sinais físicos → data/sinais_risco.json (ONI, focos INPE, Monitor de Secas, prognóstico CPTEC)
// Cada quadro tem crédito próprio (MonitorMapas.credito) com a data da SUA fonte — as cadências diferem.
// Regra editorial de legendas: só descreve (variável, período, unidade); nenhum adjetivo ou juízo.
(function () {
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const el = id => document.getElementById(id);
  const num = (v, casas) => (v == null || isNaN(v)) ? '—' : Number(v).toLocaleString('pt-BR', { minimumFractionDigits: casas || 0, maximumFractionDigits: casas || 0 });
  const set = (id, txt) => { const e = el(id); if (e) e.textContent = txt; };
  const carregar = f => fetch(f).then(r => r.ok ? r.json() : null).catch(() => null);
  const somaUF = (sinais, chave, campo) => { let t = 0, tem = false; Object.values((sinais && sinais.uf) || {}).forEach(u => { const v = u && u[chave] && u[chave][campo]; if (typeof v === 'number') { t += v; tem = true; } }); return tem ? t : null; };
  const dataDe = (sinais, fonte) => { const f = sinais && sinais.fontes && sinais.fontes[fonte]; return (f && f.consultado_em) || (sinais && sinais.gerado_em) || null; };

  function legal(indice, estados, municipios, meta) {
    if (!indice || !estados) return;
    const ufs = Object.keys(indice).filter(k => k.length === 2);
    const tot = ufs.map(u => indice[u].total).filter(v => typeof v === 'number');
    const media = tot.length ? Math.round(tot.reduce((a, b) => a + b, 0) / tot.length * 10) / 10 : null;
    set('stLegalMedia', num(media, 1));
    const st = (estados.ufs || []).map(u => u.status);
    set('stLegalNovo', num(st.filter(s => s === 'NOVO').length) + ' de 27');
    set('stLegalRecorrente', num(st.filter(s => s === 'READ' || s === 'VIG').length) + ' de 27');
    if (Array.isArray(municipios)) set('stLegalMun', num(municipios.filter(m => m.categoria === 'plano').length));
    MonitorMapas.credito('cardLegal', { fontes: ['diários oficiais estaduais e municipais', 'Censo 2022'], data: (meta && (meta.atualizado_em || meta.corte)) || null });
  }

  function saude(ms) {
    if (!ms || !ms.resumo) return;
    set('stSaudeMedia', num(ms.resumo.media_das_verificadas, 1));
    set('stSaudeUfs', num(ms.resumo.verificadas) + ' de 27');
    set('stSaudePlanos', num(ms.resumo.planos_municipais_lidos));
    const r = ms.resposta || {};
    set('stSaudeEmerg', num(r.emergencias || 0) + (Array.isArray(r.ufs) && r.ufs.length ? ' (' + r.ufs.join(', ') + ')' : ''));
    MonitorMapas.credito('cardSaude', { fontes: ['planos estaduais e municipais de saúde', 'DOU (ESPIN)'], data: ms.gerado_em || ms.corte || null });
  }

  function defesa(resp, sinais) {
    const n = resp && resp.nacional;
    if (n) {
      set('stRespIndice', num(n.indice, 1));
      set('stRespMun', num(n.n_municipios) + ' de ' + num(n.total_municipios) + ' · ' + num((n.fracao_populacao || 0) * 100, 1) + '% da população');
      set('stRespRec', num(n.reconhecidos) + (typeof n.decretados_sem_reconhecimento === 'number' ? ' · ' + num(n.decretados_sem_reconhecimento) + ' sem reconhecimento' : ''));
    }
    const cem = somaUF(sinais, 'alertas_cemaden', 'total'), inm = somaUF(sinais, 'avisos_inmet', 'total');
    set('stRespAlertas', (cem == null ? '—' : num(cem) + ' alertas') + ' · ' + (inm == null ? '—' : num(inm) + ' avisos'));
    MonitorMapas.credito('cardDefesa', { fontes: ['diários oficiais', 'S2iD', 'CEMADEN', 'INMET'], data: dataDe(sinais, 'cemaden_alertas') || (resp && resp.gerado_em) || null });
  }

  function fisico(sinais) {
    if (!sinais) return;
    const oni = sinais.enos && sinais.enos.oni && Array.isArray(sinais.enos.oni.serie) ? sinais.enos.oni.serie[sinais.enos.oni.serie.length - 1] : null;
    if (oni) { set('stOni', (oni.anomalia > 0 ? '+' : '') + num(oni.anomalia, 1)); set('stOniTri', oni.trimestre + '/' + oni.ano); }
    const focos = somaUF(sinais, 'fogo', 'focos_24h');
    set('stFocos', focos == null ? '—' : num(focos) + ' (' + Object.keys(sinais.uf || {}).length + ' UFs)');
    let s2 = 0, comSeca = 0; Object.values(sinais.uf || {}).forEach(u => { const c = u && u.secas && u.secas.cumulativa_pct; if (c) { comSeca++; if ((c.S2 || 0) > 0) s2++; } });
    const mapa = (() => { for (const u of Object.values(sinais.uf || {})) if (u && u.secas && u.secas.mapa) return u.secas.mapa; return null; })();
    set('stSeca', comSeca ? num(s2) + ' de ' + num(comSeca) + (mapa ? ' · mapa de ' + mapa.toLowerCase() : '') : '—');
    const prog = sinais.enos && sinais.enos.prognostico;
    if (prog && Array.isArray(prog.chuva) && prog.chuva.length) set('stProg', prog.chuva.map(c => c.regiao.split(/ [—(]/)[0] + ': ' + c.tendencia).join(' · '));
    MonitorMapas.credito('cardFisico', { fontes: ['NOAA/CPC', 'INPE', 'ANA', 'CPTEC'], data: sinais.gerado_em || null });
  }

  function textos(idx) {
    const lista = el('blogLista'); if (!lista) return;
    const posts = (idx && Array.isArray(idx.posts)) ? idx.posts : [];
    if (!posts.length) { lista.innerHTML = '<li class="blog-vazio">Nenhum texto publicado até a data de corte.</li>'; return; }
    lista.innerHTML = posts.map(p => '<li class="blog-item"><span class="selo">' + esc(p.categoria_rotulo) + ' · ' + esc(p.data_br) + ' · ' + esc(p.autor) + '</span>' +
      '<a class="blog-titulo" href="' + esc(p.url) + '">' + esc(p.titulo) + '</a>' +
      '<p class="blog-resumo">' + esc(p.resumo) + '</p></li>').join('');
  }

  async function iniciar() {
    const [meta, indice, estados, municipios, ms, resp, sinais, idx] = await Promise.all(
      ['data/meta.json', 'data/indice.json', 'data/estados.json', 'data/municipios.json', 'data/monitor_saude.json', 'data/resposta/por_uf.json', 'data/sinais_risco.json', 'data/blog/posts.json'].map(carregar));
    legal(indice, estados, municipios, meta); saude(ms); defesa(resp, sinais); fisico(sinais); textos(idx);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciar); else iniciar();
})();
