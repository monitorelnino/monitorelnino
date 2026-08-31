// Auditoria de acessibilidade e responsividade (axe-core WCAG 2.1 AA + boas práticas) das 5
// páginas em 3 viewports (celular 375, tablet 768, desktop 1280): overflow horizontal,
// elementos mais largos que a tela, texto <12px, alvos de toque <24px, h1 único, ordem de
// títulos, ids duplicados, rel=noopener, alt/aria-label, lang, viewport, description.
// Não roda no CI (precisa de navegador); regras baratas viraram checagem (7) em
// verificar_estrutura.js. Pré-requisito: as páginas de teste em /tmp (ver auditar_pdfs.py).
// Uso: node scripts/auditar_ux.js
const { chromium } = require('playwright'); const { AxeBuilder } = require('@axe-core/playwright');
const PAGS = [['index','file:///tmp/index_pdf_test.html'],['mapas','file:///tmp/mapas_com_libs_embutidas.html'],['proteja-se','file:///home/claude/audit/pacote/proteja-se.html'],['envie-dados','file:///mnt/user-data/outputs/pagina_3_envie-dados.html'],['obrigado','file:///home/claude/audit/pacote/obrigado.html'],['para-gestores','file:///home/claude/audit/pacote/para-gestores.html']];
const VIEWS = [['celular',375,812],['tablet',768,1024],['desktop',1280,900]];
(async () => {
  const b = await chromium.launch(); const rel = {};
  for (const [nome, url] of PAGS) { rel[nome] = {};
    for (const [vn, w, h] of VIEWS) { const page = await (await b.newContext({ viewport: {width:w, height:h} })).newPage(); page.on('dialog', d => d.dismiss());
      await page.goto(url, { waitUntil: 'networkidle', timeout: 20000 }).catch(()=>{}); await page.waitForTimeout(1200);
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
      let axe = null; try { const r = await new AxeBuilder({ page }).withTags(['wcag2a','wcag2aa','wcag21aa','best-practice']).analyze(); axe = r.violations.map(v => ({ id: v.id, impact: v.impact, n: v.nodes.length, ex: v.nodes[0] && v.nodes[0].target.join(' ').slice(0,70) })); } catch(e) { axe = 'erro: ' + e.message.slice(0,80); }
      rel[nome][vn] = { ...m, axe }; await page.context().close();
    } }
  console.log(JSON.stringify(rel, null, 1)); await b.close();
})();
