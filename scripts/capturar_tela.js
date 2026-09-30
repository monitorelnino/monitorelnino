// Capturas de tela em desktop, tablet e mobile, para anexar ao PR.
// Uso: node capturar.js <url> <prefixo> [--seletor CSS] [--script "js"] [--espera N]
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const TAMANHOS = [
  ['desktop', 1440, 900],
  ['tablet', 768, 1024],
  ['mobile', 390, 844],
];

(async () => {
  const [url, prefixo] = process.argv.slice(2);
  const arg = (n, d) => {
    const i = process.argv.indexOf(n);
    return i > 0 ? process.argv[i + 1] : d;
  };
  const seletor = arg('--seletor', null);
  const script = arg('--script', null);
  const espera = Number(arg('--espera', 2500));
  const saida = arg('--saida', '.');
  fs.mkdirSync(saida, { recursive: true });

  const browser = await chromium.launch();
  const feitos = [];
  for (const [nome, w, h] of TAMANHOS) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h },
                                           deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 }).catch(() => {});
    await page.waitForTimeout(espera);
    if (script) { await page.evaluate(script); await page.waitForTimeout(1200); }
    const destino = path.join(saida, `${prefixo}-${nome}.png`);
    if (seletor) {
      const idx = Number(arg('--indice', 0));
      const todos = await page.$$(seletor);
      const el = todos[idx];
      if (el) { await el.scrollIntoViewIfNeeded(); await page.waitForTimeout(400);
                await el.screenshot({ path: destino }); }
      else { await page.screenshot({ path: destino, fullPage: false }); }
    } else {
      await page.screenshot({ path: destino, fullPage: false });
    }
    feitos.push(destino);
    await ctx.close();
  }
  await browser.close();
  console.log(feitos.join('\n'));
})();
