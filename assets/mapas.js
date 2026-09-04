/* ============================================================
   assets/mapas.js — motor único de mapas, legendas e tooltips (v2.3, 03/09/2026)
   Toda página com mapa usa ESTE módulo. Nenhuma página define localmente
   desenharMapa / addSiglas / showTip / legenda (portão verificar_estrutura.js).
   Regras visuais fixas: viewBox 480×460, contorno .uf-path (base.css), siglas das
   27 UFs sobre todo mapa, legenda <span><i style="background:…"></i>rótulo</span>,
   tooltip #mapTooltip, crédito de figura dentro do parágrafo-nota único do cartão.
   Depende de d3 (carregado pela página) e de assets/base.css.
   ============================================================ */
(function (global) {
  'use strict';
  const NEUTRA = '#DCD3C2';
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const tooltipEl = () => document.getElementById('mapTooltip');
  function showTip(html, evt) {
    const t = tooltipEl(); if (!t) return;
    t.innerHTML = html; t.style.display = 'block';
    t.style.left = ((evt && evt.clientX) || 0) + 14 + 'px'; t.style.top = ((evt && evt.clientY) || 0) + 10 + 'px';
  }
  function hideTip() { const t = tooltipEl(); if (t) t.style.display = 'none'; }

  /** Contexto de projeção compartilhado por todos os mapas de uma página. */
  function contexto(geo, w, h) {
    const projection = d3.geoMercator().fitSize([w || 480, h || 460], geo);
    return { geo, projection, path: d3.geoPath().projection(projection), w: w || 480, h: h || 460 };
  }

  /** Coroplético por UF: corDe(uf) → cor; rotuloDe(uf) → HTML do tooltip. Sempre com siglas. */
  function ufs(ctx, svgId, corDe, rotuloDe) {
    const svg = d3.select('#' + svgId);
    svg.selectAll('g.ufs').remove(); svg.selectAll('g.siglas').remove();
    const g = svg.append('g').attr('class', 'ufs');
    g.selectAll('path').data(ctx.geo.features).join('path').attr('d', ctx.path).attr('class', 'uf-path')
      .attr('fill', d => corDe(d.properties.sigla) || NEUTRA).attr('tabindex', 0).attr('role', 'img')
      .attr('aria-label', d => d.properties.name + ': ' + String(rotuloDe(d.properties.sigla) || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim())
      .on('mouseenter', (evt, d) => showTip('<strong>' + esc(d.properties.name) + '</strong><br>' + rotuloDe(d.properties.sigla), evt))
      .on('mousemove', (evt, d) => showTip('<strong>' + esc(d.properties.name) + '</strong><br>' + rotuloDe(d.properties.sigla), evt))
      .on('focus', (evt, d) => showTip('<strong>' + esc(d.properties.name) + '</strong><br>' + rotuloDe(d.properties.sigla), { clientX: 24, clientY: 24 }))
      .on('mouseleave', hideTip).on('blur', hideTip);
    siglas(ctx, svg);
    return svg;
  }

  /** Siglas das 27 UFs — sempre por cima das camadas de área, abaixo dos pontos. */
  function siglas(ctx, svg) {
    svg.selectAll('g.siglas').remove();
    svg.append('g').attr('class', 'siglas').selectAll('text').data(ctx.geo.features).join('text')
      .attr('x', d => ctx.path.centroid(d)[0]).attr('y', d => ctx.path.centroid(d)[1])
      .attr('text-anchor', 'middle').attr('dominant-baseline', 'middle')
      .attr('font-family', "'Archivo Narrow', 'Arial Narrow', Arial, sans-serif").attr('font-size', 11).attr('font-weight', 600)
      .attr('fill', '#2E3D30').attr('paint-order', 'stroke').attr('stroke', '#F5F1E8').attr('stroke-width', 2.6).attr('stroke-opacity', .75)
      .style('pointer-events', 'none').text(d => d.properties.sigla);
  }

  /** Camada de pontos (lat/lon). opts: r(d), cor(d), rotulo(d), classe, opacidade. */
  function pontos(ctx, svgId, itens, opts) {
    const o = Object.assign({ r: () => 3, cor: () => '#7C4A34', rotulo: null, classe: 'pontos', opacidade: .85 }, opts || {});
    const svg = d3.select('#' + svgId); svg.selectAll('g.' + o.classe).remove();
    const g = svg.append('g').attr('class', o.classe);
    const sel = g.selectAll('circle').data(itens.filter(d => d.lat != null && d.lon != null)).join('circle')
      .attr('cx', d => ctx.projection([d.lon, d.lat])[0]).attr('cy', d => ctx.projection([d.lon, d.lat])[1])
      .attr('r', d => o.r(d)).attr('fill', d => o.cor(d)).attr('fill-opacity', o.opacidade).attr('stroke', '#F5F1E8').attr('stroke-width', .6);
    if (o.rotulo) sel.on('mouseenter', (evt, d) => showTip(o.rotulo(d), evt)).on('mousemove', (evt, d) => showTip(o.rotulo(d), evt)).on('mouseleave', hideTip);
    svg.selectAll('g.siglas').raise(); g.raise();
    return g;
  }

  /** Camada densa (milhares de pontos) num único <path> — barata de renderizar. */
  function pontosDensos(ctx, svgId, itens, cor, largura, opacidade) {
    const svg = d3.select('#' + svgId); svg.selectAll('path.densos').remove();
    const d = itens.filter(p => p.lat != null && p.lon != null).map(p => { const c = ctx.projection([p.lon, p.lat]); return 'M' + c[0].toFixed(1) + ' ' + c[1].toFixed(1) + 'h0'; }).join('');
    svg.append('path').attr('class', 'densos').attr('d', d).attr('stroke', cor).attr('stroke-width', largura || 1.4).attr('stroke-linecap', 'round').attr('stroke-opacity', opacidade || .55).attr('fill', 'none');
    svg.selectAll('g.siglas').raise();
  }

  /** Legenda canônica: itens [{cor, rotulo}] → <span><i></i>rótulo</span>. */
  function legenda(elId, itens) {
    const el = document.getElementById(elId); if (!el) return;
    el.innerHTML = itens.map(i => '<span><i style="background:' + i.cor + (i.opacidade != null ? ';opacity:' + i.opacidade : '') + '"></i>' + esc(i.rotulo) + '</span>').join('');
  }

  /** Escala contínua canônica (gradiente) + itens discretos opcionais. */
  function legendaContinua(elId, gradiente, rotuloMin, rotuloMax, itens) {
    const el = document.getElementById(elId); if (!el) return;
    el.innerHTML = '<span class="escala" style="flex-basis:100%; max-width:360px; display:block;">'
      + '<i style="display:block; width:100%; height:12px; border-radius:6px; border:1px solid #CDBB9F; background:' + gradiente + '"></i>'
      + '<em style="display:flex; justify-content:space-between; font-style:normal; font-size:12.5px; color:var(--muted); margin-top:3px;"><span>' + esc(rotuloMin) + '</span><span>' + esc(rotuloMax) + '</span></em></span>'
      + (itens || []).map(i => '<span><i style="background:' + i.cor + '"></i>' + esc(i.rotulo) + '</span>').join('');
  }

  /** Crédito de figura (04/09/2026, decisão editorial): UMA linha curta ao pé do cartão —
   *  "Fonte: … · data". Sem explicação, sem instrução, sem "por que está vazio". Figuras trazem
   *  título, legenda e este crédito; nada mais. O portão verificar_figuras.js garante isso. */
  function credito(caixaId, texto) {
    const caixa = document.getElementById(caixaId);
    if (!caixa || caixa.querySelector('.fonte-figura')) return;
    const d = document.createElement('div'); d.className = 'fonte-figura'; d.innerHTML = texto; caixa.appendChild(d);
  }

  /** Padrão único dos gráficos Chart.js (03/09/2026): tipografia, cores, grade, tooltip. */
  function padraoGraficos(Chart) {
    if (!Chart || !Chart.defaults) return;
    Chart.defaults.color = '#55645B';                      // --muted
    Chart.defaults.font.family = "'Archivo', system-ui, -apple-system, 'Segoe UI', sans-serif";
    Chart.defaults.font.size = 11.5;
    Chart.defaults.borderColor = '#D6C4AC';                // --line (grade)
    if (!Chart.defaults.font) Chart.defaults.font = {};
    if (Chart.defaults.plugins && Chart.defaults.plugins.legend && Chart.defaults.plugins.legend.labels) { Chart.defaults.plugins.legend.labels.boxWidth = 10; Chart.defaults.plugins.legend.labels.padding = 10; }
    if (Chart.defaults.plugins && Chart.defaults.plugins.tooltip) { const t = Chart.defaults.plugins.tooltip; t.backgroundColor = '#15201A'; t.titleFont = { family: "'Archivo', sans-serif", weight: '600' }; t.bodyFont = { family: "'Archivo', sans-serif" }; t.cornerRadius = 6; t.padding = 8; }
    const el = Chart.defaults.elements || {};
    if (el.bar) el.bar.borderRadius = 3; if (el.line) el.line.borderWidth = 2; if (el.point) el.point.radius = 2.5;
    Chart.defaults.maintainAspectRatio = false;
  }
  /** Paleta ordinal e categórica do site (tokens), para uso nos gráficos. */
  const PALETA = { status: { NOVO: '#35566B', READ: '#6E8CA0', ELAB: '#9FB6C6', VIG: '#C69B72', LAC: '#A65F3F', NAO_VERIFICADO: '#64645C' },
                   resposta: '#7C4A34', preparacao: '#35566B', neutra: '#DCD3C2', serie: ['#35566B', '#5E7C93', '#C69B72', '#A65F3F', '#87855C', '#647A7E', '#4F7D48', '#7A6A4F'] };

  global.MonitorMapas = { padraoGraficos, PALETA, NEUTRA, esc, showTip, hideTip, contexto, ufs, siglas, pontos, pontosDensos, legenda, legendaContinua, credito };
})(window);
