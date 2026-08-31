// Auditoria de GERAÇÃO dos relatórios em PDF do cidadão: gera, em memória, os 27
// estados + todos os municípios do IBGE e confere cada um (exceções, seções,
// texto ruim, caracteres fora do WinAnsi, páginas, largura do título).
// Não roda no CI (precisa de navegador + jsPDF local); use: python3 scripts/auditar_pdfs.py
const { chromium } = require('playwright'); const fs = require('fs');
const ref = require('../data/municipios_ibge_referencia.json');
const ufs = [...new Set(ref.map(m => m.uf))].sort();
const SEC = ["Em emergência, ligue","Risco projetado para","O que já existe","O que ainda falta","Pedido de informação pronto","Como se proteger","Links úteis"];
const RUIM = [/undefined/, /\bnull\b/, /\bNaN\b/, /— — \(—\)/, /\[object/, /tel:\+/, /\d\.\d+\s*(?:%|\/100)/];
// caracteres fora do WinAnsi (o que o helvetica embutido do jsPDF sabe desenhar)
const foraWinAnsi = s => [...s].filter(c => { const k = c.codePointAt(0); return k > 255 && !"–—‘’“”…•€".includes(c); });
(async () => {
  const b = await chromium.launch(); const page = await (await b.newContext()).newPage();
  const jsErr = []; page.on('pageerror', e => jsErr.push(e.message)); page.on('dialog', d => { jsErr.push('ALERT ' + d.message()); d.dismiss(); });
  await page.goto('file:///tmp/index_pdf_test.html', { waitUntil: 'networkidle', timeout: 20000 }); await page.waitForTimeout(1200);
  const problemas = []; let n = 0; const paginas = {};
  const checa = (rot, out, titulo) => {
    if (!out) { problemas.push([rot, 'NÃO GEROU (save não chamado)']); return; }
    paginas[out.pages] = (paginas[out.pages] || 0) + 1;
    SEC.forEach(s => { if (!out.text.includes(s)) problemas.push([rot, 'falta seção: ' + s]); });
    RUIM.forEach(r => { const m = out.text.match(r); if (m) problemas.push([rot, 'texto ruim: ' + m[0]]); });
    const fw = foraWinAnsi(out.text); if (fw.length) problemas.push([rot, 'caracteres fora do WinAnsi: ' + [...new Set(fw)].join(' ')]);
    if (out.pages < 2 || out.pages > 4) problemas.push([rot, 'páginas: ' + out.pages]);
    if (titulo && !out.text.includes(titulo)) problemas.push([rot, 'título ausente no PDF']);
  };
  for (const uf of ufs) {
    const out = await page.evaluate(u => { window.__out = null; try { window.__gerar(u, null); } catch(e) { return {erro: e.message}; } return window.__out; }, uf);
    if (out && out.erro) problemas.push(['estado ' + uf, 'EXCEÇÃO: ' + out.erro]); else checa('estado ' + uf, out, null); n++;
  }
  const larguras = [];
  for (const uf of ufs) {
    const lista = ref.filter(m => m.uf === uf);
    const res = await page.evaluate(({u, nomes}) => nomes.map(nome => { window.__out = null; try { window.__gerar(u, nome); } catch(e) { return {nome, erro: e.message}; }
      const o = window.__out; return o ? {nome, pages: o.pages, text: o.text, w: window.__larguraTitulo(nome + ' · ' + u)} : {nome, erro: 'save não chamado'}; }), {u: uf, nomes: lista.map(m => m.nome)});
    for (const r of res) { n++; if (r.erro) { problemas.push([r.nome + '/' + uf, 'EXCEÇÃO: ' + r.erro]); continue; }
      checa(r.nome + '/' + uf, r, r.nome + ' · ' + uf); if (r.w > 491) larguras.push([r.nome + '/' + uf, Math.round(r.w)]); }
    process.stdout.write(uf + ':' + lista.length + ' ');
  }
  console.log('\n\ngerados:', n, '| páginas:', JSON.stringify(paginas), '| erros JS de página:', jsErr.length);
  console.log('títulos mais largos que a página (>491pt):', larguras.length, larguras.slice(0, 8));
  const porTipo = {}; problemas.forEach(([r, p]) => { const k = p.split(':')[0]; porTipo[k] = (porTipo[k] || 0) + 1; });
  console.log('problemas:', problemas.length, porTipo);
  fs.writeFileSync('/tmp/problemas_pdf.json', JSON.stringify(problemas, null, 1));
  console.log(problemas.slice(0, 15).map(p => p.join(' :: ')).join('\n'));
  await b.close();
})();
