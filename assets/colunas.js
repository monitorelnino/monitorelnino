/* Colunas de leitura (07/09/2026, pedido da editoria): blocos de texto longos passam a duas colunas em telas largas,
 * para reduzir a altura ocupada. Regra: parágrafos de contexto (.hint, .note, .hero-scope, .prazo-espera, .bloco-citacao p)
 * e listas (.fontes-list) com mais de 320 caracteres recebem a classe .cols; o CSS faz o resto (só ≥ 1021 px). */
(function () {
  function aplicar() {
    var alvos = document.querySelectorAll('p.hint, p.note, .hero-scope, .prazo-espera, .bloco-citacao p, ul.fontes-list, .prosa');
    for (var i = 0; i < alvos.length; i++) {
      var el = alvos[i];
      if (el.closest && el.closest('.map-box, .chart-box, .tile, .gauge-zone, .contador-zone, nav, footer')) continue;
      var n = (el.textContent || '').replace(/\s+/g, ' ').trim().length;
      if (n >= 320) el.classList.add('cols');
    }
  }
  /* Numeração (auditoria de 07/09/2026): toda figura recebe "Figura N" e, nas páginas de dados (body.pagina-dados),
     toda seção recebe "N · " — sempre índice + 1, na ordem do documento; nenhum número é escrito à mão no HTML. */
  function numerar() {
    var figs = document.querySelectorAll('.figura');
    for (var i = 0; i < figs.length; i++) {
      var f = figs[i], pe = f.querySelector(':scope > .figura-pe');
      if (!pe) { pe = document.createElement('div'); pe.className = 'figura-pe'; f.appendChild(pe); }
      var n = pe.querySelector('.figura-num');
      if (!n) { n = document.createElement('span'); n.className = 'figura-num'; pe.appendChild(n); }
      n.textContent = 'Figura ' + (i + 1);
    }
    if (document.body.classList.contains('pagina-dados')) {
      var h2s = document.querySelectorAll('main > .panel > h2:first-child');
      for (var j = 0; j < h2s.length; j++) {
        if (h2s[j].querySelector('.secao-num')) continue;
        var s = document.createElement('span'); s.className = 'secao-num'; s.textContent = (j + 1) + ' · ';
        h2s[j].insertBefore(s, h2s[j].firstChild);
      }
    }
  }
  function tudo() { aplicar(); numerar(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', tudo); else tudo();
  window.addEventListener('load', tudo);
  // Abre o acordeão que contém o alvo de um link com âncora (ex.: pesquisadores.html#fontes-sinais)
  function abrirAncora() {
    if (!location.hash) return;
    var alvo = document.getElementById(decodeURIComponent(location.hash.slice(1)));
    if (!alvo) return;
    var d = alvo.closest && alvo.closest('details');
    if (d && !d.open) { d.open = true; setTimeout(function () { alvo.scrollIntoView(); }, 30); }
  }
  abrirAncora(); window.addEventListener('hashchange', abrirAncora);
})();
