const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
// ===== imprensa.html · bloco 1 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
(function(){
  fetch('data/indice.json').then(r=>r.json()).then(idx=>{ const ufs=Object.keys(idx).filter(k=>k.length===2); const tot=ufs.map(u=>idx[u].total); const media=Math.round(tot.reduce((a,b)=>a+b,0)/27*10)/10; const txt=media.toLocaleString('pt-BR',{minimumFractionDigits:1});
    document.getElementById('relMedia').textContent=txt; document.getElementById('relMedia2').textContent=txt;
    const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = String(v); };
    // 16/09/2026 (pedido da editoria): o site não ranqueia nem compara estados entre si — o release não
    // nomeia mais os dois primeiros e os dois últimos por nota (removido: ord/relTopo/relBase).
    fetch('data/resposta/por_uf.json').then(r => r.ok ? r.json() : null).then(R => { if (!R) return; const N = R.nacional;
      ['relDecretados', 'relDecretados2'].forEach(i => set(i, N.n_municipios.toLocaleString('pt-BR'))); set('relReconhecidos', (N.reconhecidos ?? '—').toLocaleString('pt-BR')); set('relPrimeiroDecreto', N.primeiro_decreto || '—');
      set('relPopMilhoes', ((N.pop_sob_decreto || 0) / 1e6).toFixed(1).replace('.', ','));
      // 16/09/2026 (handover): relQ1/relQ3 são CONTAGENS de estados num cruzamento antecipação × resposta — nunca
      // nomeiam qual estado (a editoria vetou nomear/ordenar estados por posição em 16/09, §73); computado ao vivo
      // de indice.json + resposta/por_uf.json, sem depender de um arquivo dedicado (o antigo resposta/quadrantes.json
      // foi removido no mesmo pedido).
      fetch('data/indice.json').then(rr => rr.ok ? rr.json() : null).then(IDX => { if (!IDX) return;
        const ufsR = Object.keys(R.uf); let q1 = 0, q3 = 0;
        ufsR.forEach(uf => { const idxUf = (IDX[uf] || {}).total; const fr = R.uf[uf].fracao_municipios || 0;
          if (idxUf == null || fr <= 0.05) return; if (idxUf >= 50) q1++; else q3++; });
        set('relQ1', q1); set('relQ3', q3);
      }).catch(() => {});
    }).catch(() => {});
    fetch('data/calendario/fontes_suspensas.json').then(r => r.ok ? r.json() : null).then(F => { if (!F) return;
      set('relSuspensas', Object.values(F.fontes || {}).filter(f => f.suspensa).length);
    }).catch(() => {});
    // 15/09/2026: mais números do release lidos do dado — planos municipais (percentual_uf.n_plano), estados com plano do ciclo (estados.json)
    fetch('data/percentual_uf.json').then(r => r.ok ? r.json() : null).then(P => { if (!P) return; const n = Object.values(P).reduce((a, i) => a + (i.n_plano || 0), 0).toLocaleString('pt-BR'); ['relPlanosMun', 'relPlanosMun2'].forEach(i => set(i, n)); }).catch(() => {});
    fetch('data/estados.json').then(r => r.ok ? r.json() : null).then(E => { if (!E) return; const c = k => (E.ufs || []).filter(u => k.includes(u.status)); const ufsDe = k => c(k).map(u => u.uf).sort().join(', ');
      ['relNovo', 'relNovo2'].forEach(i => set(i, c(['NOVO']).length)); set('relNovoUFs', ufsDe(['NOVO'])); set('relTodoAno', c(['VIG']).length); set('relElab', c(['ELAB']).length); set('relLacUFs', ufsDe(['LAC']) || 'nenhum'); }).catch(() => {});
  }).catch(()=>{});
  // 16/09/2026 (pedido da editoria): "O que mudou" (feed + relDataAnterior) saiu da página — bloco removido.
  fetch('data/meta.json').then(r=>r.json()).then(m=>{ (document.getElementById('relCorte')||{}).textContent=m.corte||'—'; document.getElementById('relData').textContent=(m.atualizado_em||m.corte||'');
    (document.getElementById('relCorte2')||{}).textContent=m.corte||'—'; (document.getElementById('relData2')||{}).textContent=(m.atualizado_em||m.corte||'');
  }).catch(()=>{});
})();

window.addEventListener('load', function(){ if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} } });

// 14/09/2026 (pedido de Patricia, 13/09): "O que a lei deixa aberto" vira nota para a imprensa — mesma fonte e o
// mesmo desenho de linha da página do calendário (data/calendario/dispositivos.json, campo nao_suspenso).
(function(){
  const ul = document.getElementById('listaNaoSuspenso'); const ul2 = document.getElementById('listaSuspenso'); if (!ul && !ul2) return;
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  fetch('data/calendario/dispositivos.json').then(r => r.ok ? r.json() : null).then(D => {
    if (!D || !Array.isArray(D.nao_suspenso)) { if (ul) ul.innerHTML = '<li class="u-muted">Lista não carregada — ver o calendário eleitoral.</li>'; if (ul2) ul2.innerHTML = '<li class="u-muted">Lista não carregada.</li>'; return; }
    if (ul) ul.innerHTML = D.nao_suspenso.map(x => '<li><strong>' + esc(x.item) + '</strong> — ' + esc(x.base) + ' <span class="u-muted">(' + esc(x.status) + ')</span></li>').join('');
    if (ul2 && Array.isArray(D.dispositivos)) ul2.innerHTML = D.dispositivos.filter(x => x.bloqueia && x.bloqueia !== '—').map(x => '<li><strong>' + esc(x.bloqueia.split('.')[0].split(' — ')[0].split(', nos')[0]) + '</strong> <span class="u-muted">(' + esc(x.dispositivo) + ')</span></li>').join('');
  }).catch(() => { if (ul) ul.innerHTML = '<li class="u-muted">Lista não carregada — ver o calendário eleitoral.</li>'; if (ul2) ul2.innerHTML = '<li class="u-muted">Lista não carregada.</li>'; });
})();

// 16/09/2026 (handover §1.8): calendário compacto para a imprensa — reusa data/marcos_ciclo.json (mesma
// fonte do "Calendário" da inicial), filtrado para os marcos ainda não passados.
(function(){
  const ul = document.getElementById('listaCalendarioImprensa'); if (!ul) return;
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  fetch('data/marcos_ciclo.json').then(r => r.ok ? r.json() : null).then(M => {
    if (!M || !Array.isArray(M.marcos)) { ul.innerHTML = '<li class="u-muted">Calendário não carregado.</li>'; return; }
    const hoje = new Date(); hoje.setHours(0, 0, 0, 0);
    const dBR = s => { const [d, m, a] = s.split('/').map(Number); return new Date(a, m - 1, d); };
    const vindos = M.marcos.filter(m => dBR(m.ate || m.data) >= hoje);
    ul.innerHTML = vindos.length ? vindos.map(m => '<li><strong>' + esc(m.data) + (m.ate ? '–' + esc(m.ate) : '') + '</strong> — ' + esc(m.titulo) + ' <span class="u-muted">(' + esc(m.fonte) + ')</span></li>').join('')
      : '<li class="u-muted">Nenhum marco futuro registrado.</li>';
  }).catch(() => { ul.innerHTML = '<li class="u-muted">Calendário não carregado.</li>'; });
})();
