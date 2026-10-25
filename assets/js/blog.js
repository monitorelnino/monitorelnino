/* ===== blog.html · índice do blog: o texto mais recente em destaque e, abaixo, uma coluna por
 * editoria (mockup aprovado em notas/mockups/blog_indice.html, 25/10/2026). Cada texto vive no
 * seu endereço permanente; a página só lista. O corpo, a abertura e as fontes vêm de
 * `data/blog/posts.json`, escrito pelo `gerar_blog.py`; os rótulos vêm de `conteudo/blog.json`.
 */
(function () {
  'use strict';

  var EDITORIAS = [
    { etiqueta: 'Legal e financiamento', classe: 'cartao--acento-argila', quando: 'Às segundas' },
    { etiqueta: 'Saúde', classe: 'cartao--acento-chuva', quando: 'Às quintas' },
  ];

  var esc = function (v) {
    return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  };

  /* Os rótulos vêm do catálogo; o de reserva fica aqui para a página não aparecer com um vazio. */
  function frase(id, valores, reserva) {
    var C = window.MonitorCatalogo;
    var t = C && C.texto ? C.texto(id, valores || {}) : null;
    return t == null ? reserva : t;
  }

  /* Espera o catálogo antes de compor, para não pedir um rótulo que ainda não chegou. */
  var pronto = (window.MonitorCatalogo && window.MonitorCatalogo.pronto) || Promise.resolve();

  Promise.all([
    fetch('data/blog/posts.json').then(function (r) { return r.ok ? r.json() : null; }),
    pronto,
  ]).then(function (par) {
    var dados = par[0];
    var lista = Array.isArray(dados) ? dados : (dados && dados.posts) || [];
    destaque(lista[0]);
    colunas(lista);
  }).catch(function () {});

  function linhaFontes(p) {
    return p.fontes
      ? '<p class="post-fontes spec">' + esc(frase('blog.textos.rotulo_fontes', { fontes: p.fontes }, 'Fontes: ' + p.fontes)) + '</p>'
      : '';
  }

  /* O texto mais recente de qualquer editoria, com título, linha fina e endereço. */
  function destaque(p) {
    var alvo = document.getElementById('blogDestaque');
    if (!alvo || !p) return;
    alvo.innerHTML = '<article class="panel post post--destaque">'
      + '<p class="selo">' + esc(p.etiqueta || '') + ' · ' + esc(p.data_br || '') + '</p>'
      + '<h2><a href="' + esc(p.url) + '">' + esc(p.titulo) + '</a></h2>'
      + (p.resumo ? '<p class="hint post-lede">' + esc(p.resumo) + '</p>' : '')
      + linhaFontes(p)
      + '<p><a href="' + esc(p.url) + '">' + esc(frase('blog.destaque.ler', {}, 'Ler o texto →')) + '</a></p>'
      + '</article>';
  }

  /* Uma coluna por editoria, do texto mais novo ao mais antigo; sem texto, a frase com a data do corte. */
  function colunas(lista) {
    var alvo = document.getElementById('blogColunas');
    if (!alvo) return;
    var corte = (document.getElementById('corteDados') || {}).textContent || '';
    alvo.innerHTML = EDITORIAS.map(function (ed) {
      var textos = lista.filter(function (p) { return p.etiqueta === ed.etiqueta; });
      var corpo = textos.length
        ? '<ol class="blog-lista">' + textos.map(function (p) {
            return '<li><span class="spec">' + esc(p.data_br || '') + '</span>'
              + '<a href="' + esc(p.url) + '"><strong>' + esc(p.titulo) + '</strong></a>'
              + (p.resumo ? '<p class="hint">' + esc(p.resumo) + '</p>' : '') + '</li>';
          }).join('') + '</ol>'
        : '<p class="hint">' + esc(frase('blog.colunas.sem_texto', { data: corte },
            'Nenhum texto publicado nesta editoria até ' + corte + '.')) + '</p>';
      return '<section class="cartao-mapa ' + ed.classe + '">'
        + '<h2 class="selo">' + esc(ed.etiqueta) + '</h2>'
        + '<p class="spec">' + esc(ed.quando) + '</p>'
        + corpo + '</section>';
    }).join('');
  }
})();
