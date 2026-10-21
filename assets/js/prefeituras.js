/* ===== prefeituras.html · "Para gestores" (reforma de 17/10/2026, HANDOVER_GESTORES_16-10-2026) =====
 * A consulta é o módulo comum (`ConsultaMunicipio`); o cartão junta, por código IBGE, o que os
 * arquivos de origem já guardam: listas federais (enquadramento_card), risco previsto do boletim
 * (sinais_risco), transferências da União e do FNS e a despesa própria na rubrica de defesa civil.
 * Nada é recalculado nem classificado aqui; ausência é a frase da classe, nunca zero nem vazio.
 * O plano do município sai de `municipios_card.json` pela classificação comum
 * (`ConsultaMunicipio.situacaoDoPlano`, a mesma da inicial). */
function _erroGest(onde) { return function (e) { try { console.error('[MARÉ] falha em ' + onde + ':', e); } catch (_) {} }; }
window.addEventListener('load', function(){
  if (window.VLibras && window.VLibras.Widget){
    try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {}
  }
});

(function gestores() {
  const C = window.MonitorCatalogo, P = 'prefeituras.municipio.';
  const tx = (id, v) => (C && C.texto && C.texto(P + id, v)) || '';
  const json = url => fetch(url).then(r => r.ok ? r.json() : null).catch(() => null);
  const esc = v => String(v == null ? '' : v).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const reais = v => v === 0 ? 'zero' : 'R$ ' + Math.round(v).toLocaleString('pt-BR');
  const MES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
  const NOMES = {estiagem: 'seca', incendios: 'fogo', chuvas: 'chuva forte', calor: 'calor'};

  const REF = json('data/municipios_ibge_referencia.json'), ENQ = json('data/enquadramento_card.json');
  const CARD = json('data/municipios_card.json'), META = json('data/meta.json');
  let financeiro = null;   // só na primeira consulta: são os arquivos grandes da página de Financiamento
  const carregarFinanceiro = () => financeiro = financeiro || Promise.all([
    json('data/financiamento/municipios/transferencias_uniao.json'),
    json('data/financiamento/municipios/fns_municipios_2026.json'),
    json('data/financiamento/municipios/despesa_182.json')]);

  /* Os dois números do "O que a lei exige" vêm do dado, como na inicial. */
  Promise.all([REF, ENQ, C && C.pronto]).then(([ref, enq]) => {
    const n = (ref || []).length, ind = Object.values((enq || {}).municipios || {}).filter(v => v.ch || v.geo).length;
    if (n && C) C.escrever(document.getElementById('municipioAbertura'), 'prefeituras.municipio.abertura.molde', {n_municipios: n});
    /* O guarda é a FONTE, não o valor: com o arquivo no ar e ninguém indicado, o cartão diz zero
       por extenso; sem o arquivo, fica o texto de reserva, que é a lacuna declarada. Testar o valor
       descartava o zero medido e deixava o 2.095 de reserva no ar como leitura de hoje. */
    const pôr = (id, v) => { const e = document.getElementById(id); if (e && v != null) { e.textContent = v === 0 ? 'zero' : v.toLocaleString('pt-BR'); e.setAttribute('data-conteudo-fixado', '1'); } };
    pôr('leiValor_indicados', enq ? ind : null); pôr('leiValor_todos', ref ? n : null);
  }).catch(_erroGest('gestores:numeros'));
  /* Fonte dos três cartões: o ato e a data da edição em que o MARÉ o conferiu. */
  Promise.all([json('data/meta.json'), C && C.pronto]).then(([M]) => {
    ['estados', 'indicados', 'todos'].forEach(k => {
      if (window.MonitorMapas) MonitorMapas.credito('leiFonte_' + k, {fontes: C.texto('prefeituras.quem-deve.' + k + '.fonte'),
        url: C.texto('prefeituras.quem-deve.' + k + '.fonte_url'), data: (M || {}).atualizado_em || null});
    });
  }).catch(_erroGest('gestores:fontes'));

  const cartao = (acento, rotulo, valor, nota) => '<div class="cartao cartao--acento-' + acento + '">'
    + '<p class="cartao-numero-rotulo">' + esc(rotulo) + '</p><p>' + valor + '</p>'
    + (nota ? '<p class="note u-mb-0">' + nota + '</p>' : '') + '</div>';

  /* Três valores, como no handover: localizado (com o ato e o documento), não localizado até o corte
     (verificado, sem documento de plano) e ainda não verificado. */
  function cartaoPlano(sp, corte) {
    if (sp.estado === 'encontrado' || sp.estado === 'estadual')
      return cartao('argila', tx('plano.rotulo'), esc(tx('plano.localizado', {ato: sp.documento || sp.fonte || '', data: sp.data || ''}).replace(/,\s*$/, '')),
        sp.url ? '<a href="' + esc(sp.url) + '" target="_blank" rel="noopener">' + esc(tx('plano.ver')) + '</a>' : '');
    if (sp.estado === 'nao_verificado') return cartao('argila', tx('plano.rotulo'), esc(tx('plano.nao_verificado')), esc(tx('plano.nao_verificado_nota')));
    return cartao('argila', tx('plano.rotulo'), esc(tx('plano.nao_localizado', {corte: corte || tx('sem_coleta')})), tx('plano.nao_localizado_nota'));
  }

  function mostrar(uf, nome, card, ref, enq, sinais, fin, plano, corte) {
    const reg = (ref || []).find(x => x.uf === uf && x.nome === nome) || {}, cod = String(reg.codigo_ibge || '');
    const marcas = ((enq || {}).municipios || {})[cod] || {};
    const risco = ((sinais || {}).uf || {})[uf] || {}, rp = risco.risco_projetado || {};
    const doc = (((sinais || {}).fontes || {}).painel_el_nino || {}).documento || '';
    const familias = (rp.componentes || []).map(c => NOMES[c]).filter(Boolean);
    let recursos = esc(tx('sem_coleta')), notaRec = '';
    if (fin) {
      const [T, F, D] = fin;
      const meses = Object.entries((T || {}).meses_lidos || {}).filter(([, v]) => !v.parcial).map(([m]) => m).sort();
      const ultimo = meses[meses.length - 1];
      const soma = (obj, f) => meses.reduce((a, m) => a + (obj && obj[m] ? f(obj[m]) : 0), 0);
      // arquivo ausente = sem coleta; município ausente do arquivo lido = não localizado (como no Financiamento)
      const ler = (X, f) => !X ? tx('sem_coleta') : (X.municipios || {})[cod] ? f(X.municipios[cod]) : tx('recursos.nao_localizado');
      const dc = ler(T, x => reais(soma(x.meses, r => r.defesa_civil || 0)));
      const sa = ler(F, x => reais(soma(x.meses, r => r[0] || 0)));
      const classe = ler(D, x => (x.classe === 'com_lancamento'
        ? tx('recursos.classe.com_lancamento', {valor: reais(+(x.valores || {}).liquidada || 0)})
        : tx('recursos.classe.' + x.classe)) || tx('sem_coleta'));
      recursos = esc(tx('recursos.valor', {defesa_civil: dc, saude: sa}));
      notaRec = tx('recursos.nota', {mes: ultimo ? MES[+ultimo.slice(4) - 1] + ' de ' + ultimo.slice(0, 4) : tx('sem_coleta'),
        ano: String((D || {}).exercicio || ''), classe: esc(classe)});
    }
    card.innerHTML = '<h4>' + esc(nome) + ' · ' + esc(uf) + '</h4><div class="grade-figuras">'
      + cartaoPlano(ConsultaMunicipio.situacaoDoPlano((((plano || {}).municipios) || {})[cod]), corte)
      + cartao('neutro', tx('cadastro.rotulo'), esc(tx(marcas.ch || marcas.geo ? 'cadastro.indicado' : 'cadastro.fora')), tx('cadastro.nota'))
      + cartao('musgo', tx('risco.rotulo'), esc(familias.length ? tx('risco.valor', {familias: familias.join(', ').replace(/^./, c => c.toUpperCase())}) : tx('risco.sem_sinal')),
          doc ? tx('risco.nota', {data_boletim: esc(doc.split(/\s+[—-]\s+/).pop())}) : '')
      + cartao('neutro', tx('recursos.rotulo'), recursos, notaRec)
      + '</div>';
  }

  Promise.all([REF, json('data/geo_uf.json'), C && C.pronto]).then(([ref, geo]) => {
    const NOME_UF = {}; ((geo || {}).features || []).forEach(f => { NOME_UF[f.properties.sigla] = f.properties.name; });
    const porUF = {};
    (ref || []).forEach(x => (porUF[x.uf] = porUF[x.uf] || []).push(x.nome));
    const SINAIS = json('data/sinais_risco.json');
    ConsultaMunicipio.montar({uf: 'munUF', municipio: 'munNome', lista: 'munLista', cartao: 'munCard',
      estados: NOME_UF, semLista: tx('sem_lista'),
      municipios: uf => (porUF[uf] || []).slice().sort((a, b) => a.localeCompare(b)),
      mostrar: (uf, nome, card) => {
        Promise.all([REF, ENQ, SINAIS, CARD, META]).then(([r, e, s, p, m]) => {
          const corte = (m || {}).corte || '';
          mostrar(uf, nome, card, r, e, s, null, p, corte);
          return carregarFinanceiro().then(fin => { if (card.querySelector('h4') && card.querySelector('h4').textContent.startsWith(nome + ' · ')) mostrar(uf, nome, card, r, e, s, fin, p, corte); });
        }).catch(_erroGest('gestores:cartao'));
      }});
  }).catch(_erroGest('gestores:consulta'));
})();
