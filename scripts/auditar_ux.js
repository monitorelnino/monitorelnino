// Auditoria de acessibilidade e responsividade (axe-core WCAG 2.1 AA + boas práticas) das páginas
// do site em 3 viewports (celular 375, tablet 768, desktop 1280): overflow horizontal, elementos
// mais largos que a tela, texto <12px, alvos de toque <24px, h1 único, ordem de títulos, ids
// duplicados, rel=noopener, alt/aria-label, lang, viewport, description.
// Não roda no CI (precisa de navegador); regras baratas viraram checagem (7) em
// verificar_estrutura.js.
//
// §237 (26/09/2026): este auditor existia e estava ÓRFÃO. A lista de páginas apontava para
// caminhos de sessões antigas — /tmp/index_pdf_test.html, /home/claude/audit/pacote/…,
// /mnt/user-data/outputs/… — que não existem em máquina nenhuma hoje. Ele rodava e não auditava
// nada. Agora a lista é DERIVADA dos *.html da raiz, como `validar_workflows.py` já faz, e por isso
// página nova entra sozinha; e ele passou a GRAVAR CAPTURA, porque a pergunta que a editoria faz é
// "como ficou", e relatório de axe-core não responde isso.
//
// As páginas são servidas por HTTP, não abertas por file://: elas buscam data/*.json ao vivo, e em
// file:// o navegador recusa esse fetch — a auditoria mediria uma página sem dado nenhum.
//
// Uso: node scripts/auditar_ux.js [pagina...]        (sem argumento: todas)
//   BASE=http://127.0.0.1:8788   endereço do servidor local (padrão)
//   SEM_CAPTURA=1                só o relatório, sem gravar PNG
//
// O axe-core é OPCIONAL: se `@axe-core/playwright` não estiver instalado, a auditoria roda sem
// ele e diz isso no campo `axe`. As medições próprias (rolagem, largura, texto minúsculo, alvo
// de toque, títulos, ids, alt, lang) e as capturas não dependem dele.
const { chromium } = require('playwright');
// §237: `@axe-core/playwright` NUNCA foi declarado no package.json — é a segunda razão pela qual
// este auditor ficou órfão: quem o escreveu tinha o pacote no ambiente, e ele nunca entrou no
// projeto. Não acrescento dependência que ninguém pediu; o axe entra se estiver instalado e a
// auditoria diz quando não está. O contraste, que é o que mais importa numa troca de cor, já é
// conferido por `scripts/verificar_acessibilidade.js`, que está no perfil `cor --rapido`.
let AxeBuilder = null;
try { AxeBuilder = require('@axe-core/playwright').AxeBuilder; } catch (e) { AxeBuilder = null; }
const fs = require('fs'); const path = require('path');
const RAIZ = path.resolve(__dirname, '..');
const BASE = (process.env.BASE || 'http://127.0.0.1:8788').replace(/\/$/, '');
const PREVIA = path.join(RAIZ, 'previa');
const CAPTURA = process.env.SEM_CAPTURA !== '1';
// Lista DERIVADA da raiz, como validar_workflows.py: página nova entra sozinha, e nenhuma lista
// escrita à mão envelhece aqui.
const pedidas = process.argv.slice(2).map(a => a.replace(/\.html$/, ''));
const PAGS = fs.readdirSync(RAIZ).filter(f => f.endsWith('.html'))
  .map(f => [f.replace(/\.html$/, ''), `${BASE}/${f}`])
  .filter(([nome]) => !pedidas.length || pedidas.includes(nome));
