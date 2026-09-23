// Renderizador do painel Power BI da Defesa Civil do AM (§165, 23/09/2026).
//
// POR QUE EXISTE. A sonda de camada (§164, sondar_paineis.py) descobre QUE existe um painel;
// não o abre. Power BI monta a tabela em JavaScript depois do carregamento, então a busca
// textual recebe de app.powerbi.com só o esqueleto da página. Ler a tabela dos 62 municípios
// do AM exige navegador real — é o que este script faz, e só isto.
//
// DIVISÃO DE TRABALHO (deliberada): aqui só se RENDERIZA e se EXTRAI o que está na tela,
// em bruto. Quem casa município com código IBGE, baixa documento, preserva evidência, lê
// número e data do ato e decide camada é coletar_painel_am.py — em Python, testável offline,
// com as travas do projeto. Este arquivo não escreve nada no banco nem em data/.
//
// SAÍDA: um único JSON em stdout (contrato com o lado Python):
//   { ok, url, lido_em, colunas[], linhas[{indice, celulas{}, url_do_link|null, como_obtido}],
//     n_linhas, diagnostico{}, erro|null }
// Toda incerteza vira campo declarado, nunca palpite: célula ausente é null, link não obtido
// é null com o motivo em `como_obtido`. O lado Python transforma isso em lacuna declarada.
//
// Uso: node scripts/renderizar_painel_am.js <url> [--espera-ms N] [--html-para <arquivo>]
const { chromium } = require('playwright');

const ALVO_LINHAS = 62;            // 62 municípios do AM — conferido contra a referência IBGE
const MAX_ROLAGENS = 40;           // teto de rolagens da grade virtualizada

// Alguns ambientes (CI do projeto, contêiner do agente) trazem um Chromium pré-instalado
// cuja revisão não bate com a que o Playwright instalado espera — aí o launch() padrão
// falha pedindo `npx playwright install`. CHROMIUM_BIN, ou o link do ambiente, resolve.
function opcoesDoNavegador() {
  const fs = require('fs');
  for (const c of [process.env.CHROMIUM_BIN, '/opt/pw-browsers/chromium']) {
    if (c && fs.existsSync(c)) return { executablePath: c };
  }
  return {};
}

function arg(nome, padrao) {
  const i = process.argv.indexOf(nome);
  return i > -1 && process.argv[i + 1] ? process.argv[i + 1] : padrao;
}

// Power BI expõe a tabela com papéis ARIA padrão (role=grid/row/columnheader/gridcell) e
// numera as linhas em aria-rowindex. É por isso que a extração não depende de classes CSS
// internas, que a Microsoft troca sem aviso.
// ACHADO DA RODADA 1 (23/09/2026): a primeira versão fazia querySelector e pegava a PRIMEIRA
// grade da página. O Power BI desenha vários visuais, cada um podendo ser role=grid — e o
// primeiro não era a tabela dos municípios. Resultado: 20 linhas lidas, nenhuma casando com o
// IBGE. Agora enumeramos TODAS as grades, pontuamos e escolhemos a certa; as candidatas
// descartadas vão no diagnóstico, para que uma escolha errada seja visível em vez de silenciosa.
async function extrairGrade(page, alvoLinhas) {
  return await page.evaluate((alvo) => {
    // A pontuação roda DENTRO da página: aqui não existe nada do Node.
    const pontuar = (g) => {
      const cab = [...g.querySelectorAll('[role="columnheader"]')]
        .map(e => (e.innerText || e.getAttribute('aria-label') || '').toLowerCase());
      const linhas = [...g.querySelectorAll('[role="row"]')]
        .filter(tr => tr.querySelector('[role="gridcell"], [role="cell"]')).length;
      let p = 0;
      // Cabeçalho que nomeia município é o sinal mais forte de ser a tabela certa.
      if (cab.some(c => /munic[íi]pio/.test(c))) p += 100;
      if (cab.some(c => /calha|ano|plano/.test(c))) p += 20;
      const declarado = Number(g.getAttribute('aria-rowcount')) || 0;
      // Proximidade do total esperado, por linhas no DOM ou por aria-rowcount (virtualizada).
      const melhor = Math.max(linhas, declarado);
      p += melhor >= alvo ? 50 : Math.round(50 * (melhor / alvo));
      return { pontos: p, cabecalho: cab, linhas, aria_rowcount: declarado || null };
    };
    const grades = [...document.querySelectorAll('div[role="grid"], div[role="table"]')];
    if (!grades.length) return { achou: false, candidatas: [] };
    const pontuadas = grades.map((g, i) => ({ i, g, ...pontuar(g) }));
    pontuadas.sort((a, b) => b.pontos - a.pontos);
    const candidatas = pontuadas.map(x => ({ indice: x.i, pontos: x.pontos,
      cabecalho: x.cabecalho.slice(0, 6), linhas: x.linhas, aria_rowcount: x.aria_rowcount }));
    const grade = pontuadas[0].g;
    if (!grade) return { achou: false, candidatas };
    // Marca a escolhida para que o lado Node consiga rolar ESTA grade, e não a página.
    for (const g of grades) g.removeAttribute('data-mare-grade');
    grade.setAttribute('data-mare-grade', '1');
    const cab = [...grade.querySelectorAll('[role="columnheader"]')]
      .map(e => (e.innerText || e.getAttribute('aria-label') || '').replace(/\s+/g, ' ').trim())
      .filter(Boolean);
    const linhas = [];
    for (const tr of grade.querySelectorAll('[role="row"]')) {
      const cels = [...tr.querySelectorAll('[role="gridcell"], [role="cell"]')];
      if (!cels.length) continue;                       // linha de cabeçalho
      const idx = tr.getAttribute('aria-rowindex');
      const valores = cels.map(c => (c.innerText || c.getAttribute('title') || '')
        .replace(/\s+/g, ' ').trim());
      // O ícone de link pode ser um <a href> de verdade (coluna do tipo Web URL) ou apenas
      // uma imagem clicável (coluna com ação), caso em que não há URL no DOM.
      const a = tr.querySelector('a[href]');
      linhas.push({
        aria_rowindex: idx ? Number(idx) : null,
        valores,
        href: a ? a.getAttribute('href') : null,
        tem_icone_clicavel: !!tr.querySelector('img, [role="button"], [class*="icon" i]'),
      });
    }
    return { achou: true, cabecalho: cab, linhas, candidatas,
             aria_rowcount: grade.getAttribute('aria-rowcount') };
  }, alvoLinhas);
}

