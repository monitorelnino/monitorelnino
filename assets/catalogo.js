// O LEITOR DO CATÁLOGO DE CONTEÚDO — a página pede o texto, não o guarda.
//
// Handover do catálogo de conteúdo (05/10/2026). A editoria separou três camadas: ESTRUTURA (o
// contrato de layout, em `layout/contratos/<pagina>.json`), CONTEÚDO (o catálogo, em
// `conteudo/<pagina>.json`) e DADO (os geradores, que produzem `data/*.json`). Este arquivo liga a
// segunda à página: todo elemento com `data-conteudo="<id>"` recebe o texto daquele identificador.
//
// POR QUE ISSO EXISTE. Antes, mudar uma legenda era abrir o HTML, achar a linha, editar, rodar os
// portões e abrir um PR de página. Agora é uma linha num JSON, aplicada por
// `scripts/aplicar_edicoes.py` a partir de um pedido aprovado — sem reabrir a página. O texto deixa
// de estar misturado com a marcação, e passa a ter identificador estável, que é o que permite à
// editoria apontar "este trecho" sem descrever onde ele fica.
//
// O QUE ELE NÃO FAZ. Não formata número, não decide plural a partir de dado, não busca `data/`.
// Quando o texto depende de valor, o catálogo guarda um MOLDE com marcadores `{chave}` e quem o
// preenche é o código da página, que já tem o dado em mão — este leitor só resolve o molde quando
// recebe os valores. A fronteira é de propósito: dado é a terceira camada.
//
// FALHA SEGURA. Se o catálogo não carregar, a página NÃO fica em branco: o texto que está no HTML
// permanece, porque este leitor só SOBRESCREVE quando tem o que escrever. É a razão de a migração
// manter o texto no HTML em vez de esvaziá-lo — o catálogo é a fonte, o HTML é a reserva.
(function () {
  "use strict";

  const Catalogo = {
    pagina: null,
    textos: {},
    comum: {},
    carregado: false,
  };

  function nomeDaPagina() {
    const p = (location.pathname.split("/").pop() || "index.html").trim();
    return (p || "index.html").replace(/\.html$/, "");
  }

  // Resolve o molde: `{chave}` vira valor, e `{n|nenhum …|um …|{n} …}` escolhe pelo número.
  //
  // A forma do plural é a do handover (item 1.2): três ramos separados por `|`, na ordem
  // ZERO · UM · MUITOS, e o ramo escolhido pode conter `{n}` para trazer o número formatado. Ela
  // existe porque "0 municípios decretaram" é texto que o projeto não publica: zero é por extenso,
  // e um não leva plural. Deixar isso no código espalharia a mesma decisão por dez arquivos.
  function resolverMolde(molde, valores) {
    if (typeof molde !== "string") return molde;
    const v = valores || {};

    // Primeiro os ramos de plural, porque eles contêm `{n}` dentro.
    // O último ramo aceita `{chave}` dentro, e SÓ isso. Com `[^|]*?` ele fecharia no `}` do
    // marcador interno e devolveria `{n vários}` em vez de `3 vários`; com `[^|]*` guloso
    // atravessaria dois moldes na mesma frase.
    let fora = molde.replace(/\{(\w+)\|([^|{}]*)\|([^|{}]*)\|((?:[^|{}]|\{\w+\})*)\}/g,
      function (_todo, chave, zero, um, muitos) {
        const n = Number(v[chave]);
        if (!isFinite(n)) return _todo;
        const ramo = n === 0 ? zero : (n === 1 ? um : muitos);
        return ramo.replace(/\{(\w+)\}/g, (_m, k) => formatar(v[k]));
      });

    // Depois os marcadores simples.
    fora = fora.replace(/\{(\w+)\}/g, function (todo, chave) {
      return Object.prototype.hasOwnProperty.call(v, chave) ? formatar(v[chave]) : todo;
    });
    return fora;
  }

  // Número em pt-BR, como o resto do site o escreve. Texto passa inteiro.
  function formatar(valor) {
    if (typeof valor === "number" && isFinite(valor)) return valor.toLocaleString("pt-BR");
    return valor == null ? "" : String(valor);
  }

  function texto(id, valores) {
    const bruto = Object.prototype.hasOwnProperty.call(Catalogo.textos, id)
      ? Catalogo.textos[id]
      : Catalogo.comum[id];
    if (bruto == null) return null;
    return resolverMolde(bruto, valores);
  }

  // Preenche os elementos marcados. Chamável de novo: quem muda um molde recalcula só o seu.
  function aplicar(raiz) {
    const onde = raiz || document;
    let postos = 0, ausentes = [];
    onde.querySelectorAll("[data-conteudo]").forEach(function (el) {
      // Elemento FIXADO é o que o código da página já compôs com dado em mão (um molde resolvido).
      // O leitor não o sobrescreve: se o catálogo carregar depois do `fetch` da página — e carrega,
      // quando a rede está rápida para um e lenta para o outro —, reescrever aqui apagaria o
      // número e deixaria só o texto de reserva. Foi o que a primeira medição da migração mostrou.
      if (el.hasAttribute("data-conteudo-fixado")) return;
      const id = el.getAttribute("data-conteudo");
      const t = texto(id, el.dataset.conteudoValores ? JSON.parse(el.dataset.conteudoValores) : null);
      if (t == null) { ausentes.push(id); return; }
      // `textContent`, não `innerHTML`: o catálogo guarda TEXTO. Entrada que precise de marcação
      // (um link dentro da prosa) declara-se com `data-conteudo-html`, abaixo, e aí o portão de
      // conformidade a confere com o mesmo rigor.
      el.textContent = t;
      postos += 1;
    });
    onde.querySelectorAll("[data-conteudo-html]").forEach(function (el) {
      // A marca de FIXADO vale aqui também. Ela só estava no caminho de texto, e a assimetria era
      // um defeito à espera: uma entrada com marcação que a página compõe com dado em mão seria
      // reescrita com o molde não resolvido na primeira `aplicar` que passasse depois — a mesma
      // corrida que o Financiamento mediu em 05/10/2026, só que no outro caminho.
      if (el.hasAttribute("data-conteudo-fixado")) return;
      const id = el.getAttribute("data-conteudo-html");
      const t = texto(id, el.dataset.conteudoValores ? JSON.parse(el.dataset.conteudoValores) : null);
      if (t == null) { ausentes.push(id); return; }
      el.innerHTML = t;
      postos += 1;
    });
    if (ausentes.length) {
      // Não quebra a página: avisa no console e deixa o texto de reserva do HTML. O portão
      // `verificar_catalogo.py` é que reprova identificador ausente, no PR, onde dá para consertar.
      console.warn("catálogo: " + ausentes.length + " identificador(es) sem entrada: "
                   + ausentes.slice(0, 8).join(", "));
    }
    return { postos: postos, ausentes: ausentes };
  }

  async function carregar() {
    Catalogo.pagina = nomeDaPagina();
    const pedir = async (caminho) => {
      try {
        const r = await fetch(caminho, { cache: "no-cache" });
        if (!r.ok) return {};
        return await r.json();
      } catch (e) { return {}; }
    };
    const [proprio, comum] = await Promise.all([
      pedir("conteudo/" + Catalogo.pagina + ".json"),
      pedir("conteudo/_comum.json"),
    ]);
    Catalogo.textos = (proprio && proprio.textos) || {};
    Catalogo.comum = (comum && comum.textos) || {};
    Catalogo.carregado = true;
    return aplicar(document);
  }

  // Escreve no elemento uma entrada do catálogo, resolvendo o molde com os valores dados.
  //
  // É por aqui que o código da página põe texto que depende de dado. Duas garantias que o call
  // site não precisa repetir: (a) se o catálogo não tiver a entrada, NÃO escreve — o texto de
  // reserva do HTML permanece, e a página não fica com um vazio no lugar da frase; (b) marca o
  // elemento como fixado, para o leitor não o sobrescrever quando terminar de carregar.
  function escrever(elemento, id, valores) {
    const el = typeof elemento === "string" ? document.getElementById(elemento) : elemento;
    if (!el) return null;
    const t = texto(id, valores);
    if (t == null || t === "") return null;
    el.textContent = t;
    el.setAttribute("data-conteudo-fixado", "1");
    return t;
  }

  // O catálogo é assíncrono, e quem compõe texto com dado precisa saber quando ele chegou. Sem
  // isto, o `fetch` da página pode resolver antes e pedir uma entrada que ainda não existe.
  let resolverPronto;
  const pronto = new Promise((r) => (resolverPronto = r));

  window.MonitorCatalogo = {
    carregar: carregar,
    aplicar: aplicar,
    texto: texto,
    escrever: escrever,
    resolverMolde: resolverMolde,
    pronto: pronto,
    estado: Catalogo,
  };

  // Carrega sozinho, cedo: o texto tem de estar posto antes de o leitor ver a página. Se o
  // documento já passou do `DOMContentLoaded` (script com `defer` que entrou depois), chama já.
  const iniciar = () => carregar().then((r) => { resolverPronto(r); return r; });
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
