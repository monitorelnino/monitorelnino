/* Portão: a página de imprensa não escreve à mão nada que dependa do dado.
 *
 * Regra 0 do handover de 01/10/2026. Tudo o que muda quando o site se atualiza — os dois índices,
 * a data da edição, os seis números do topo, os cartões da semana, os números do release, as
 * versões dos índices — sai de `data/*.json` a cada publicação.
 *
 * O QUE ELE EXISTE PARA BARRAR
 * ----------------------------
 * Duas coisas, e as duas já aconteceram nesta página:
 *
 *   (a) **Número congelado.** O release trazia "Essas contagens são refeitas a partir de 26 de
 *       outubro" e "Desde julho, — páginas oficiais estão fora do ar": uma data que passou e um
 *       traço que nunca virou número. Número escrito à mão não envelhece com aviso; envelhece em
 *       silêncio.
 *   (b) **Versão divergente.** A página citava "antecipação" depois de a v3.1 ter tirado o
 *       componente temporal do índice. A versão publicada tem de ser a do motor que calculou o
 *       número, não uma string paralela.
 *
 * Ele renderiza a página de verdade, com o banco de verdade, e confere o resultado — não o código
 * que o produz. É a única forma de pegar o traço que ficou.
 *
 * Uso: node scripts/verificar_imprensa_do_dado.js
 */
const fs = require("fs");
const path = require("path");
const { JSDOM, VirtualConsole } = require("jsdom");
const { inlinePageJs } = require("./_inline_js");

const RAIZ = path.resolve(__dirname, "..");
const PAGINA = "imprensa.html";

// Os campos que NÃO podem ficar em "—" depois de a página carregar. Cada um é um número ou uma
// data que o banco tem: se aparecer travessão aqui, a leitura falhou ou o id mudou de nome, e nos
// dois casos a página publicada mente por omissão.
// 01/10/2026: a lista acompanha a página reorganizada. Saíram os quatro contadores do topo e os
// ids do release antigo (`relMedia`, `relDecretados`, `relPlanosMun`, `relQ1`, `relQ3`), que não
// existem mais; entraram os do release aprovado.
// 02/10/2026 (redesenho da imprensa): o release deixou de ser gabarito com um `<span>` por número
// e passou a ser o TEXTO GERADO por gerar_imprensa_semana.py. Saíram da lista os ids daquele
// gabarito (`relLegal`, `relSaude`, `relPlanosSemana`, `relDecretosSemana`, `relPopSemana`,
// `relPlanosTotal`, `relDecretosTotal`), que não existem mais. A garantia não enfraquece: o texto
// do release é conferido abaixo contra o próprio arquivo que o gerou, e o motor tem autoteste.
// 03/10/2026 (handover do blog e da imprensa): a página passa a ter só o ESTÁVEL. `relData` saiu
// com a frase de abertura que trazia a data da edição — a data agora vive no cartão do boletim,
// que é o único elemento dinâmico, e no bloco "Como citar". Os ids que restam são os que a regra 0
// sempre quis proteger: índice, versão e data de acesso vindos do banco, nunca escritos à mão.
const OBRIGATORIOS = [
  "topoLegal", "topoSaude",
  "citarVersaoLegal", "citarVersaoSaude", "citarAcesso",
  // 04/10/2026 (rotina semanal): `boletimData` saiu, e `textosDaSemana` NÃO entra nesta lista. A
  // lista exige conteúdo preenchido do banco, e o ponteiro dos textos pode estar legitimamente
  // vazio — enquanto nenhuma das duas linhas da rotina tiver texto publicado, a lista se esconde e
  // a seção fica com o título e o caminho para o blog. Quem confere o ponteiro é o bloco próprio,
  // abaixo: cada link mostrado tem de existir em posts.json, e número nenhum pode aparecer.
];

const falhas = [];
const ler = p => JSON.parse(fs.readFileSync(path.join(RAIZ, p), "utf-8"));

