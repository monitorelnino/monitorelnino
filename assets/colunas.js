/* 16/10/2026 (editoria, lote 2 do Monitor de riscos): a colunação automática dos textos longos
 * (desde 07/09/2026) saiu do site — texto corrido em coluna única em todas as páginas. Fica aqui só
 * a abertura do acordeão que contém o alvo de uma âncora. */
(function () {
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
