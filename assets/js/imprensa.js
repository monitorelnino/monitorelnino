const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
// ===== imprensa.html · bloco 1 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
(function(){
  fetch('data/indice.json').then(r=>r.json()).then(idx=>{ const ufs=Object.keys(idx).filter(k=>k.length===2); const tot=ufs.map(u=>idx[u].total); const media=Math.round(tot.reduce((a,b)=>a+b,0)/27*10)/10; const txt=media.toLocaleString('pt-BR',{minimumFractionDigits:1});
    document.getElementById('relMedia').textContent=txt; document.getElementById('relMedia2').textContent=txt;
    const fx = v => v < 25 ? 'estágio inicial' : v < 50 ? 'em construção' : v < 70 ? 'consolidado' : 'avançado';
    const rf = document.getElementById('relFaixa'); if (rf) rf.textContent = fx(+String(txt).replace(',', '.'));
    fetch('data/resposta/por_uf.json').then(r => r.ok ? r.json() : null).then(R => { if (!R) return; const N = R.nacional;
      document.getElementById('relDecretados').textContent = N.n_municipios.toLocaleString('pt-BR'); document.getElementById('relPop').textContent = (100 * N.fracao_populacao).toFixed(1).replace('.', ',') + '%'; }).catch(() => {});
    const av=ufs.filter(u=>idx[u].total>=70).length, ini=ufs.filter(u=>idx[u].total<25).length;
    document.getElementById('relEstados').textContent=av+' estado(s) estão na faixa avançada (70 ou mais) e '+ini+' na faixa inicial (abaixo de 25).'; }).catch(()=>{});
  fetch('feeds/brasil.xml').then(r => r.ok ? r.text() : '').then(x => { const ul = document.getElementById('listaMudou'); if (!ul || !x) return;
    const doc = new DOMParser().parseFromString(x, 'application/xml'); const lim = new Date(Date.now() - 7 * 86400000);
    const itens = [...doc.getElementsByTagName('entry')].map(e => ({t: (e.getElementsByTagName('title')[0] || {}).textContent || '', d: (e.getElementsByTagName('updated')[0] || {}).textContent || '', l: (e.getElementsByTagName('link')[0] || {}).getAttribute ? e.getElementsByTagName('link')[0].getAttribute('href') : ''}))
      .filter(i => new Date(i.d) >= lim).slice(0, 12);
    ul.innerHTML = itens.length ? itens.map(i => '<li>' + i.d.slice(0, 10).split('-').reverse().join('/') + ' · ' + (i.l ? '<a href="' + i.l + '">' : '') + esc(i.t) + (i.l ? '</a>' : '') + '</li>').join('') : '<li>Nenhuma mudança verificada nos últimos sete dias.</li>'; }).catch(() => {});
  fetch('data/meta.json').then(r=>r.json()).then(m=>{ document.getElementById('relCorte').textContent=m.corte||'—'; document.getElementById('relData').textContent=(m.atualizado_em||m.corte||''); }).catch(()=>{});
})();

window.addEventListener('load', function(){ if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} } });
