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
  const NEUTRA = '#DCE3E2';
  // v3.1 §14.2 (06/09/2026): hex só aqui e em tokens.css. Páginas usam var(--nome) em CSS/estilo
  // inline e MonitorMapas.cor('nome') onde precisam de um valor concreto (canvas do Chart.js).
  const COR = { vazio:'#0E0F0D', abissal:'#15201A', musgo:'#2E3D30', argila:'#7C4A34', ambar:'#C9814B', bioluz:'#A8C99A',
                sintetico:'#5E7C93', mineral:'#8FA5A8', areia:'#D6C4AC', 'osso-claro':'#F0F4F3', linha:'#C5CFCE',
                'cinza-quente':'#66736F', 'sem-dado':'#DCE3E2', branco:'#FFFFFF', 'areia-escura':'#7A6A4F', zebra:'#E9EEEC',
                muted:'#55645B', 'gauge-trilho':'#E7DECD', 'gauge-borda':'#CDBB9F', 'gauge-osso':'#F5F1E8', 'gauge-cinza':'#DDDED9',
                'ambar-escuro':'#A87A50', 'sintetico-escuro':'#2A4457', preto:'#000000' };
  function cor(nome) { return COR[nome] || nome; }
  /** Relógio de prazo (07/09/2026): anel que esvazia de data_base a vencimento. resta ∈ [0,1]; dias < 0 = vencido.
   *  Devolve o SVG (string). Cor: Âmbar > 30 % restante; Argila abaixo de 30 %; Mineral apagado quando vencido. */
  function relogio(resta, dias, opts) {
    const o = Object.assign({ tam: 88, espessura: 9, cor: null }, opts || {});
    const r = (o.tam - o.espessura) / 2, c = 2 * Math.PI * r, vencido = dias < 0;
    const f = vencido ? 0 : Math.max(0, Math.min(1, resta));
    const corAnel = o.cor || (vencido ? COR.mineral : f < 0.3 ? COR.argila : COR.ambar);
    const num = vencido ? Math.abs(dias) : dias, rot = vencido ? 'dias<tspan> </tspan>atrás' : dias === 0 ? 'hoje' : dias === 1 ? 'dia' : 'dias';
    return '<svg class="relogio" viewBox="0 0 ' + o.tam + ' ' + o.tam + '" width="' + o.tam + '" height="' + o.tam + '" role="img" aria-label="' + (vencido ? 'transcorrido há ' + Math.abs(dias) + ' dia(s)' : Math.round(f * 100) + '% do prazo restante, ' + dias + ' dia(s)') + '">'
      + '<circle cx="' + o.tam / 2 + '" cy="' + o.tam / 2 + '" r="' + r + '" fill="none" stroke="' + COR['sem-dado'] + '" stroke-width="' + o.espessura + '"/>'
      + '<circle cx="' + o.tam / 2 + '" cy="' + o.tam / 2 + '" r="' + r + '" fill="none" stroke="' + corAnel + '" stroke-width="' + o.espessura + '" stroke-linecap="butt" stroke-dasharray="' + (c * f).toFixed(1) + ' ' + c.toFixed(1) + '" transform="rotate(-90 ' + o.tam / 2 + ' ' + o.tam / 2 + ')"' + (vencido ? ' opacity=".55"' : '') + '/>'
      + '<text x="' + o.tam / 2 + '" y="' + (o.tam / 2 + 2) + '" text-anchor="middle" font-family="Fraunces, Georgia, serif" font-size="' + (o.tam >= 88 ? 28 : 22) + '" fill="' + (vencido ? COR.mineral : COR.vazio) + '">' + num + '</text>'
      + '<text x="' + o.tam / 2 + '" y="' + (o.tam / 2 + o.tam * 0.2) + '" text-anchor="middle" font-family="Archivo Narrow, Arial Narrow, Arial, sans-serif" font-size="12" fill="' + COR.muted + '" letter-spacing=".06em">' + rot.toUpperCase().replace('<TSPAN> </TSPAN>', ' ') + '</text></svg>';
  }   // tema técnico (05/09/2026): 'sem dado' em areia-clara sobre branco
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
      .attr('font-family', "'Archivo Narrow', 'Arial Narrow', Arial, sans-serif").attr('font-size', 12).attr('font-weight', 600)
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
    el.innerHTML = '<span class="escala">'
      + '<i style="background:' + gradiente + '"></i>'
      + '<em><span>' + esc(rotuloMin) + '</span><span>' + esc(rotuloMax) + '</span></em></span>'
      + (itens || []).map(i => '<span><i style="background:' + i.cor + '"></i>' + esc(i.rotulo) + '</span>').join('');
  }

  /** Data no formato único do site (dd/mm/aaaa). Aceita dd/mm/aaaa (com hora ou texto ao redor), aaaa-mm-dd e Date. */
  function dataBR(v) {
    if (!v) return null;
    if (v instanceof Date) return String(v.getDate()).padStart(2, '0') + '/' + String(v.getMonth() + 1).padStart(2, '0') + '/' + v.getFullYear();
    const s = String(v); let m = s.match(/(\d{2})\/(\d{2})\/(\d{4})/); if (m) return m[1] + '/' + m[2] + '/' + m[3];
    m = s.match(/(\d{4})-(\d{2})-(\d{2})/); if (m) return m[3] + '/' + m[2] + '/' + m[1];
    return null;
  }
  /** Crédito de figura — formato ÚNICO do site (auditoria de 07/09/2026):
   *    "Fonte: órgão · documento · Atualização: dd/mm/aaaa"   ou   "… · Atualização: sem coleta até o corte".
   *  credito(caixaId, { fontes: 'INMET' | ['DOU', 'S2iD'], data: '07/09/2026' | null, url: 'https://…' (opcional, no 1º nome) })
   *  Sem explicações, sem instruções, sem "por que está vazio". Uma linha por figura ou cartão; nunca duplica.
   *  Portões: verificar_figuras.js (texto) e verificar_consistencia_visual.js (estilo computado). */
  function credito(caixaId, spec) {
    const caixa = document.getElementById(caixaId);
    if (!caixa || caixa.querySelector('.fonte-figura')) return;
    if (typeof spec === 'string') throw new Error('MonitorMapas.credito: use {fontes, data}; texto livre não é aceito (' + caixaId + ')');
    const fontes = (Array.isArray(spec.fontes) ? spec.fontes : [spec.fontes]).filter(Boolean).map(esc);
    if (spec.url && fontes.length) fontes[0] = '<a href="' + esc(spec.url) + '" target="_blank" rel="noopener">' + fontes[0] + '</a>';
    const data = dataBR(spec.data);
    const d = document.createElement('div'); d.className = 'fonte-figura';
    d.innerHTML = '<span class="fonte-k">Fonte:</span> ' + fontes.join(' · ') + ' · <span class="fonte-k">Atualização:</span> ' + (data || 'sem coleta até o corte');
    let pe = caixa.querySelector(':scope > .figura-pe');
    if (!pe) { pe = document.createElement('div'); pe.className = 'figura-pe'; caixa.appendChild(pe); }
    pe.insertBefore(d, pe.firstChild);   // crédito antes do número da figura
  }

  /** Padrão único dos gráficos Chart.js (03/09/2026): tipografia, cores, grade, tooltip. */
  function padraoGraficos(Chart) {
    if (!Chart || !Chart.defaults) return;
    Chart.defaults.color = '#55645B';                      // --muted
    Chart.defaults.font.family = "'Archivo', system-ui, -apple-system, 'Segoe UI', sans-serif";
    Chart.defaults.font.size = 12;                          // --fs-caption
    Chart.defaults.borderColor = '#D6C4AC';                // --line (grade)
    if (!Chart.defaults.font) Chart.defaults.font = {};
    if (Chart.defaults.plugins && Chart.defaults.plugins.legend && Chart.defaults.plugins.legend.labels) { Chart.defaults.plugins.legend.labels.boxWidth = 10; Chart.defaults.plugins.legend.labels.padding = 10; }
    if (Chart.defaults.plugins && Chart.defaults.plugins.tooltip) { const t = Chart.defaults.plugins.tooltip; t.backgroundColor = '#15201A'; t.titleFont = { family: "'Archivo', sans-serif", weight: '600' }; t.bodyFont = { family: "'Archivo', sans-serif" }; t.cornerRadius = 6; t.padding = 8; }
    const el = Chart.defaults.elements || {};
    if (el.bar) el.bar.borderRadius = 3; if (el.line) el.line.borderWidth = 2; if (el.point) el.point.radius = 2.5;
    Chart.defaults.maintainAspectRatio = false;
  }
  /** PALETA SEMÂNTICA ÚNICA (auditoria de 09/09/2026): toda figura do site colore o MESMO significado com a MESMA
   *  cor, em qualquer página. As páginas leem daqui; nenhuma define mapa próprio de significado → cor
   *  (portão verificar_estrutura.js). Regras: verde Musgo = preparação/publicado; Sintético = frio de dado;
   *  Âmbar/Argila = calor de dado, resposta e perigo; Mineral = intermediário/recorrente; Areia = neutro/sem sinal;
   *  cinza-quente = ainda não verificado; sem-dado = fonte não coletada. */
  const PALETA = {
    // faixas do MARÉ (e da prontidão sanitária): fundo e cor do texto da pílula
    faixas: { inicial: COR.argila, construcao: COR.ambar, consolidado: COR.sintetico, avancado: COR.musgo, nao_verificado: COR['cinza-quente'] },
    faixasTexto: { inicial: COR.branco, construcao: COR.abissal, consolidado: COR.branco, avancado: COR.branco, nao_verificado: COR.branco },
    faixaDe: v => v == null ? 'nao_verificado' : v < 25 ? 'inicial' : v < 50 ? 'construcao' : v < 70 ? 'consolidado' : 'avancado',
    faixaRotulo: { inicial: 'Estágio inicial', construcao: 'Em construção', consolidado: 'Consolidado', avancado: 'Avançado', nao_verificado: 'Ainda não verificado' },
    // status do instrumento estadual (defesa civil e saúde) e das capitais
    status: { NOVO: COR.musgo, READ: COR.sintetico, ELAB: COR.ambar, VIG: COR.mineral, LAC: COR.argila, NAO_VERIFICADO: COR['cinza-quente'] },
    // categoria do ato municipal (mapa de pontos, tabelas, cartão da cidade)
    categorias: { plano: COR.musgo, plano_antigo: COR.sintetico, plano_elaboracao: COR.ambar, estrutura: COR.ambar, decreto: COR.argila,
                  coberto_estadual: COR.mineral, nao_el_nino: COR.areia, nao_localizado: COR.argila, nao_verificado: COR['cinza-quente'] },
    // nível de verificação municipal
    verificacao: { nao_verificado: COR['cinza-quente'], nacional: COR.mineral, estadual: COR.sintetico, municipal_completo: COR.musgo, fonte_suspensa: COR.argila },
    // famílias de risco do ciclo — a tríade de tokens.css (--chuva, --seca, --fogo) vale em todas as páginas
    risco: { chuvas: COR.sintetico, seca: COR.ambar, fogo: COR.argila, multi: COR['areia-escura'], sem_sinal: COR.areia },
    // consistência risco × instrumento (mapa 5 da Defesa civil)
    consistencia: { COBRE: COR.musgo, PARCIAL: COR.mineral, DIFERE: COR.argila, SEM: COR.argila, NEUTRO: COR.areia },
    // ENOS
    enso: { el_nino: COR.argila, neutro: COR.areia, la_nina: COR.sintetico },
    // antecipação × resposta (índice × contador); defeso
    preparacao: COR.musgo, resposta: COR.argila, defeso: COR.argila, antes_defeso: COR.ambar,
    // rampas contínuas: perigo/intensidade (quente) e preparação/cobertura (verde)
    rampaPerigo: [COR['osso-claro'], COR.argila], rampaPreparo: [COR.zebra, COR.musgo],
    // ordinal de 4 degraus para intensidade (dengue 1–4, calor 1–3+, quartis de valor pago): do mais brando ao mais grave
    ordinal4: [COR.mineral, COR.ambar, COR['ambar-escuro'], COR.argila],
    // séries por ano (o ano corrente sempre em Argila)
    anos: { '2026': COR.argila, '2025': COR.ambar, '2024': COR.mineral, canal: COR.musgo, p75: COR.ambar, p90: COR.sintetico },
    // rotas do dinheiro (Financiamento): família da chave de acesso — regra em frios, decreto em quentes,
    // discricionária em âmbar/areia, execução direta em mineral, rota estadual em musgo. Oito cores distintas.
    // chave de acesso das rotas (legenda da rede) e temas dos compromissos federais
    chaves: { regra: COR.sintetico, decreto: COR.argila, discricionaria: COR.ambar, direta: COR.mineral, estadual: COR.musgo },
    temas: { hidrico: COR.sintetico, fogo: COR.argila, alimentar: COR.ambar, saude: COR.mineral, outro: COR.areia },
    rotas: { r1: COR['sintetico-escuro'], r2: COR.sintetico, r3: COR.argila, r4: COR['ambar-escuro'], r5: COR.ambar, r6: COR['areia-escura'], r7: COR.mineral, rE: COR.musgo },
    neutra: NEUTRA, semDado: COR['sem-dado'], zero: COR.zebra,
    serie: [COR.musgo, COR.sintetico, COR.ambar, COR.argila, COR.mineral, COR['areia-escura'], COR.bioluz, COR.muted] };

  global.MonitorMapas = { padraoGraficos, PALETA, NEUTRA, COR, cor, relogio, esc, showTip, hideTip, contexto, ufs, siglas, pontos, pontosDensos, legenda, legendaContinua, credito, dataBR };
})(window);
