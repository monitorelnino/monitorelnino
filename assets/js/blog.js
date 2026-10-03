/* ===== blog.html · índice dos textos e cartão do boletim =================================
 *
 * 03/10/2026 (handover do blog e da imprensa). Duas coisas, e nada mais:
 *
 *   1. a LISTA dos textos, do mais novo ao mais antigo, com título, etiqueta (Boletim ·
 *      Acontecimento), data e a abertura de uma linha;
 *   2. o CARTÃO do boletim mais recente, com três números da semana — os mesmos três que a
 *      Imprensa aponta —, congelados na data da edição.
 *
 * Os quatro quadros "Situação do monitoramento" saíram: usavam o vocabulário antigo
 * ("antecipação", "prontidão") e repetiam, com outra régua, o que as páginas publicam. E o corpo
 * dos textos não recebe cartão nenhum — os números vivem nas páginas, e o texto pode citá-los.
 */
(function () {
  'use strict';
  var esc = function (v) {
    return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  };

  /* A lista. Sem texto, a página diz que ainda não há — e não finge uma lista vazia. */
  fetch('data/blog/posts.json').then(function (r) { return r.ok ? r.json() : null; })
    .then(function (posts) {
      var alvo = document.getElementById('blogLista');
      if (!alvo) return;
      var lista = Array.isArray(posts) ? posts : (posts && posts.posts) || [];
      if (!lista.length) {
        alvo.innerHTML = '<li class="u-muted">Nenhum texto publicado até agora.</li>';
        return;
      }
      alvo.innerHTML = lista.map(function (p) {
        return '<li><a href="' + esc(p.url) + '"><strong>' + esc(p.titulo) + '</strong></a>'
          + '<span class="spec"> ' + esc(p.etiqueta || p.categoria_rotulo || '') + ' · '
          + esc(p.data_br || '') + '</span>'
          + '<p class="u-mb-0">' + esc(p.resumo || '') + '</p></li>';
      }).join('');
    }).catch(function () {});

  /* O cartão do boletim: a edição mais recente com etiqueta Boletim, e os três números dela.
     Os números vêm CONGELADOS do arquivo da edição (`data/blog/boletins/<data>.json`), e não do
     motor da semana — um boletim de três semanas atrás mostrando o número de hoje seria outro
     documento. Sem edição, a seção inteira some: cartão vazio é pior que seção ausente. */
  Promise.all([
    fetch('data/blog/posts.json').then(function (r) { return r.ok ? r.json() : null; }),
    fetch('data/blog/boletim_mais_recente.json').then(function (r) { return r.ok ? r.json() : null; })
  ]).then(function (resp) {
    var posts = resp[0], boletim = resp[1];
    var secao = document.getElementById('boletim');
    var lista = Array.isArray(posts) ? posts : (posts && posts.posts) || [];
    var ed = lista.filter(function (p) { return (p.etiqueta || '') === 'Boletim'; })[0];
    if (!ed || !boletim || !(boletim.numeros || []).length) {
      if (secao) secao.hidden = true;
      return;
    }
    var data = document.getElementById('boletimData');
    if (data) data.textContent = 'Edição de ' + (boletim.edicao || ed.data_br || '');
    var link = document.getElementById('boletimLink');
    if (link) { link.href = ed.url; link.textContent = 'ler o boletim de ' + (ed.data_br || ''); }
    var grade = document.getElementById('boletimNumeros');
    if (grade) {
      grade.innerHTML = boletim.numeros.slice(0, 3).map(function (n) {
        return '<div class="cartao-numero">'
          + '<p class="cartao-numero-valor">' + esc(n.valor) + '</p>'
          + '<p class="cartao-numero-rotulo">' + esc(n.rotulo) + '</p>'
          + '<p class="cartao-numero-fonte">' + esc(n.fonte || '') + '</p></div>';
      }).join('');
    }
  }).catch(function () {});
})();
