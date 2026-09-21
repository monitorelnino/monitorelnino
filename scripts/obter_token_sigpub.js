#!/usr/bin/env node
/* obter_token_sigpub.js — §129/§130: o token do widget de calendário do SIGPub
 * (diariomunicipal.com.br) é preenchido por JavaScript (controller Stimulus
 * "csrf-protection"); o HTML servido traz só um placeholder estático (verificado
 * contra produção em 20/09/2026). Este script abre a página num Chromium real
 * (mesmo padrão de scripts/verificar_movel.js), espera o JS preencher o valor
 * real (por POLLING, não uma espera fixa — 20/09/2026: 800ms fixo não foi
 * suficiente contra produção real; o mecanismo pode ser assíncrono) e devolve
 * token + cookies da sessão em JSON, para o coletor Python
 * (coletar_diarios_consorciados.py) reusar em requisições HTTP normais depois —
 * não precisa de navegador para o resto do fluxo (POST do calendário, PDF).
 *
 * USO: node scripts/obter_token_sigpub.js <url-base-do-slug>
 * SAÍDA (stdout, uma linha JSON): {"ok":true,"token":"...","cookies":[...]}
 *                              ou {"ok":false,"erro":"...", "diagnostico": {...}}
 * Nunca lança — erro sempre vira JSON com ok:false, para o chamador Python
 * decidir (lacuna declarada), nunca um traceback quebrando o subprocess. */
const { chromium } = require("playwright");
const PLACEHOLDER = "csrf-token";
const POLL_MS = 400, TIMEOUT_TOKEN_MS = 12000;

(async () => {
  const url = process.argv[2];
  if (!url) { console.log(JSON.stringify({ ok: false, erro: "uso: obter_token_sigpub.js <url>" })); process.exit(1); }
  let b;
  const consoleMsgs = [], pageErrors = [];
  try {
    b = await chromium.launch();
    const ctx = await b.newContext();
    const page = await ctx.newPage();
    page.on("console", m => { if (m.type() === "error") consoleMsgs.push(m.text().slice(0, 200)); });
    page.on("pageerror", e => pageErrors.push(String(e.message || e).slice(0, 200)));
    await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
    // Polling em vez de espera fixa (achado 20/09/2026: 800ms não bastou contra produção real —
    // o mecanismo que preenche o token pode ser assíncrono, ex. uma chamada de rede própria).
    const inicio = Date.now();
    let token = null, tentativas = 0;
    while (Date.now() - inicio < TIMEOUT_TOKEN_MS) {
      tentativas++;
      token = await page.evaluate(() => {
        const el = document.querySelector("#calendar__token");
        return el ? el.value : null;
      });
      if (token && token !== PLACEHOLDER) break;
      await page.waitForTimeout(POLL_MS);
    }
    const cookies = await ctx.cookies();
    const tempo_ms = Date.now() - inicio;
    await b.close();
    if (!token) {
      console.log(JSON.stringify({ ok: false, erro: "input #calendar__token não encontrado na página renderizada",
        diagnostico: { tentativas, tempo_ms, console_erros: consoleMsgs.slice(0, 5), erros_pagina: pageErrors.slice(0, 5) } }));
      process.exit(1);
    }
    if (token === PLACEHOLDER) {
      console.log(JSON.stringify({ ok: false,
        erro: `token ainda é o placeholder ('${PLACEHOLDER}') após ${tempo_ms}ms / ${tentativas} tentativas — JS não preencheu a tempo, ou o mecanismo mudou`,
        diagnostico: { tentativas, tempo_ms, console_erros: consoleMsgs.slice(0, 5), erros_pagina: pageErrors.slice(0, 5) } }));
      process.exit(1);
    }
    console.log(JSON.stringify({ ok: true, token, cookies, diagnostico: { tentativas, tempo_ms } }));
  } catch (e) {
    if (b) await b.close().catch(() => {});
    console.log(JSON.stringify({ ok: false, erro: `${e.name}: ${e.message}`.slice(0, 300),
      diagnostico: { console_erros: consoleMsgs.slice(0, 5), erros_pagina: pageErrors.slice(0, 5) } }));
  }
})();
