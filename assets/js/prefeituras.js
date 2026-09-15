// ===== prefeituras.html · bloco 1 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
(function(){
  const p = new URLSearchParams(location.search);
  const set = (id, v) => { const el = document.getElementById(id); if (el && v) el.value = v; };
  set('cUF', (p.get('uf') || '').toUpperCase());
  // Lista de municípios por UF (malha IBGE): carga preguiçosa, com degradação graciosa
  let __refMun = null;
  async function preencherMunicipios(){
    const uf = document.getElementById('cUF').value;
    const dl = document.getElementById('listaMunEnvio');
    if (!uf){ dl.innerHTML = ''; return; }
    try {
      if (!__refMun){
        __refMun = window.__MUN_REF__ || await fetch('data/municipios_ibge_referencia.json').then(r => r.json());
      }
      const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
      dl.innerHTML = __refMun.filter(m => m.uf === uf)
        .map(m => esc(m.nome)).sort((a, b) => a.localeCompare(b))
        .map(n => `<option value="${n}">`).join('');
    } catch (e) { dl.innerHTML = ''; /* offline/prévia sem dados: campo segue como texto livre */ }
  }
  document.getElementById('cUF').addEventListener('change', preencherMunicipios);
  preencherMunicipios();
  set('cMunicipio', p.get('mun') || '');
  set('cTipo', p.get('tipo') || '');
  // Produção = domínio final OU o subdomínio temporário *.netlify.app (útil para testar
  //   nas Partes 2-3 do guia de publicação, antes do DNS do domínio próprio propagar).
  // Qualquer outro host (prévia local, file://, artefato de visualização) mantém o
  //   formulário desativado — Netlify Forms só funciona quando hospedado de fato.
  const ehProducao = /\.netlify\.app$/.test(location.hostname) || /(^|\.)monitorelnino\.com\.br$/.test(location.hostname);
  if (!ehProducao){
    const off = document.getElementById('contribOffline'); if (off) off.textContent = 'Nesta prévia local o envio fica desativado; na versão publicada, funciona.';
    document.getElementById('formContrib').addEventListener('submit', (e) => { e.preventDefault();
      alert('Prévia local: o envio do formulário funciona apenas na versão publicada do site.'); });
  }
})();

// ===== prefeituras.html · bloco 2 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
window.addEventListener('load', function(){ if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} } });

// 14/09/2026 (auditoria editorial §1.8): "O que ainda é possível no período eleitoral" vem do mesmo dado do calendário
// (data/calendario/dispositivos.json, campo nao_suspenso) — nenhuma linha digitada aqui.
(function(){
  const ul = document.getElementById('listaNaoSuspenso'); if (!ul) return;
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  fetch('data/calendario/dispositivos.json').then(r => r.ok ? r.json() : null).then(D => {
    if (!D || !Array.isArray(D.nao_suspenso)) { ul.innerHTML = '<li class="u-muted">Lista não carregada — ver o calendário eleitoral.</li>'; return; }
    ul.innerHTML = D.nao_suspenso.map(x => '<li><strong>' + esc(x.item) + '</strong> — ' + esc(x.base) + '</li>').join('');
  }).catch(() => { ul.innerHTML = '<li class="u-muted">Lista não carregada — ver o calendário eleitoral.</li>'; });
})();

// 15/09/2026 (pedido da editoria): "Descubra se seu município é prioritário" — busca na aproximação
// populacional do Cadastro Nacional (data/municipios_prioritarios.json, gerar_prioritarios.py), a
// mesma fonte do mapa em defesa-civil.html. Nunca recalculada aqui.
(function(){
  const selUF = document.getElementById('selUFPrior'), input = document.getElementById('inputMunPrior');
  const dl = document.getElementById('listaMunPrior'), out = document.getElementById('resultadoPrior');
  if (!selUF) return;
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const NOMES_UF = {AC:'Acre',AL:'Alagoas',AM:'Amazonas',AP:'Amapá',BA:'Bahia',CE:'Ceará',DF:'Distrito Federal',ES:'Espírito Santo',GO:'Goiás',MA:'Maranhão',MG:'Minas Gerais',MS:'Mato Grosso do Sul',MT:'Mato Grosso',PA:'Pará',PB:'Paraíba',PE:'Pernambuco',PI:'Piauí',PR:'Paraná',RJ:'Rio de Janeiro',RN:'Rio Grande do Norte',RO:'Rondônia',RR:'Roraima',RS:'Rio Grande do Sul',SC:'Santa Catarina',SE:'Sergipe',SP:'São Paulo',TO:'Tocantins'};
  fetch('data/municipios_prioritarios.json').then(r => r.ok ? r.json() : null).then(PRIOR => {
    if (!PRIOR) { out.hidden = false; out.textContent = 'Lista não carregada.'; return; }
    const porUF = {}; PRIOR.municipios.forEach(m => (porUF[m.uf] = porUF[m.uf] || []).push(m));
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
      if (!m) { out.innerHTML = '<strong>' + esc(nome) + ' (' + uf + ')</strong> não está na aproximação de municípios prioritários desta edição — o que não significa risco baixo: é a aproximação populacional, não a lista oficial completa.'; return; }
      out.innerHTML = '<strong>' + esc(m.nome) + ' (' + uf + ')</strong> está na aproximação de municípios prioritários. '
        + (m.publicado ? 'Instrumento (plano, decreto ou estrutura) já localizado até o corte — ' : 'Nenhum instrumento localizado até o corte — ')
        + '<a href="index.html#' + esc(uf) + '">ver o estado na página inicial →</a>';
    };
    input.addEventListener('change', buscar); input.addEventListener('input', () => { if ([...dl.options].some(o => o.value === input.value)) buscar(); });
    if (window.MonitorMapas) MonitorMapas.credito('fontePrior', {fontes: ['Cadastro Nacional de Municípios com Áreas Suscetíveis a Desastres (MIDR/SEDEC) — aproximação por população', 'MARÉ'], data: null});
    else document.getElementById('fontePrior').innerHTML = '<p class="note u-mb-0">Fonte: Cadastro Nacional de Municípios com Áreas Suscetíveis a Desastres (MIDR/SEDEC) — aproximação por população · MARÉ.</p>';
  }).catch(() => { out.hidden = false; out.textContent = 'Lista não carregada.'; });
})();
