// ===== pesquisadores.html · bloco 1 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
window.addEventListener('load', function(){ if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} } });

// ===== pesquisadores.html · bloco 2 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
let DATA, TRANSFERENCIAS, META, TABELA_MUNICIPIOS, SINAIS;
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
async function __load(){
  [DATA, TRANSFERENCIAS, META, TABELA_MUNICIPIOS, SINAIS] = await Promise.all(['estados','transferencias','meta','municipios','sinais_risco'].map(f => fetch('data/' + f + '.json').then(r => { if(!r.ok) throw new Error('Falha ao carregar data/' + f + '.json'); return r.json(); })));
document.getElementById('fontesMonitoramento').innerHTML = TRANSFERENCIAS.fontes_monitoramento
  .map(f => `<li><a href="${esc(f.url)}" target="_blank" rel="noopener">${esc(f.nome)}</a></li>`).join('');
  const ROTULO_HOST = {
  'www.diariomunicipal.com.br': 'Diários Oficiais dos Municípios (FAMUP/FEMURN/AMA/FAMEP/Sergipe)',
  'acaoinverno.recife.pe.gov.br': 'Ação Inverno · Prefeitura do Recife',
  'www.defesacivil.sc.gov.br': 'Defesa Civil de Santa Catarina',
  'defesacivil.es.gov.br': 'CEPDEC/ES — repositório estadual de planos de contingência',
  'www.gov.br': 'Portais gov.br (MIDR/SEDEC e órgãos federais)',
};
const porFonte = new Map();
TABELA_MUNICIPIOS.filter(m => m.url).forEach(m => {
  const host = new URL(m.url).hostname;
  // subcaminhos do diariomunicipal distinguem federações; demais domínios agrupam pelo host
  const chave = host === 'www.diariomunicipal.com.br' ? host + '/' + (new URL(m.url).pathname.split('/')[1] || '') : host;
  const g = porFonte.get(chave) || {host, urls: [], n: 0};
  g.urls.push(m.url); g.n++;
  porFonte.set(chave, g);
});
document.getElementById('fontesVerificadas').innerHTML =
  [...porFonte.values()]
    .map(g => {
      const nome = ROTULO_HOST[g.host] || g.host;
      const href = g.urls.sort((a,b)=>a.length-b.length)[0]; // o link mais raiz do domínio
      return {nome, href, n: g.n};
    })
    .sort((a,b)=>b.n - a.n || a.nome.localeCompare(b.nome))
    .map(f => `<li><a href="${f.href}" target="_blank" rel="noopener">${f.nome}</a> <span style="color:var(--muted);">· ${f.n} registro${f.n > 1 ? 's' : ''}</span></li>`).join('');
document.getElementById('fontesFederaisCount').textContent = document.querySelectorAll('#fontesFederais li').length;

function renderTable(){
    const q = document.getElementById('tblSearch').value.toLowerCase();
    const cat = document.getElementById('tblCat').value;
    const rows = TABELA_MUNICIPIOS
      .filter(m => (!cat || m.categoria===cat) &&
        (!q || m.nome.toLowerCase().includes(q) || m.uf.toLowerCase().includes(q)))
      .sort((a,b)=> a.uf.localeCompare(b.uf) || a.nome.localeCompare(b.nome));
    document.getElementById('tblBody').innerHTML = rows.map(m=>{
      const [lbl,cor] = CAT_LABEL_TBL[m.categoria];
      const fonte = m.url ? `<a href="${esc(m.url)}" target="_blank" rel="noopener">${esc(m.fonte)}</a>` : esc(m.fonte);
      return `<tr><td><strong>${m.nome}</strong></td><td>${m.uf}</td>
        <td><span class="cat-pill" style="background:${cor}">${lbl}</span></td>
        <td>${m.documento}</td><td style="white-space:nowrap;">${m.data}</td><td>${fonte}</td><td style="white-space:nowrap; font-family:'Archivo Narrow', 'Arial Narrow', Arial, sans-serif; font-size:12.5px; color:var(--muted);">${m.canal||'—'}</td></tr>`;
    }).join('');
  }
  document.getElementById('tblSearch').addEventListener('input', renderTable);
  document.getElementById('tblCat').addEventListener('change', renderTable);
  renderTable();
  
  const CAT_LABEL_TBL = {
    plano:['Plano preventivo',MonitorMapas.cor('musgo')], plano_antigo:['Plano desatualizado',MonitorMapas.cor('sintetico')],
    plano_elaboracao:['Em elaboração',MonitorMapas.cor('ambar')], estrutura:['Estrutura de coordenação',MonitorMapas.cor('ambar')], decreto:['Decreto reativo',MonitorMapas.cor('argila')],
    coberto_estadual:['Coberto pelo estado',MonitorMapas.cor('mineral')], nao_el_nino:['Não é El Niño',MonitorMapas.cor('areia')],
    nao_localizado:['Nada localizado',MonitorMapas.cor('argila')],
    nao_verificado:['Ainda não verificado',MonitorMapas.cor('cinza-quente')],
  };
  
  (document.getElementById('munCount')||{}).textContent = TABELA_MUNICIPIOS.length;
  if (document.querySelector('#tblFontes tbody') && SINAIS && SINAIS.fontes) {
  document.querySelector('#tblFontes tbody').innerHTML = Object.entries(SINAIS.fontes).map(([id, f]) => {
    const situacao = f.status === 'coletado'
      ? '<strong>Coletada</strong> em ' + esc(f.consultado_em) + '<br><span class="note">' + esc(f.documento || '') + '</span>'
      : '<span class="note fonte-espera">Não localizamos coleta até o corte</span>';
    return '<tr><td><a href="' + esc(f.url_publica) + '" target="_blank" rel="noopener">' + esc(f.nome) + '</a><br>' +
      '<span class="note">Camada: ' + esc(CAMADA_ROTULO[f.camada]) + '</span></td><td>' + esc(f.orgao) + '</td><td>' +
      esc(f.papel) + '</td><td>' + situacao + '</td></tr>';
  }).join('');
  }
  { const fm = document.getElementById('fontesMonit'); if (fm) fm.innerHTML = (TRANSFERENCIAS.fontes_monitoramento || []).map(f => '<li><a href="' + esc(f.url) + '" target="_blank" rel="noopener">' + esc(f.nome) + '</a></li>').join(''); }
  const el = id => document.getElementById(id);
  el('pqCorte').textContent = META.corte || '—'; el('pqAtualizado').textContent = META.atualizado_em || '—';
  fetch('data/log_buscas.json').then(r => r.ok ? r.json() : null).then(l => { if (!(l && l.execucoes)) return; el('pqLog').textContent = l.execucoes.length.toLocaleString('pt-BR');
    const ult = l.execucoes.reduce((a, e) => e.data > a ? e.data : a, ''); const c = {}; l.execucoes.filter(e => e.data === ult).forEach(e => { c[e.canal] = (c[e.canal] || 0) + 1; });
    el('pqCanais').textContent = ult + ' — ' + Object.entries(c).sort((a, b) => b[1] - a[1]).map(([k, v]) => k + ' ' + v).join(' · '); });
  fetch('data/verificacao_resumo.json').then(r => r.ok ? r.json() : null).then(v => { if (!(v && v.por_uf)) return;
    document.querySelector('#tblLog tbody').innerHTML = Object.keys(v.por_uf).sort().map(uf => { const n = v.por_uf[uf]; return '<tr><td><strong>' + esc(uf) + '</strong></td><td>' + (n.nacional || 0) + '</td><td>' + (n.estadual || 0) + '</td><td>' + (n.municipal_parcial || 0) + '</td><td>' + (n.municipal_completo || 0) + '</td><td>' + (n.nao_verificado || 0) + '</td></tr>'; }).join(''); });
  fetch('data/cobertura_qd.json').then(r => r.ok ? r.json() : null).then(c => { const m = (c && c.municipios) || {}; const t = Object.values(m); el('pqCobertura').textContent = t.length ? t.filter(x => x.cobertura_qd === true).length + ' indexados · ' + t.filter(x => x.cobertura_qd === false).length + ' não indexados · ' + (5571 - t.length) + ' ainda não testados' : 'ainda não testada (a rotina preenche a partir da próxima rodada)'; });
  fetch('data/calendario/fontes_suspensas.json').then(r => r.ok ? r.json() : null).then(f => { const n = f ? Object.values(f.fontes || {}).filter(x => x.suspensa).length : 0; el('pqSuspensas').textContent = n + ' fonte(s) suspensa(s) detectada(s)'; });
}
__load().catch(err => { document.body.insertAdjacentHTML('afterbegin', '<div style="background:var(--argila);color:#fff;padding:14px 20px;">Erro ao carregar os dados: ' + err.message + '</div>'); });

// ===== pesquisadores.html · bloco 3 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
window.addEventListener('load', function(){ if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} } });
