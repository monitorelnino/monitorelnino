// Auditoria de CONTEÚDO dos relatórios em PDF: cada registro de municipios.json,
// cada emergência de atos_resposta.json e cada estado precisam aparecer no PDF
// com categoria, documento, fonte, status e capital certos. Use: python3 scripts/auditar_pdfs.py
const { chromium } = require('playwright');
const mun = require('../data/municipios.json'), atos = require('../data/atos_resposta.json').eventos;
const est = require('../data/estados.json').ufs, indice = require('../data/indice.json'), fin = require('../data/financiamento_uf.json');
const CAT = {plano:'Plano preventivo', plano_antigo:'Plano desatualizado', plano_elaboracao:'Em elaboração', decreto:'Decreto reativo', coberto_estadual:'Coberto pelo estado', nao_el_nino:'Não é El Niño', nao_localizado:'verificado individualmente', nao_verificado:'Ainda não verificado'};
const FRASE_STATUS = {LAC:'O estado ainda não publicou plano estadual', ELAB:'está em elaboração e ainda não foi publicado', VIG:'não menciona o El Niño 2026/2027'};
(async () => {
  const b = await chromium.launch(); const page = await (await b.newContext()).newPage(); page.on('dialog', d => d.dismiss());
  await page.goto('file:///tmp/index_pdf_test.html', { waitUntil: 'networkidle', timeout: 20000 }); await page.waitForTimeout(1200);
  const gerar = async (uf, m) => (await page.evaluate(({u, m}) => { window.__out = null; window.__gerar(u, m); return window.__out.text; }, {u: uf, m})).replace(/\s+/g, ' ');
  const probs = [];
  // 265 registros municipais
  for (const m of mun) { const t = await gerar(m.uf, m.nome);
    if (!t.includes(CAT[m.categoria])) probs.push([m.nome + '/' + m.uf, 'categoria ausente: ' + CAT[m.categoria]]);
    if (!['nao_localizado','nao_verificado'].includes(m.categoria) && m.documento && m.documento !== '—' && !t.includes(m.documento.slice(0, 40).replace(/\s+/g,' '))) probs.push([m.nome + '/' + m.uf, 'documento ausente']);
    if (!['nao_localizado','nao_verificado'].includes(m.categoria) && m.fonte && m.fonte !== '—' && !t.includes(m.fonte.slice(0, 25).replace(/\s+/g,' '))) probs.push([m.nome + '/' + m.uf, 'fonte ausente']); }
  // 5 emergências
  for (const e of atos) { const t = await gerar(e.uf, e.nome);
    if (!t.includes(e.nome + ' decretou situação de emergência em ' + e.data)) probs.push([e.nome + '/' + e.uf, 'emergência ausente']); }
  // 27 estados: status, capital, financiamento, DF
  for (const d of est) { const t = await gerar(d.uf, null); const st = indice[d.uf].status_estadual;
    if (FRASE_STATUS[st] && !t.includes(FRASE_STATUS[st])) probs.push(['estado ' + d.uf, 'frase de status ausente: ' + st]);
    if (st !== 'LAC' && d.doc && !t.includes(d.doc.slice(0, 40).replace(/\s+/g,' '))) probs.push(['estado ' + d.uf, 'documento estadual ausente']);
    if (d.capital && !t.includes('Capital (' + d.capital.nome + ')')) probs.push(['estado ' + d.uf, 'capital ausente']);
    if (fin[d.uf] && fin[d.uf].status === 'localizado' && !t.includes('Recurso preventivo estadual')) probs.push(['estado ' + d.uf, 'financiamento ausente']);
    if (!/Risco projetado para [^.]+ neste ciclo .{8,}/.test(t)) probs.push(['estado ' + d.uf, 'risco vazio']); }
  const df = await gerar('DF', null); console.log('DF, cobertura:', (df.match(/Municípios do estado[^\n]+/) || ['?'])[0]);
  const ce = mun.find(m => m.categoria === 'coberto_estadual'); if (ce) { const t = await gerar(ce.uf, ce.nome); console.log('coberto_estadual (' + ce.nome + '/' + ce.uf + '):', (t.match(/Sua cidade está coberta[^\n]+/) || ['FALTA'])[0].slice(0, 120)); }
  console.log('\nproblemas de conteúdo:', probs.length); probs.slice(0, 20).forEach(p => console.log('  ', p.join(' :: ')));
  await b.close();
})();