// ACHADO DA RODADA REAL (23/09/2026): a versão anterior rolava com page.mouse.wheel sem
// nunca mover o cursor, isto é, na posição (0,0) — fora da grade. O Power BI só rola o
// visual sob o ponteiro, então a roda caía no vazio e a leitura parava nas 20 primeiras
// linhas de 62. O aviso de "leitura parcial" saiu certo; a causa é que não houve rolagem
// nenhuma. Três estratégias, da mais confiável para a mais frágil, e a que funcionou fica
// declarada no diagnóstico — rolagem que para de funcionar precisa ser visível, não muda.
async function rolarGrade(page) {
  const sel = '[data-mare-grade="1"]';
  // 1. scrollTop no contêiner que de fato rola (o visual do Power BI usa um filho próprio).
  const porCodigo = await page.evaluate((s) => {
    const g = document.querySelector(s);
    if (!g) return false;
    const cands = [g, ...g.querySelectorAll('*')];
    for (const c of cands) {
      if (c.scrollHeight - c.clientHeight > 8) {
        const antes = c.scrollTop;
        c.scrollTop = antes + Math.max(200, c.clientHeight - 40);
        if (c.scrollTop !== antes) return true;
      }
    }
    return false;
  }, sel).catch(() => false);
  if (porCodigo) return 'scrollTop';

  // 2. roda do mouse COM o ponteiro sobre a grade — o que faltava antes.
  const caixa = await page.locator(sel).first().boundingBox().catch(() => null);
  if (caixa) {
    await page.mouse.move(caixa.x + caixa.width / 2, caixa.y + caixa.height / 2);
    await page.mouse.wheel(0, 600);
    return 'wheel-sobre-a-grade';
  }

  // 3. último recurso: evento de roda sintético na própria grade.
  const sintetico = await page.evaluate((s) => {
    const g = document.querySelector(s);
    if (!g) return false;
    g.dispatchEvent(new WheelEvent('wheel', { deltaY: 600, bubbles: true }));
    return true;
  }, sel).catch(() => false);
  return sintetico ? 'wheel-sintetico' : 'sem-rolagem';
}