// A captura fica nas duas larguras que o checklist da marca nomeia; a auditoria segue nas três.
const VIEWS = [['celular',375,812],['tablet',768,1024],['desktop',1280,900]];
const LARGURAS_DE_CAPTURA = new Set(['celular','desktop']);
(async () => {
  if (!PAGS.length) { console.error('nenhuma página casou com o pedido: ' + pedidas.join(' ')); process.exit(2); }
  if (CAPTURA) fs.mkdirSync(PREVIA, { recursive: true });
  const b = await chromium.launch(); const rel = {}; const capturas = [];
  for (const [nome, url] of PAGS) { rel[nome] = {};
    for (const [vn, w, h] of VIEWS) { const page = await (await b.newContext({ viewport: {width:w, height:h} })).newPage(); page.on('dialog', d => d.dismiss());
      let resp = null;
      try { resp = await page.goto(url, { waitUntil: 'networkidle', timeout: 20000 }); } catch (e) { resp = null; }
      if (!resp || !resp.ok()) {
        // Falha de carregamento NÃO vira relatório limpo: auditar uma página que não abriu diria
        // "sem problema" sobre nada. Diz o que houve e para.
        console.error(`✗ ${nome} (${vn}): a página não carregou em ${url}` +
          (resp ? ` — HTTP ${resp.status()}` : ' — sem resposta') +
          `\n  O servidor local está de pé? python3 -m http.server 8788 --bind 127.0.0.1`);
        await page.context().close(); await b.close(); process.exit(1);
      }
      await page.waitForTimeout(1200);
      const m = await page.evaluate(() => {
        const vw = window.innerWidth; const doc = document.documentElement;
        const overflowX = doc.scrollWidth > vw + 1;
        const largos = [...document.querySelectorAll('body *')].filter(el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.right > vw + 2 && getComputedStyle(el).position !== 'fixed'; }).slice(0,5).map(el => el.tagName.toLowerCase() + (el.id ? '#'+el.id : '') + (el.className && typeof el.className==='string' ? '.'+el.className.split(' ')[0] : '') + ' ' + Math.round(el.getBoundingClientRect().right - vw) + 'px');
        const pequenos = [...document.querySelectorAll('body *')].filter(el => { if (!el.childNodes.length) return false; const tx = [...el.childNodes].some(n => n.nodeType===3 && n.textContent.trim()); if (!tx) return false; const fs = parseFloat(getComputedStyle(el).fontSize); const r = el.getBoundingClientRect(); return fs < 12 && r.width > 0 && r.height > 0; }).map(el => (el.className && typeof el.className==='string' ? '.'+el.className.split(' ')[0] : el.tagName.toLowerCase()) + ':' + getComputedStyle(el).fontSize);
        const toques = [...document.querySelectorAll('a[href], button, input, select, summary')].filter(el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && (r.height < 24 || r.width < 24) && getComputedStyle(el).display !== 'inline'; }).length;
        const h1 = document.querySelectorAll('h1').length; const hs = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].map(h => +h.tagName[1]); let pulo = 0; for (let i=1;i<hs.length;i++) if (hs[i] > hs[i-1]+1) pulo++;
        const ids = [...document.querySelectorAll('[id]')].map(e=>e.id); const dupIds = ids.filter((v,i)=>ids.indexOf(v)!==i);
        return { overflowX, largos, pequenos: [...new Set(pequenos)].slice(0,8), nPequenos: pequenos.length, toques, h1, pulo, dupIds: [...new Set(dupIds)], lang: doc.lang, viewportMeta: !!document.querySelector('meta[name=viewport]'), descricao: !!document.querySelector('meta[name=description]'), semNoopener: [...document.querySelectorAll('a[target=_blank]')].filter(a => !/noopener/.test(a.rel)).length, imgSemAlt: [...document.querySelectorAll('img')].filter(i => !i.hasAttribute('alt')).length, svgSemLabel: [...document.querySelectorAll('svg[role=img]')].filter(s => !s.getAttribute('aria-label')).length };
      });
      let axe = null;
      if (!AxeBuilder) { axe = 'nao_instalado: @axe-core/playwright ausente (npm i -D @axe-core/playwright para ligar)'; }
      else { try { const r = await new AxeBuilder({ page }).withTags(['wcag2a','wcag2aa','wcag21aa','best-practice']).analyze(); axe = r.violations.map(v => ({ id: v.id, impact: v.impact, n: v.nodes.length, ex: v.nodes[0] && v.nodes[0].target.join(' ').slice(0,70) })); } catch(e) { axe = 'erro: ' + e.message.slice(0,80); } }
      if (CAPTURA && LARGURAS_DE_CAPTURA.has(vn)) {
        const arq = path.join(PREVIA, `${nome}-${vn}.png`);
        await page.screenshot({ path: arq, fullPage: true });
        capturas.push(path.relative(RAIZ, arq).replace(/\\/g, '/'));
      }
      rel[nome][vn] = { ...m, axe }; await page.context().close();
    } }
  console.log(JSON.stringify(rel, null, 1));
  if (capturas.length) console.error(`\n${capturas.length} captura(s) em previa/: ${capturas.join(', ')}`);
  await b.close();
})();
