// Sonda de válvula (ramo coleta-dia/*, nunca mesclado): abre UMA página como navegador identificado
// e lista as requisições de rede (url, tipo, status, tamanho) para achar o arquivo de dados do mapa.
// Respeita robots.txt: recusa (disallow, 401/403/429/451, captcha) para sem contorno.
const { chromium } = require('playwright');
const url = process.argv[2];
const UA = 'Monitor El Nino Brasil (monitorelnino.com.br; contato@futuraevidencelab.com.br)';
(async () => {
  const u = new URL(url);
  const r = await fetch(u.origin + '/robots.txt', { headers: { 'User-Agent': UA } }).catch(() => null);
  const txt = r && r.ok ? await r.text() : '';
  console.log('robots', r ? r.status : 'sem resposta');
  let todos = false, bloqueia = false;
  for (const l of txt.split('\n')) {
    const m = l.split('#')[0].trim().match(/^(user-agent|disallow)\s*:\s*(.*)$/i);
    if (!m) continue;
    if (/user-agent/i.test(m[1])) todos = m[2].trim() === '*';
    else if (todos && m[2].trim() && u.pathname.startsWith(m[2].trim())) bloqueia = true;
  }
  if (bloqueia) { console.log('RECUSA robots.txt: parar'); return; }
  const b = await chromium.launch();
  const p = await (await b.newContext({ userAgent: UA })).newPage();
  const lin = [];
  p.on('response', async (x) => {
    const h = x.headers();
    lin.push([x.status(), x.request().resourceType(), h['content-type'] || '', h['content-length'] || '', x.url()]);
  });
  const resp = await p.goto(url, { waitUntil: 'networkidle', timeout: 90000 }).catch((e) => { console.log('erro', e.message); return null; });
  console.log('pagina', resp && resp.status());
  await p.waitForTimeout(8000);
  for (const l of lin) console.log('REQ', l.join(' | '));
  const txtp = (await p.innerText('body').catch(() => '')).slice(0, 600).replace(/\s+/g, ' ');
  console.log('corpo', txtp);
  await b.close();
})();