// A grade do Power BI é virtualizada: só as linhas visíveis existem no DOM. Rola até o
// número de linhas distintas parar de crescer (ou bater o teto), acumulando por rowindex.
async function extrairTudoRolando(page) {
  const porIndice = new Map();
  let cabecalho = [], rowcount = null, semGanho = 0, candidatas = [];
  const estrategias = [];
  for (let i = 0; i < MAX_ROLAGENS; i++) {
    const g = await extrairGrade(page, ALVO_LINHAS);
    if (!g.achou) return { achou: false, candidatas: g.candidatas || [] };
    if (g.cabecalho && g.cabecalho.length) cabecalho = g.cabecalho;
    if (g.candidatas) candidatas = g.candidatas;
    if (g.aria_rowcount) rowcount = Number(g.aria_rowcount);
    const antes = porIndice.size;
    for (const l of g.linhas) {
      const chave = l.aria_rowindex != null ? `i${l.aria_rowindex}` : `v${l.valores.join('|')}`;
      if (!porIndice.has(chave)) porIndice.set(chave, l);
    }
    if (porIndice.size === antes) { if (++semGanho >= 3) break; } else semGanho = 0;
    // aria-rowcount CONTA O CABEÇALHO: 63 para 62 municípios. Descontá-lo é o que faz esta
    // parada disparar; sem isso a leitura sempre ia até o teto de rolagens.
    if (rowcount && porIndice.size >= rowcount - 1) break;
    const como = await rolarGrade(page);
    estrategias.push(como);
    await page.waitForTimeout(700);
  }
  const linhas = [...porIndice.values()].sort(
    (a, b) => (a.aria_rowindex ?? 1e9) - (b.aria_rowindex ?? 1e9));
  return { achou: true, cabecalho, linhas, aria_rowcount: rowcount, candidatas,
           rolagem: { tentativas: estrategias.length, estrategias } };
}

(async () => {
  const url = process.argv[2];
  const espera = Number(arg('--espera-ms', '15000'));
  const htmlPara = arg('--html-para', null);
  const saida = { ok: false, url, lido_em: new Date().toISOString().slice(0, 10),
                  colunas: [], linhas: [], n_linhas: 0, diagnostico: {}, erro: null };
  if (!url) { saida.erro = 'uso: node scripts/renderizar_painel_am.js <url>'; console.log(JSON.stringify(saida)); process.exit(2); }

  let navegador = null;
  try {
    navegador = await chromium.launch(opcoesDoNavegador());
    const ctx = await navegador.newContext({
      userAgent: process.env.MONITOR_UA || 'MonitorElNinoBrasil/2.2.4 (+https://monitorelnino.com.br)',
      locale: 'pt-BR',
    });
    const page = await ctx.newPage();
    const erros = [];
    page.on('pageerror', e => erros.push(String(e).slice(0, 200)));

    const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    saida.diagnostico.http = resp ? resp.status() : null;
    // Power BI não atinge networkidle (telemetria contínua): espera declarada, não heurística.
    await page.waitForTimeout(espera);
    try { await page.waitForSelector('div[role="grid"], div[role="table"]', { timeout: 20000 }); } catch { /* tratado abaixo */ }

    const g = await extrairTudoRolando(page);
    if (!g.achou) {
      saida.erro = 'grade não encontrada no DOM renderizado (role=grid/table ausente)';
      saida.diagnostico.texto_visivel = (await page.innerText('body').catch(() => '')).replace(/\s+/g, ' ').slice(0, 400);
    } else {
      saida.colunas = g.cabecalho;
      saida.diagnostico.aria_rowcount = g.aria_rowcount;
      // Toda grade da página, com a nota que recebeu: uma escolha errada fica visível.
      saida.diagnostico.grades_candidatas = g.candidatas;
      saida.diagnostico.rolagem = g.rolagem;
      for (const l of g.linhas) {
        const celulas = {};
        g.cabecalho.forEach((c, i) => { celulas[c] = l.valores[i] ?? null; });
        if (!g.cabecalho.length) l.valores.forEach((v, i) => { celulas[`col_${i}`] = v; });
        saida.linhas.push({
          indice: l.aria_rowindex,
          celulas,
          valores: l.valores,
          url_do_link: l.href,
          // Declarado: por que temos (ou não temos) a URL desta linha.
          como_obtido: l.href ? 'href na própria célula'
            : (l.tem_icone_clicavel ? 'ícone sem href — URL não obtida sem clique' : 'sem link na linha'),
        });
      }
      saida.n_linhas = saida.linhas.length;
      saida.ok = saida.n_linhas > 0;
      if (saida.n_linhas && saida.n_linhas < ALVO_LINHAS) {
        saida.diagnostico.aviso = `apenas ${saida.n_linhas} de ${ALVO_LINHAS} linhas esperadas — `
          + 'rolagem pode não ter alcançado o fim da grade; tratar como leitura parcial';
      }
    }
    if (erros.length) saida.diagnostico.pageerrors = erros.slice(0, 3);
    if (htmlPara) require('fs').writeFileSync(htmlPara, await page.content(), 'utf-8');
  } catch (e) {
    saida.erro = `${e.name}: ${String(e.message).slice(0, 300)}`;
  } finally {
    if (navegador) await navegador.close().catch(() => {});
  }
  console.log(JSON.stringify(saida));
  process.exit(saida.ok ? 0 : 1);
})();
