// ===== envie-dados.html · bloco 1 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
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
    document.getElementById('contribOffline').textContent = 'Nesta prévia local o envio fica desativado; na versão publicada, funciona.';
    document.getElementById('formContrib').addEventListener('submit', (e) => { e.preventDefault();
      alert('Prévia local: o envio do formulário funciona apenas na versão publicada do site.'); });
  }
})();

// ===== envie-dados.html · bloco 2 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
window.addEventListener('load', function(){ if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} } });
