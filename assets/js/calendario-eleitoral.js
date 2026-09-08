// ===== calendario-eleitoral.html · bloco 1 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
window.addEventListener('load', function(){ if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} } });

// ===== calendario-eleitoral.html · bloco 2 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
async function __load(){
  const el = id => document.getElementById(id);
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const D = await fetch('data/calendario/dispositivos.json').then(r => r.ok ? r.json() : null).catch(() => null);
  if (D) {
    el('calConferido').textContent = D.conferido_em;
    document.querySelector('#tblDispositivos tbody').innerHTML = D.dispositivos.map(x => '<tr><td><strong>' + esc(x.dispositivo) + '</strong></td><td>' + esc(x.bloqueia) + '</td><td>' + esc(x.excecao) + '</td><td>' + esc(x.significa) + '</td><td><details><summary>trecho</summary><p class="note">' + esc(x.trecho) + '</p><a href="' + esc(x.fonte) + '" target="_blank" rel="noopener">fonte lida</a></details></td></tr>').join('');
    el('listaNaoSuspenso').innerHTML = D.nao_suspenso.map(x => '<li><strong>' + esc(x.item) + '</strong> — ' + esc(x.base) + ' <span class="u-muted">(' + esc(x.status) + ')</span></li>').join('');
  }
  const f = await fetch('data/calendario/fontes_suspensas.json').then(r => r.ok ? r.json() : null).catch(() => null);
  const n = f ? Object.values(f.fontes || {}).filter(x => x.suspensa).length : 0;
  el('calSuspensas').textContent = n ? n + ' fonte(s), primeira detecção ' + Object.values(f.fontes).map(x => x.primeira_deteccao).sort()[0] : 'nenhuma detectada pelo robô até o corte (o detector passou a rodar em 06/09/2026; a página da SUDEC/BA foi achada à mão em 02/09)';
  { const fs = f ? Object.values(f.fontes || {}).filter(x => x.suspensa) : []; const por = {}; fs.forEach(x => { por[x.setor || 'defesa_civil'] = (por[x.setor || 'defesa_civil'] || 0) + 1; });
    el('calSetores').textContent = fs.length ? '(' + Object.entries(por).map(([k, v]) => ({defesa_civil: 'defesa civil', saude: 'saúde', financiamento: 'financiamento'}[k] || k) + ' ' + v).join(' · ') + ')' : '';
    const ms = f && Object.entries(f.fontes || {}).find(([u]) => /monitoramento-das-arboviroses/.test(u));
    el('calSaudeDefeso').textContent = ms ? 'painel epidemiológico federal (Painel das Arboviroses do MS) em edição de defeso desde ' + ms[1].primeira_deteccao.split('-').reverse().join('/') + (fs.filter(x => x.setor === 'saude').length > 1 ? ' · mais ' + (fs.filter(x => x.setor === 'saude').length - 1) + ' painel(is) estadual(is) indisponível(is)' : '') : 'nenhuma fonte de saúde suspensa detectada'; }
  const c = await fetch('data/cobertura_qd.json').then(r => r.ok ? r.json() : null).catch(() => null);
  const t = c ? Object.values(c.municipios || {}) : [];
  el('calSemCobertura').textContent = t.length ? t.filter(x => x.cobertura_qd === false).length + ' de ' + t.length + ' testados (' + (5571 - t.length) + ' ainda não testados)' : 'ainda não testado — a rotina preenche a partir da próxima rodada';
  const r = await fetch('data/resposta/serie_semanal.json').then(r => r.ok ? r.json() : null).catch(() => null);
  if (r) el('calDecretos').textContent = r.semanas.filter(s => s.defeso).reduce((a, s) => a + s.municipios, 0) + ' municípios com primeiro decreto entre 04/07 e o corte';
}
__load().catch(err => { document.body.insertAdjacentHTML('afterbegin', '<div class="erro-carga">Erro ao carregar os dados: ' + err.message + '</div>'); });

// ===== calendario-eleitoral.html · bloco 3 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
window.addEventListener('load', function(){ if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} } });
