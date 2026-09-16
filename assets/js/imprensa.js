const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
// ===== imprensa.html · bloco 1 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
(function(){
  fetch('data/indice.json').then(r=>r.json()).then(idx=>{ const ufs=Object.keys(idx).filter(k=>k.length===2); const tot=ufs.map(u=>idx[u].total); const media=Math.round(tot.reduce((a,b)=>a+b,0)/27*10)/10; const txt=media.toLocaleString('pt-BR',{minimumFractionDigits:1});
    document.getElementById('relMedia').textContent=txt; document.getElementById('relMedia2').textContent=txt;
    const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = String(v); };
    // 16/09/2026 (pedido da editoria): o site não ranqueia nem compara estados entre si — o release não
    // nomeia mais os dois primeiros e os dois últimos por nota (removido: ord/relTopo/relBase).
    const fx = v => v < 25 ? 'estágio inicial' : v < 50 ? 'em construção' : v < 70 ? 'consolidado' : 'avançado';
    const rf = document.getElementById('relFaixa'); if (rf) rf.textContent = fx(+String(txt).replace(',', '.'));
    fetch('data/resposta/por_uf.json').then(r => r.ok ? r.json() : null).then(R => { if (!R) return; const N = R.nacional;
      ['relDecretados', 'relDecretados2', 'achDecretados'].forEach(i => set(i, N.n_municipios.toLocaleString('pt-BR'))); set('relReconhecidos', (N.reconhecidos ?? '—').toLocaleString('pt-BR')); set('relPrimeiro', N.primeiro_decreto || '—'); set('achPop', (100 * N.fracao_populacao).toFixed(1).replace('.', ',') + '%'); document.getElementById('relPop').textContent = (100 * N.fracao_populacao).toFixed(1).replace('.', ',') + '%'; }).catch(() => {});
    // 15/09/2026: mais números do release lidos do dado — planos municipais (percentual_uf.n_plano), estados com plano do ciclo (estados.json), MARÉ Saúde (monitor_saude.resumo), reconhecidos (resposta)
    fetch('data/percentual_uf.json').then(r => r.ok ? r.json() : null).then(P => { if (!P) return; const n = Object.values(P).reduce((a, i) => a + (i.n_plano || 0), 0).toLocaleString('pt-BR'); ['relPlanosMun', 'relPlanosMun2', 'achPlanosMun'].forEach(i => set(i, n)); }).catch(() => {});
    fetch('data/verificacao_resumo.json').then(r => r.ok ? r.json() : null).then(V => { const vd = V && V.varredura_diarios; if (vd && vd.consultados) set('relDiarios', Number(vd.consultados).toLocaleString('pt-BR')); }).catch(() => {});
    fetch('data/estados.json').then(r => r.ok ? r.json() : null).then(E => { if (!E) return; const c = k => (E.ufs || []).filter(u => k.includes(u.status)); const ufsDe = k => c(k).map(u => u.uf).sort().join(', ');
      ['relNovo', 'relNovo2', 'achNovo'].forEach(i => set(i, c(['NOVO']).length)); set('relNovoUFs', ufsDe(['NOVO'])); set('relTodoAno', c(['VIG']).length); set('achTodoAno', c(['VIG']).length); set('relElab', c(['ELAB']).length); set('relLacUFs', ufsDe(['LAC']) || 'nenhum'); }).catch(() => {});
    fetch('data/financiamento/serie_nacional.json').then(r => r.ok ? r.json() : null).then(S => { if (!S || !S.semanas) return; const antes = S.semanas.filter(w => w.semana < S.defeso.inicio), dur = S.semanas.filter(w => w.semana >= S.defeso.inicio && w.semana <= S.defeso.fim && (w.r5 || 0) > 0);
      const bi = (antes.reduce((a, w) => a + (w.r5 || 0), 0) / 1e9).toFixed(1).replace('.', ','), mi = (dur.reduce((a, w) => a + (w.r5 || 0), 0) / 1e6).toFixed(0);
      set('relAntesDefeso', bi); set('achAntes', bi); set('relDuranteDefeso', mi); set('achDurante', mi); const carga = (S.carga_da_fonte || S.corte || '').slice(0, 10); set('relCarga', carga); set('achCarga', carga); }).catch(() => {});
    fetch('data/financiamento/mps_2026.json').then(r => r.ok ? r.json() : null).then(M => { if (!M) return; (M.mps || []).forEach(m => { const v = ((m.execucao || {}).pago || 0) / 1e6; set(m.id === 'mp1367' ? 'relMP1367' : 'relMP1384', v.toFixed(1).replace('.', ',')); }); }).catch(() => {});
    fetch('data/saude_uf.json').then(r => r.ok ? r.json() : null).then(SU => { if (!SU) return; set('achSaudeNovo', Object.values(SU.uf || {}).filter(u => u.status === 'NOVO').length); }).catch(() => {});
    fetch('data/monitor_saude.json').then(r => r.ok ? r.json() : null).then(M => { const a = document.getElementById('relSaude'), b = document.getElementById('relSaudeN'); if (a && M && M.resumo && M.resumo.media_das_verificadas != null) { a.textContent = M.resumo.media_das_verificadas.toFixed(1).replace('.', ','); set('achSaude', a.textContent); } if (b && M && M.resumo) b.textContent = String(M.resumo.verificadas); }).catch(() => {});
    const av=ufs.filter(u=>idx[u].total>=70).length, ini=ufs.filter(u=>idx[u].total<25).length;
    (document.getElementById('relEstados')||{}).textContent=av+' estado(s) estão na faixa avançada (70 ou mais) e '+ini+' na faixa inicial (abaixo de 25).'; }).catch(()=>{});
  fetch('feeds/brasil.xml').then(r => r.ok ? r.text() : '').then(x => { const ul = document.getElementById('listaMudou'); if (!ul || !x) return;
    const doc = new DOMParser().parseFromString(x, 'application/xml'); const lim = new Date(Date.now() - 7 * 86400000);
    const itens = [...doc.getElementsByTagName('entry')].map(e => ({t: (e.getElementsByTagName('title')[0] || {}).textContent || '', d: (e.getElementsByTagName('updated')[0] || {}).textContent || '', l: (e.getElementsByTagName('link')[0] || {}).getAttribute ? e.getElementsByTagName('link')[0].getAttribute('href') : ''}))
      .filter(i => new Date(i.d) >= lim).slice(0, 12);
    ul.innerHTML = itens.length ? itens.map(i => '<li>' + i.d.slice(0, 10).split('-').reverse().join('/') + ' · ' + (i.l ? '<a href="' + i.l + '">' : '') + esc(i.t) + (i.l ? '</a>' : '') + '</li>').join('') : '<li>Nenhuma mudança verificada nos últimos sete dias.</li>'; }).catch(() => {});
  fetch('data/meta.json').then(r=>r.json()).then(m=>{ (document.getElementById('relCorte')||{}).textContent=m.corte||'—'; document.getElementById('relData').textContent=(m.atualizado_em||m.corte||''); }).catch(()=>{});
})();

window.addEventListener('load', function(){ if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} } });

// 14/09/2026 (pedido de Patricia, 13/09): "O que a lei deixa aberto" vira nota para a imprensa — mesma fonte e o
// mesmo desenho de linha da página do calendário (data/calendario/dispositivos.json, campo nao_suspenso).
(function(){
  const ul = document.getElementById('listaNaoSuspenso'); if (!ul) return;
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  fetch('data/calendario/dispositivos.json').then(r => r.ok ? r.json() : null).then(D => {
    if (!D || !Array.isArray(D.nao_suspenso)) { ul.innerHTML = '<li class="u-muted">Lista não carregada — ver o calendário eleitoral.</li>'; return; }
    ul.innerHTML = D.nao_suspenso.map(x => '<li><strong>' + esc(x.item) + '</strong> — ' + esc(x.base) + ' <span class="u-muted">(' + esc(x.status) + ')</span></li>').join('');
  }).catch(() => { ul.innerHTML = '<li class="u-muted">Lista não carregada — ver o calendário eleitoral.</li>'; });
})();
