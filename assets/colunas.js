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
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', aplicar); else aplicar();
  window.addEventListener('load', aplicar);
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
