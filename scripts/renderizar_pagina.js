// Renderizador genérico de página oficial (§185, 23/09/2026).
//
// POR QUE EXISTE. O §164 descobriu a falha de CAMADA: evidência publicada atrás de JavaScript é
// invisível para busca textual. O §165 resolveu isso para o painel Power BI do AM, com um extrator
// de grade ARIA. Mas a classe é maior que painel: o portal da Defesa Civil do MT é Liferay e
// responde "Este site precisa que o seu navegador tenha JAVASCRIPT ativo" — a página de documentos
// existe, os links existem, e o cliente HTTP recebe só o esqueleto. Sem navegador real, o Monitor
// registraria "nada localizado" onde há documento publicado.
//
// DIVISÃO DE TRABALHO, a mesma do §165: aqui só se RENDERIZA e se listam os links e o texto que a
// página mostra. Quem decide o que é plano, baixa, preserva evidência e lê o ato é o lado Python,
// com as travas do projeto. Este arquivo não escreve em data/ nem decide nada.
//
// IDENTIFICAÇÃO. O User-Agent é o do projeto, com o endereço público e o contato — nunca disfarçado
// de navegador comum nem de Googlebot (§185). O sítio sabe quem está lendo.
//
// SAÍDA: um JSON em stdout — { ok, url, http, titulo, texto, links[{href,texto}], n_links, erro }
//
// Uso: node scripts/renderizar_pagina.js <url> [--espera-ms N] [--html-para <arquivo>]
const fs = require('fs');
const { chromium } = require('playwright');

const UA = 'MonitorElNinoBrasil/2.2.4 (+https://monitorelnino.com.br; contato@monitorelnino.com.br)';

function executavelDoChromium() {
  // Mesma tolerância do renderizador do AM: ambientes diferentes guardam o Chromium em lugares
  // diferentes, e falhar por caminho é pior do que tentar o padrão do Playwright.
  for (const p of [process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE, process.env.CHROME_BIN]) {
    if (p && fs.existsSync(p)) return p;
  }
  return undefined;
}

(async () => {
  const url = process.argv[2];
  const i = process.argv.indexOf('--espera-ms');
  const espera = i > 0 ? Number(process.argv[i + 1]) : 3500;
  const j = process.argv.indexOf('--html-para');
  const htmlPara = j > 0 ? process.argv[j + 1] : null;
  const saida = { ok: false, url, http: null, titulo: null, texto: null, links: [], n_links: 0, erro: null };
  if (!url) { saida.erro = 'uso: renderizar_pagina.js <url>'; console.log(JSON.stringify(saida)); process.exit(1); }

  let navegador;
  try {
    navegador = await chromium.launch({ executablePath: executavelDoChromium() });
    const contexto = await navegador.newContext({ userAgent: UA, locale: 'pt-BR' });
    const pagina = await contexto.newPage();
    const resposta = await pagina.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
    saida.http = resposta ? resposta.status() : null;
    await pagina.waitForTimeout(espera);

    saida.titulo = (await pagina.title() || '').trim().slice(0, 200);
    saida.texto = (await pagina.evaluate(() => document.body ? document.body.innerText : ''))
      .replace(/\s+/g, ' ').trim().slice(0, 20000);
    saida.links = await pagina.evaluate(() => Array.from(document.querySelectorAll('a[href]'))
      .map((a) => ({ href: a.href, texto: (a.innerText || a.title || '').replace(/\s+/g, ' ').trim().slice(0, 200) }))
      .filter((l) => l.href && l.href.startsWith('http')));
    saida.n_links = saida.links.length;
    saida.ok = true;
    if (htmlPara) fs.writeFileSync(htmlPara, await pagina.content(), 'utf-8');
  } catch (e) {
    saida.erro = `${e.name}: ${String(e.message).slice(0, 300)}`;
  } finally {
    if (navegador) await navegador.close().catch(() => {});
  }
  console.log(JSON.stringify(saida));
  process.exit(saida.ok ? 0 : 1);
})();
