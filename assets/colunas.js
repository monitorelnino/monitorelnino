/* Colunas de leitura (07/09/2026, pedido da editoria): blocos de texto longos passam a duas colunas em telas largas,
 * para reduzir a altura ocupada. Regra: parágrafos de contexto (.hint, .note, .hero-scope, .prazo-espera, .bloco-citacao p)
 * e listas (.fontes-list) com mais de 320 caracteres recebem a classe .cols; o CSS faz o resto (só ≥ 1021 px).
 * 16/09/2026 (pedido da editoria): fichas "Como ler" (dialog e [data-voz="ficha"]) ficam de fora — quebrar uma frase
 * ao meio entre duas colunas atrapalha a leitura; nessas, o texto foi encurtado por parágrafo em vez de colunado. */
(function () {
  function aplicar() {
    var alvos = document.querySelectorAll('p.hint, p.note, .hero-scope, .prazo-espera, .bloco-citacao p, ul.fontes-list, .prosa');
    for (var i = 0; i < alvos.length; i++) {
      var el = alvos[i];
      if (el.closest && el.closest('.map-box, .chart-box, .tile, .gauge-zone, .contador-zone, nav, footer, dialog, [data-voz="ficha"]')) continue;
      var n = (el.textContent || '').replace(/\s+/g, ' ').trim().length;
      if (n >= 320) el.classList.add('cols');
    }
  }
  /* 03/10/2026 — A NUMERAÇÃO SAIU, de seção e de figura.
     Ela nasceu de uma auditoria de 07/09/2026: toda figura recebia "Figura N" e, nas páginas de
     dados, toda seção recebia "N · ". As decisões de 01 e 02/10/2026 a revogaram em dois passos —
     os handovers passaram a exigir "seções sem caixa e sem numeração", e os contratos de layout
     proibiram a palavra "FIGURA" no texto que o leitor lê. Até aqui as duas coisas conviviam porque
     ninguém verificava: a folha de estilo ESCONDIA o rótulo nos cartões e este arquivo continuava
     ESCREVENDO-O fora deles. O portão de conformidade, no primeiro passe (03/10/2026), leu
     "FIGURA 1" e "1 · Situação atual" no Monitor de riscos e no Blog, onde as figuras não são
     cartão. Esconder o que não devia existir é pior do que escrever: o texto chega a quem usa
     leitor de tela e some para quem confere a página. Então ele deixa de ser escrito. */

  function tudo() { aplicar(); }
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
