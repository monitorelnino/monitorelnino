/* ===== blog.html · índice dos textos e os dois cartões da rotina =========================
 *
 * 04/10/2026 (handover da rotina semanal). O blog tem duas coisas:
 *
 *   1. no topo, os DOIS cartões de texto — o mais recente de "Legal e financiamento" e o mais
 *      recente de "Saúde": etiqueta, título, data, abertura de uma linha e "Ler →";
 *   2. a lista cronológica de todos os textos, do mais novo ao mais antigo, com filtro por
 *      etiqueta.
 *
 * Sem número e sem gráfico no índice: a rotina produz texto, e os números vivem nas páginas do
 * Monitor. O cartão de uma linha que ainda não tem texto NÃO aparece — cartão vazio afirma que
 * existe algo ali.
 */
(function () {
  'use strict';
  var LINHAS = ['Legal e financiamento', 'Saúde'];
  var esc = function (v) {
    return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  };

  fetch('data/blog/posts.json').then(function (r) { return r.ok ? r.json() : null; })
    .then(function (dados) {
      var lista = Array.isArray(dados) ? dados : (dados && dados.posts) || [];
      cartoes(lista);
      indice(lista);
    }).catch(function () {});

  /* Os dois cartões: o primeiro texto de cada linha, na ordem em que a rotina os produz. */
  function cartoes(lista) {
    var alvo = document.getElementById('destaquesTextos');
    var secao = document.getElementById('destaques');
    if (!alvo) return;
    var html = LINHAS.map(function (linha) {
      var p = lista.filter(function (x) { return (x.etiqueta || '') === linha; })[0];
      if (!p) return '';
      return '<article class="cartao-mapa">'
        + '<p class="spec">' + esc(linha) + ' · ' + esc(p.data_br || '') + '</p>'
        + '<h3 class="cartao-mapa-titulo"><a href="' + esc(p.url) + '">' + esc(p.titulo) + '</a></h3>'
        + '<p class="cartao-mapa-nota">' + esc(p.resumo || '') + '</p>'
        + '<p class="u-mb-0"><a href="' + esc(p.url) + '">Ler →</a></p>'
        + '</article>';
    }).filter(Boolean).join('');
    if (!html) { if (secao) secao.hidden = true; return; }
    alvo.innerHTML = html;
  }

  /* A lista, com filtro por etiqueta. O filtro é de leitura, não de dado: ele esconde linhas, não
     recarrega nada, e sem JS a lista inteira continua legível. */
  function indice(lista) {
    var alvo = document.getElementById('blogLista');
    if (!alvo) return;
    if (!lista.length) {
      alvo.innerHTML = '<li class="u-muted">Nenhum texto publicado até agora.</li>';
      return;
    }
    alvo.innerHTML = lista.map(function (p) {
      return '<li data-etiqueta="' + esc(p.etiqueta || '') + '">'
        + '<a href="' + esc(p.url) + '"><strong>' + esc(p.titulo) + '</strong></a>'
        + '<span class="spec"> ' + esc(p.etiqueta || '') + ' · ' + esc(p.data_br || '') + '</span>'
        + '<p class="u-mb-0">' + esc(p.resumo || '') + '</p></li>';
    }).join('');

    var filtro = document.getElementById('blogFiltro');
    if (!filtro) return;
    var presentes = [];
    lista.forEach(function (p) {
      if (p.etiqueta && presentes.indexOf(p.etiqueta) < 0) presentes.push(p.etiqueta);
    });
    if (presentes.length < 2) { filtro.hidden = true; return; }
    filtro.innerHTML = '<option value="">Todas as etiquetas</option>'
      + presentes.map(function (e) { return '<option>' + esc(e) + '</option>'; }).join('');
    filtro.addEventListener('change', function () {
      var alvoEtiqueta = filtro.value;
      Array.prototype.forEach.call(alvo.querySelectorAll('li'), function (li) {
        li.hidden = !!alvoEtiqueta && li.getAttribute('data-etiqueta') !== alvoEtiqueta;
      });
    });
  }
})();