(async () => {
  const vc = new VirtualConsole();
  const html = inlinePageJs(fs.readFileSync(path.join(RAIZ, PAGINA), "utf-8"), RAIZ);
  const dom = new JSDOM(html, {
    runScripts: "dangerously", resources: undefined, url: "https://localhost/",
    virtualConsole: vc,
    beforeParse(w) {
      w.fetch = (rel) => {
        try {
          const txt = fs.readFileSync(path.join(RAIZ, rel.split("?")[0]), "utf-8");
          return Promise.resolve({ ok: true, json: () => Promise.resolve(JSON.parse(txt)) });
        } catch (e) { return Promise.resolve({ ok: false }); }
      };
    },
  });
  await new Promise(r => setTimeout(r, 2500));
  const d = dom.window.document;
  const txt = id => ((d.getElementById(id) || {}).textContent || "").trim();

  for (const id of OBRIGATORIOS) {
    if (!d.getElementById(id)) { falhas.push(`${PAGINA}: id '${id}' não existe mais — o portão cobra um campo que a página não tem`); continue; }
    const v = txt(id);
    if (!v || v === "—") falhas.push(`${PAGINA}: '${id}' ficou em "${v || "vazio"}" — é número ou data que vem do banco`);
  }

  // A versão publicada é a do motor que calculou o número.
  const idx = ler("data/indice.json");
  const uf = Object.keys(idx).find(k => k.length === 2);
  const versaoMotor = String((idx[uf] || {}).metodo || "").match(/^v(\d+(?:\.\d+)*)/);
  if (versaoMotor && txt("citarVersaoLegal") !== versaoMotor[1]) {
    falhas.push(`${PAGINA}: versão do MARÉ Legal na página ("${txt("citarVersaoLegal")}") ≠ a do motor em data/indice.json ("${versaoMotor[1]}")`);
  }
  const saude = ler("data/monitor_saude.json");
  if (saude.versao != null && txt("citarVersaoSaude") !== String(saude.versao)) {
    falhas.push(`${PAGINA}: versão do MARÉ Saúde na página ("${txt("citarVersaoSaude")}") ≠ data/monitor_saude.json ("${saude.versao}")`);
  }

  /* 04/10/2026 — O PONTEIRO É DOS TEXTOS, NÃO DO BOLETIM.
   *
   * O handover da rotina semanal trocou "O boletim desta semana" por "Textos desta semana": dois
   * links, título e data, um por linha da rotina, e **sem números** — os números vivem nas páginas
   * do Monitor e no pacote interno, e um número aqui seria uma terceira cópia a conferir toda
   * semana. O que a regra 0 cobra, então, é que cada link mostrado exista em `posts.json` com
   * aquele título: nada escrito à mão, nada que envelheça em silêncio.
   *
   * Sem texto de nenhuma das duas linhas, a LISTA é escondida pelo próprio script e a seção fica
   * com o título e o ponteiro permanente para o blog. Esse caso não é falha: é a página dizendo
   * menos, que é o certo quando não há o que dizer.
   */
  try {
    const dados = ler("data/blog/posts.json");
    const posts = Array.isArray(dados) ? dados : (dados.posts || []);
    const LINHAS = ["Legal e financiamento", "Saúde"];
    const esperados = LINHAS
      .map(linha => posts.filter(p => (p.etiqueta || "") === linha)[0])
      .filter(Boolean);
    const itens = d.querySelectorAll("#textosDaSemana li");
    if (itens.length !== esperados.length) {
      falhas.push(`${PAGINA}: o ponteiro mostra ${itens.length} texto(s) e as duas linhas da `
                  + `rotina têm ${esperados.length} publicado(s)`);
    }
    const mostrado = txt("textosDaSemana");
    for (const p of esperados) {
      if (!mostrado.includes(p.titulo)) {
        falhas.push(`${PAGINA}: o texto "${p.titulo}" não aparece no ponteiro`);
      }
      if (p.data_br && !mostrado.includes(p.data_br)) {
        falhas.push(`${PAGINA}: a data ${p.data_br} do texto não aparece no ponteiro`);
      }
    }
    // A trava do que SAIU: número no ponteiro significa que o cartão numérico voltou.
    if (/\d{1,3}(\.\d{3})+|\d{3,}/.test(mostrado)) {
      falhas.push(`${PAGINA}: o ponteiro dos textos mostra número — os números vivem nas páginas `
                  + `e no pacote, não aqui (handover de 04/10/2026)`);
    }
  } catch (e) { falhas.push(`${PAGINA}: posts.json ilegível: ${e.message}`); }

  if (falhas.length) {
    console.log("✗ IMPRENSA (regra 0 — nada à mão que dependa do dado):");
    falhas.forEach(f => console.log("   -", f));
    process.exit(1);
  }
  console.log(`✓ IMPRENSA OK — ${OBRIGATORIOS.length} campos vindos do banco, versões e data da edição batendo com data/indice.json, data/monitor_saude.json e data/meta.json.`);
})();
