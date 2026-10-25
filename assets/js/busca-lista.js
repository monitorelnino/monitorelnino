/* Filtro de lista enquanto se digita (glossário, perguntas). Compartilhado; sem biblioteca.
   BuscaLista.montar(campo, itens): oculta (hidden) os itens cujo texto não contém o termo. */
(function () {
  function montar(campo, itens) {
    function filtrar() {
      var q = campo.value.trim().toLowerCase();
      itens.forEach(function (el) {
        el.hidden = q !== '' && el.textContent.toLowerCase().indexOf(q) === -1;
      });
    }
    campo.addEventListener('input', filtrar);
    return filtrar;
  }
  window.BuscaLista = { montar: montar };
})();
