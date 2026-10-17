/* Consulta do município: um componente para todas as páginas (17/10/2026, PLANO_DE_EXECUCAO B1 item 0).
 * Comportamento aprovado na inicial (30/09 e 16/10/2026): "1 · Seu estado…" abre "2 · Seu município…"
 * com a lista daquele estado; o cartão `.meu-card` só aparece quando o nome casa com a lista; nome que
 * não está na lista recebe uma frase; clicar no campo com um município escolhido o esvazia e reabre a
 * lista inteira, sem botão de limpar (o cartão anterior fica até o novo nome casar).
 * Cada página dá só o que é dela:
 *   estados     {sigla: nome}
 *   municipios  uf → lista de nomes (ou promessa dela; nulo = o estado não tem arquivo)
 *   mostrar     (uf, nome, cartão) → escreve o conteúdo do cartão
 *   semLista    texto da lacuna quando `municipios` devolve nulo
 * Os ids dos controles vêm em `uf`, `municipio`, `lista` e `cartao`. */
(function (global) {
  'use strict';
  const nrm = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();

  function montar(o) {
    const $ = id => document.getElementById(id);
    const selUF = $(o.uf), inp = $(o.municipio), lista = $(o.lista), card = $(o.cartao);
    let nomes = [];
    const oficial = v => nomes.find(n => nrm(n) === nrm(v)) || '';
    const esconder = () => { card.hidden = true; card.innerHTML = ''; };
    const frase = (texto, classe) => {
      const p = document.createElement('p');
      if (classe) p.className = classe;
      p.textContent = texto;
      card.replaceChildren(p); card.hidden = false;
    };
    Object.entries(o.estados).sort((a, b) => a[1].localeCompare(b[1]))
      .forEach(([sigla, nome]) => selUF.add(new Option(nome, sigla)));

    function render() {
      const uf = selUF.value, q = nrm(inp.value);
      if (!uf || !q) return esconder();
      const nome = oficial(inp.value);
      if (nome) { o.mostrar(uf, nome, card); card.hidden = false; return; }
      // Ainda digitando um nome que existe: sem cartão até casar (o evento é `input`).
      if (nomes.some(n => nrm(n).startsWith(q))) return esconder();
      frase('Não encontramos “' + inp.value.trim() + '” na lista de municípios do IBGE para ' + uf
        + '. Confira a grafia ou escolha o nome na lista.');
    }
    // A lista do estado chega síncrona (inicial) ou por arquivo (Monitor de riscos); a síncrona
    // não espera, para o campo abrir no mesmo evento.
    function abrir(uf, r) {
      if (selUF.value !== uf) return;
      if (!r) return frase(o.semLista, 'lacuna');
      nomes = r;
      lista.replaceChildren(...nomes.map(n => new Option(n)));
      inp.disabled = false;
    }
    selUF.addEventListener('change', () => {
      const uf = selUF.value;
      inp.value = ''; inp.disabled = true; lista.replaceChildren(); nomes = []; esconder();
      if (!uf) return;
      const r = o.municipios(uf);
      if (r && typeof r.then === 'function') r.then(x => abrir(uf, x), () => abrir(uf, null));
      else abrir(uf, r);
    });
    inp.addEventListener('input', render);
    ['focus', 'click'].forEach(ev => inp.addEventListener(ev, () => { if (oficial(inp.value)) inp.value = ''; }));
  }

  global.ConsultaMunicipio = { montar, nrm };
})(window);
