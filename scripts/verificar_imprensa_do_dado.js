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
const OBRIGATORIOS = [
  "relData", "topoLegal", "topoSaude",
  "citarVersaoLegal", "citarVersaoSaude", "citarAcesso",
  "relLegal", "relSaude", "relPlanosSemana", "relDecretosSemana", "relPopSemana",
  "relPlanosTotal", "relDecretosTotal",
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

  // A data da edição é a do banco.
  const meta = ler("data/meta.json");
  const esperada = meta.atualizado_em || meta.corte;
  if (esperada && txt("relData") !== esperada) {
    falhas.push(`${PAGINA}: data da edição na página ("${txt("relData")}") ≠ data/meta.json ("${esperada}")`);
  }

  // Os dois contadores semanais são os MESMOS cartões da seção da semana: dois números iguais na
  // mesma página com contas diferentes é o defeito que a regra 0 existe para impedir.
  try {
    const semana = ler("data/imprensa/semana.json");
    const de = id => (semana.cartoes.find(c => c.id === id) || {}).valor;
    // O número da semana aparece duas vezes na página: no cartão e no release. É aí que a conta
    // dupla pode nascer, e é aí que o portão olha. "nenhum" é a forma aprovada do zero no release.
    const pares = [["relPlanosSemana", "planos_no_periodo"],
                   ["relDecretosSemana", "decretos_no_periodo"],
                   ["relPopSemana", "populacao_decretos_no_periodo"]];
    for (const [id, cartao] of pares) {
      const naPagina = txt(id).replace(/\./g, "");
      const noDado = de(cartao);
      const esperado = noDado === 0 ? "nenhum" : String(noDado);
      if (noDado != null && naPagina !== esperado) {
        falhas.push(`${PAGINA}: '${id}' mostra ${naPagina} e o cartão '${cartao}' tem ${noDado} — o mesmo número com duas contas`);
      }
    }
  } catch (e) { falhas.push(`${PAGINA}: data/imprensa/semana.json ilegível: ${e.message}`); }

  if (falhas.length) {
    console.log("✗ IMPRENSA (regra 0 — nada à mão que dependa do dado):");
    falhas.forEach(f => console.log("   -", f));
    process.exit(1);
  }
  console.log(`✓ IMPRENSA OK — ${OBRIGATORIOS.length} campos vindos do banco, versões e data da edição batendo com data/indice.json, data/monitor_saude.json e data/meta.json.`);
})();
