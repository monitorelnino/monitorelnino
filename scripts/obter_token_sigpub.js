#!/usr/bin/env node
/* obter_token_sigpub.js — §129/§130: o token do widget de calendário do SIGPub
 * (diariomunicipal.com.br) é preenchido por JavaScript (controller Stimulus
 * "csrf-protection"); o HTML servido traz só um placeholder estático (verificado
 * contra produção em 20/09/2026). Este script abre a página num Chromium real
 * (mesmo padrão de scripts/verificar_movel.js), espera o JS preencher o valor
 * real e devolve token + cookies da sessão em JSON, para o coletor Python
 * (coletar_diarios_consorciados.py) reusar em requisições HTTP normais depois —
 * não precisa de navegador para o resto do fluxo (POST do calendário, PDF).
 *
 * USO: node scripts/obter_token_sigpub.js <url-base-do-slug>
 * SAÍDA (stdout, uma linha JSON): {"ok":true,"token":"...","cookies":[...]}
 *                              ou {"ok":false,"erro":"..."}
 * Nunca lança — erro sempre vira JSON com ok:false, para o chamador Python
 * decidir (lacuna declarada), nunca um traceback quebrando o subprocess. */
const { chromium } = require("playwright");
const PLACEHOLDER = "csrf-token";

(async () => {
  const url = process.argv[2];
  if (!url) { console.log(JSON.stringify({ ok: false, erro: "uso: obter_token_sigpub.js <url>" })); process.exit(1); }
  let b;
  try {
    b = await chromium.launch();
    const ctx = await b.newContext();
    const page = await ctx.newPage();
    await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
    // O controller Stimulus roda no carregamento; espera curta de segurança além do networkidle
    // (mesmo padrão de folga usado em verificar_movel.js para JS assíncrono).
    await page.waitForTimeout(800);
    const token = await page.evaluate(() => {
      const el = document.querySelector("#calendar__token");
      return el ? el.value : null;
    });
    const cookies = await ctx.cookies();
    await b.close();
    if (!token) {
      console.log(JSON.stringify({ ok: false, erro: "input #calendar__token não encontrado na página renderizada" }));
      process.exit(1);
    }
    if (token === PLACEHOLDER) {
      console.log(JSON.stringify({ ok: false, erro: `token ainda é o placeholder ('${PLACEHOLDER}') após espera — JS não preencheu a tempo, ou o mecanismo mudou` }));
      process.exit(1);
    }
    console.log(JSON.stringify({ ok: true, token, cookies }));
  } catch (e) {
    if (b) await b.close().catch(() => {});
    console.log(JSON.stringify({ ok: false, erro: `${e.name}: ${e.message}`.slice(0, 300) }));
    process.exit(1);
  }
})();
