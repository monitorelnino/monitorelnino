/* Grade de estados: UM componente, parametrizado por índice.
 *
 * Item 7 do handover de 02/10/2026. A inicial mostrava os 27 estados num MAPA DE CARTÕES — cada
 * estado na sua posição geográfica, com sigla, nome, número e duas barras —, e o MARÉ Saúde mostrava
 * os mesmos 27 em colunas por região, com outro desenho. Dois componentes para a mesma coisa
 * divergem na primeira troca: um ganha a correção, o outro fica.
 *
 * Agora é um só. A posição geográfica, o desenho do cartão, o teclado e a ficha vivem aqui; a
 * página passa o índice que quer ver (`MARÉ Legal` ou `MARÉ Saúde`), a barra de baixo (resposta) e
 * o que fazer no clique. O estilo é o de `.regions`/`.tile` em `assets/base.css`, por CLASSE e não
 * por id — é o que faz o componente funcionar em qualquer página sem copiar regra (item 3.1).
 *
 * Estado não verificado ocupa o mesmo lugar, sem número, com "não verificado" e barras vazias.
 * Nunca zero: zero é um valor medido, e "não verificado" é a ausência de medição.
 */
(function (global) {
  'use strict';

  /* A posição de cada estado no mapa de cartões: [linha, coluna]. RR e AP no alto, AC à esquerda,
   * RS embaixo. Esta tabela era privada de index.js e passou a ser do componente. */
  var GRADE_BR = {
    RR: [1, 2], AP: [1, 3],
    AM: [2, 2], PA: [2, 3], MA: [2, 4], CE: [2, 5],
    AC: [3, 1], RO: [3, 2], TO: [3, 3], PI: [3, 4], PB: [3, 5], RN: [3, 6],
    MT: [4, 2], GO: [4, 3], BA: [4, 4], PE: [4, 5], AL: [4, 6],
    MS: [5, 2], DF: [5, 3], MG: [5, 4], SE: [5, 5],
    SP: [6, 3], RJ: [6, 4], ES: [6, 5],
    PR: [7, 3], SC: [7, 4],
    RS: [8, 3]
  };

  function esc(v) {
    return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function numero(v) {
    return v == null ? null : String(v).replace('.', ',');
  }

  /* Uma barra do cartão. `alvo` é 0–100; sem valor, a barra fica vazia e cinza — e a ausência é
   * dita no texto, não na cor. */
  function barra(alvo, classe) {
    if (alvo == null) return '<div class="tile-bar tile-bar--vazia"></div>';
    return '<div class="tile-bar ' + (classe || '') + '"><div class="tile-fill" data-alvo="' + alvo +
      '" style="--galvo:' + Math.max(alvo, 0.1) + '; width:' + alvo + '%"></div></div>';
  }

  /* Monta a grade.
   *
   * opcoes = {
   *   alvo:        elemento ou id onde a grade entra
   *   ufs:         [{uf, nome, status}]  — a lista canônica, com nome por extenso
   *   indice:      função(uf) -> número 0–100 ou null   (barra de cima)
   *   resposta:    função(uf) -> número 0–100 ou null   (barra de baixo)
   *   rotulo:      texto do índice, para o title e o aria-label ("MARÉ Saúde")
   *   aoClicar:    função(uf) — a ficha da página
   *   extra:       função(uf) -> HTML opcional dentro do cartão
   * }
   */
  function montar(opcoes) {
    var o = opcoes || {};
    var alvo = typeof o.alvo === 'string' ? document.getElementById(o.alvo) : o.alvo;
    if (!alvo) return 0;
    var ufs = (o.ufs || []).filter(function (x) { return x && x.uf; });
    if (!ufs.length) return 0;
    var indice = o.indice || function () { return null; };
    var resposta = o.resposta || function () { return null; };
    var rotulo = o.rotulo || 'índice';

    alvo.innerHTML = '';
    ufs.forEach(function (item) {
      var uf = item.uf;
      var v = indice(uf);
      var r = resposta(uf);
      var t = document.createElement('div');
      t.className = 'tile' + (item.status ? ' st-' + item.status : '') + (v == null ? ' tile--sem-dado' : '');
      t.dataset.uf = uf;
      t.title = uf + ' · ' + rotulo + ' ' + (v == null ? 'não verificado' : numero(v) + ' / 100');
      var pos = GRADE_BR[uf];
      if (pos) { t.style.gridRow = pos[0]; t.style.gridColumn = pos[1]; }
      t.innerHTML = '<span class="tile-uf">' + esc(uf) + '</span>' +
        '<span class="tile-nome">' + esc(item.nome || '') + '</span>' +
        (v == null
          ? '<span class="tile-score tile-score--vazio">não verificado</span>'
          : '<span class="tile-score" data-contar="' + v + '">0,0</span>') +
        barra(v, 'tile-bar--indice') +
        barra(r, 'tile-bar--resposta') +
        (o.extra ? o.extra(uf) : '');
      /* Alcançável por teclado, como qualquer botão: o cartão é um alvo de clique, e sem papel e
       * índice de tabulação quem navega por teclado não alcança nenhum estado. */
      t.setAttribute('role', 'button');
      t.tabIndex = 0;
      t.setAttribute('aria-label', 'Detalhe de ' + t.title);
      if (o.aoClicar) {
        t.addEventListener('click', function () { o.aoClicar(uf); });
        t.addEventListener('keydown', function (e) {
          if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); t.click(); }
        });
      }
      alvo.appendChild(t);
    });
    return ufs.length;
  }

  /* A legenda das duas barras, igual em toda página que usa o componente. */
  function legendaDasBarras(alvoLegenda, rotuloIndice) {
    var el = typeof alvoLegenda === 'string' ? document.getElementById(alvoLegenda) : alvoLegenda;
    if (!el) return;
    el.innerHTML = '<span>Barra de cima: ' + esc(rotuloIndice || 'índice') + ' 0–100</span>' +
      '<span>Barra de baixo: resposta 0–100</span>';
  }

  /* `legendaDasBarras` e a legenda das DUAS BARRAS do cartao, e nao legenda de mapa: o motor
 * unico de legenda de figura e MonitorMapas.legenda, em assets/mapas.js, e o portao de
 * estrutura confere que ninguem o redefine. */
global.GradeEstados = { montar: montar, legendaDasBarras: legendaDasBarras, GRADE_BR: GRADE_BR };
})(window);
