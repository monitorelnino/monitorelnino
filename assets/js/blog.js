/* ===== blog.html · os textos do blog, inteiros, um após o outro =========================
 *
 * 05/10/2026 (handover da preparação programática, item 6.1). O blog deixa de ser índice de
 * links: cada texto aparece INTEIRO, do mais recente ao mais antigo, com título, etiqueta e data,
 * autoria, corpo em prosa, linha de fontes e "como citar" com o endereço permanente.
 *
 * A partir do décimo primeiro texto, os DEZ mais recentes ficam inteiros e os anteriores vão para
 * a lista do fim — a página não pode crescer sem limite, e o endereço permanente de cada texto
 * continua sendo o lugar dele.
 *
 * Saíram os dois cartões de "textos mais recentes" e o filtro por etiqueta. O cartão repetiria
 * título e abertura logo acima do próprio texto.
 *
 * O corpo vem de `data/blog/posts.json`, que o `gerar_blog.py` escreve a partir do texto aprovado
 * pela editoria: é HTML que o próprio gerador produziu com o Markdown do texto, e por isso entra
 * como HTML. Tudo o mais — título, etiqueta, data, autoria, fontes, endereço — é escapado.
 */
(function () {
  'use strict';
  var INTEIROS = 10;

  var esc = function (v) {
    return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  };

  /* Os rótulos vêm do catálogo de conteúdo; o de reserva fica aqui, para a página não aparecer
     com um vazio no lugar da frase se o JSON não carregar. */
  function frase(id, valores, reserva) {
    var C = window.MonitorCatalogo;
    var t = C && C.texto ? C.texto(id, valores || {}) : null;
    return t == null ? reserva : t;
  }

  /* Espera o catálogo antes de compor: o `fetch` dos textos e o do catálogo resolvem em ordem
     imprevisível, e compor antes pediria uma entrada que ainda não existe. Foi a corrida medida no
     Financiamento em 05/10. Sem catálogo na página, segue com os rótulos de reserva. */
  var pronto = (window.MonitorCatalogo && window.MonitorCatalogo.pronto) || Promise.resolve();

  Promise.all([
    fetch('data/blog/posts.json').then(function (r) { return r.ok ? r.json() : null; }),
    pronto,
  ]).then(function (par) {
    var dados = par[0];
    var lista = Array.isArray(dados) ? dados : (dados && dados.posts) || [];
    textos(lista.slice(0, INTEIROS));
    anteriores(lista.slice(INTEIROS));
  }).catch(function () {});

  /* Cada texto inteiro, na ordem em que o índice já vem: do mais recente ao mais antigo. */
  function textos(lista) {
    var alvo = document.getElementById('blogTextos');
    if (!alvo) return;
    if (!lista.length) {
      alvo.innerHTML = '<p class="u-muted">'
        + esc(frase('blog.textos.sem_texto', {}, 'Nenhum texto publicado até agora.')) + '</p>';
      return;
    }
    alvo.innerHTML = lista.map(function (p) {
      var selo = [p.etiqueta || p.categoria_rotulo, p.data_br, p.autor]
        .filter(Boolean).map(esc).join(' · ');
      var partes = ['<article class="panel post" id="post-' + esc(p.slug) + '">'];
      if (selo) partes.push('<p class="selo">' + selo + '</p>');
      partes.push('<h3><a href="' + esc(p.url) + '">' + esc(p.titulo) + '</a></h3>');
      if (p.resumo) partes.push('<p class="hint post-lede">' + esc(p.resumo) + '</p>');
      partes.push('<div class="post-corpo">' + (p.html || '') + '</div>');
      if (p.fontes) {
        partes.push('<p class="post-fontes spec">'
          + esc(frase('blog.textos.rotulo_fontes', { fontes: p.fontes },
            'Fontes: ' + p.fontes)) + '</p>');
      }
      if (p.endereco_permanente) {
        /* O endereço é link, e o leitor do catálogo escreve texto, não marcação: o molde traz a
           frase até a data, e o link vem depois, montado aqui. */
        partes.push('<p class="post-citar spec">'
          + esc(frase('blog.textos.como_citar',
            { titulo: p.titulo, data: p.data_br || '' },
            'Como citar: Editoria do MARÉ. ' + p.titulo + '. Blog do MARÉ, '
            + (p.data_br || '') + '.'))
          + ' <a href="' + esc(p.endereco_permanente) + '">'
          + esc(p.endereco_permanente) + '</a></p>');
      }
      partes.push('</article>');
      return partes.join('');
    }).join('');
  }

  /* Do décimo primeiro em diante: título, etiqueta e data, com link para a página do texto. A
     seção só aparece quando há o que listar — seção vazia com título afirma que existe algo ali. */
  function anteriores(lista) {
    var alvo = document.getElementById('blogLista');
    var secao = document.getElementById('anteriores');
    if (!alvo || !secao) return;
    if (!lista.length) { secao.hidden = true; return; }
    alvo.innerHTML = lista.map(function (p) {
      return '<li><a href="' + esc(p.url) + '"><strong>' + esc(p.titulo) + '</strong></a>'
        + '<span class="spec"> ' + esc(p.etiqueta || '') + ' · ' + esc(p.data_br || '')
        + '</span></li>';
    }).join('');
    secao.hidden = false;
  }
})();
