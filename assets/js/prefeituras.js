// 15/09/2026: o formulário "Indique um documento publicado" migrou para pesquisadores.html (e o JS para pesquisadores.js) — a página passou a ser "Para gestores".
// ===== prefeituras.html · bloco 2 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
window.addEventListener('load', function(){ if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} } });

// 14/09/2026 (auditoria editorial §1.8): "O que ainda é possível no período eleitoral" vem do mesmo dado do calendário
// (data/calendario/dispositivos.json, campo nao_suspenso) — nenhuma linha digitada aqui.
(function(){
  const ul = document.getElementById('listaNaoSuspenso'); if (!ul) return;
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  fetch('data/calendario/dispositivos.json').then(r => r.ok ? r.json() : null).then(D => {
    if (!D || !Array.isArray(D.nao_suspenso)) { ul.innerHTML = '<li class="u-muted">Lista não carregada; ver o calendário eleitoral.</li>'; return; }
    ul.innerHTML = D.nao_suspenso.map(x => '<li><strong>' + esc(x.item) + ':</strong> ' + esc(x.base) + '</li>').join('');
  }).catch(() => { ul.innerHTML = '<li class="u-muted">Lista não carregada; ver o calendário eleitoral.</li>'; });
})();

// 15/09/2026 (pedido da editoria): "Descubra se seu município é prioritário" — busca na aproximação
// populacional do Cadastro Nacional (data/municipios_prioritarios.json, gerar_prioritarios.py).
// 22/09/2026 (§155, decisão editorial): virou o CARD do município — todos os 5.571 consultáveis
// (referência IBGE), tag de prioritário, situação no MARÉ, "publicação na imprensa encontrada" com
// link (pista: NÃO pontua) e como pedir o documento ao gestor. Dado: data/municipios_card.json
// (gerar_card_municipios.py), carregado só na primeira consulta. Nada é calculado aqui.
(function(){
  const selUF = document.getElementById('selUFPrior'), input = document.getElementById('inputMunPrior');
  const dl = document.getElementById('listaMunPrior'), out = document.getElementById('resultadoPrior');
  if (!selUF) return;
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const NOMES_UF = {AC:'Acre',AL:'Alagoas',AM:'Amazonas',AP:'Amapá',BA:'Bahia',CE:'Ceará',DF:'Distrito Federal',ES:'Espírito Santo',GO:'Goiás',MA:'Maranhão',MG:'Minas Gerais',MS:'Mato Grosso do Sul',MT:'Mato Grosso',PA:'Pará',PB:'Paraíba',PE:'Pernambuco',PI:'Piauí',PR:'Paraná',RJ:'Rio de Janeiro',RN:'Rio Grande do Norte',RO:'Rondônia',RR:'Roraima',RS:'Rio Grande do Sul',SC:'Santa Catarina',SE:'Sergipe',SP:'São Paulo',TO:'Tocantins'};
  const CAT = {plano:'plano de contingência localizado', plano_antigo:'plano de edição anterior localizado', plano_elaboracao:'plano em elaboração (ato oficial localizado)',
               coberto_estadual:'coberto pelo plano estadual', decreto:'decreto de emergência localizado (não conta como preparação)', nao_verificado:'ainda não verificado',
               nao_el_nino:'ato localizado é de outro risco (não conta)', nao_localizado:'nenhum plano localizado até o corte'};
  let CARDS = null;
  const cards = () => CARDS || (CARDS = fetch('data/municipios_card.json').then(r => r.ok ? r.json() : {municipios:{}}).catch(() => ({municipios:{}})));
  fetch('data/municipios_ibge_referencia.json').then(r => r.ok ? r.json() : null).then(REF => {
    if (!REF) { out.hidden = false; out.textContent = 'Lista não carregada.'; return; }
    const porUF = {}; REF.forEach(m => (porUF[m.uf] = porUF[m.uf] || []).push(m));
    Object.keys(porUF).sort((a, b) => (NOMES_UF[a] || a).localeCompare(NOMES_UF[b] || b)).forEach(uf => {
      const o = document.createElement('option'); o.value = uf; o.textContent = (NOMES_UF[uf] || uf) + ' (' + uf + ')'; selUF.appendChild(o);
    });
    const atualizar = () => {
      const uf = selUF.value;
      if (!uf) { input.disabled = true; input.value = ''; dl.innerHTML = ''; out.hidden = true; return; }
      input.disabled = false;
      dl.innerHTML = porUF[uf].map(m => m.nome).sort((a, b) => a.localeCompare(b)).map(n => `<option value="${esc(n)}">`).join('');
    };
    selUF.addEventListener('change', atualizar); atualizar();
    const buscar = () => {
      const uf = selUF.value, nome = input.value.trim();
      if (!uf || !nome) { out.hidden = true; return; }
      const m = (porUF[uf] || []).find(x => x.nome.toLowerCase() === nome.toLowerCase());
      out.hidden = false;
      if (!m) { out.innerHTML = '<strong>' + esc(nome) + ' (' + uf + ')</strong> não consta na referência do IBGE — confira a grafia.'; return; }
      out.innerHTML = 'Consultando…';
      cards().then(D => {
        const c = (D.municipios || {})[String(m.codigo_ibge)] || {};
        const prior = c.prioritario ? '<span class="tag tag--prior">prioritário</span> ' : '';
        const cat = c.categoria || 'nao_localizado';
        let h = '<p class="u-mb-0"><strong>' + esc(m.nome) + ' (' + uf + ')</strong> ' + prior + '</p>';
        h += '<p class="u-mb-0"><strong>No MARÉ:</strong> ' + esc(CAT[cat] || cat)
          + (c.url ? ' — <a href="' + esc(c.url) + '" rel="noopener">' + esc((c.documento || 'documento').slice(0, 90)) + ' →</a>' : '')
          + (c.data ? ' <span class="u-muted">(' + esc(c.data) + ')</span>' : '') + '</p>';
        if (c.prioritario) h += '<p class="note u-mb-0">Está na aproximação de municípios prioritários do Cadastro Nacional (MIDR/SEDEC) — aproximação por população, não a lista oficial.</p>';
        if (c.imprensa && c.imprensa.length) {
          h += '<p class="u-mb-0"><strong>Publicação na imprensa encontrada</strong> <span class="u-muted">(pista — não pontua no MARÉ sem o documento oficial):</span></p><ul class="u-mb-0">'
            + c.imprensa.map(i => '<li><a href="' + esc(i.url) + '" rel="noopener">' + esc(i.titulo || i.veiculo) + '</a> <span class="u-muted">' + esc(i.veiculo) + (i.data ? ' · ' + esc(i.data) : '') + '</span></li>').join('') + '</ul>';
        }
        if (!['plano', 'plano_antigo', 'plano_elaboracao', 'coberto_estadual'].includes(cat)) {   // sem documento do tipo plano → convida a pedir
          h += '<p class="note u-mb-0"><strong>Peça o documento ao gestor público.</strong> Qualquer pessoa pode pedir, sem justificar (Lei de Acesso à Informação, Lei 12.527/2011): pelo e-SIC ou pela ouvidoria da prefeitura, ou pelo <a href="https://falabr.cgu.gov.br" rel="noopener">Fala.BR →</a> se o município não tiver canal próprio. Texto que funciona: <em>"Solicito cópia do Plano de Contingência de Proteção e Defesa Civil vigente do município, com o ato (decreto ou portaria) que o instituiu, número e data."</em> A resposta é devida em até 20 dias. Recebeu? <a href="mailto:contato@futuraevidencelab.com.br?subject=Plano%20de%20conting%C3%AAncia%20municipal">Envie para o MARÉ →</a></p>';
        }
        h += '<p class="note u-mb-0"><a href="index.html#' + esc(uf) + '">ver o estado na página inicial →</a></p>';
        out.innerHTML = h;
      });
    };
    input.addEventListener('change', buscar); input.addEventListener('input', () => { if ([...dl.options].some(o => o.value === input.value)) buscar(); });
    if (window.MonitorMapas) MonitorMapas.credito('fontePrior', {fontes: ['Cadastro Nacional de Municípios com Áreas Suscetíveis a Desastres (MIDR/SEDEC) — aproximação por população', 'MARÉ (registros verificados e pistas de imprensa)'], data: null});
    else document.getElementById('fontePrior').innerHTML = '<p class="note u-mb-0">Fonte: Cadastro Nacional (MIDR/SEDEC) — aproximação por população · MARÉ.</p>';
  }).catch(() => { out.hidden = false; out.textContent = 'Lista não carregada.'; });
})();
