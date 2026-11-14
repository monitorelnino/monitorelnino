// Sonda (não grava em data/): que chamadas a plataforma do MapBiomas faz para mostrar estatística de fogo e de água.
const { chromium } = require('playwright');
const UA = 'MonitorElNinoBrasil/2.2.4 (+https://monitorelnino.com.br; contato@monitorelnino.com.br)';
const PAGINAS = ['https://plataforma.brasil.mapbiomas.org/', 'https://plataforma.brasil.mapbiomas.org/fire/fire_monthly',
  'https://plataforma.brasil.mapbiomas.org/fire', 'https://plataforma.brasil.mapbiomas.org/water/water_water_surface',
  'https://plataforma.monitordofogo.mapbiomas.org/', 'https://monitordofogo.mapbiomas.org/'];
(async () => {
  const b = await chromium.launch(); const ctx = await b.newContext({ userAgent: UA });
  for (const url of PAGINAS) {
    const p = await ctx.newPage(); const vistos = [];
    p.on('response', async r => { const u = r.url(); if (/google|gtag|fonts|\.png|\.svg|\.woff|\.css|tile|\.pbf|\.jpg/i.test(u)) return;
      const ct = r.headers()['content-type'] || ''; let amostra = '';
      if (/json|graphql/.test(ct)) { try { amostra = (await r.text()).slice(0, 300); } catch (e) {} }
      vistos.push(`${r.status()} ${r.request().method()} ${u.slice(0, 220)} ${ct.slice(0, 30)} ${amostra.replace(/\s+/g, ' ')}`); });
    try { await p.goto(url, { waitUntil: 'networkidle', timeout: 45000 }); } catch (e) { vistos.push('goto: ' + e.message.slice(0, 80)); }
    await p.waitForTimeout(4000);
    const post = []; p.on('request', q => { if (q.method() === 'POST') post.push(q.url() + ' ' + (q.postData() || '').slice(0, 400)); });
    console.log('=== ' + url + ' → ' + p.url() + ' · ' + (await p.title()));
    vistos.filter(v => !/\.js |text\/javascript|text\/html/.test(v)).slice(0, 40).forEach(v => console.log('  ' + v));
    const js = vistos.filter(v => /\.js /.test(v)).map(v => v.split(' ')[2]); console.log('  js: ' + js.slice(0, 6).join(' '));
    await p.close();
  }
  await b.close();
})();
