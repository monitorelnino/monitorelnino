/* A7-17 (12/10/2026): erro de bloco que não renderiza não é engolido em silêncio — vai ao
   console com o lugar, onde o portão de runtime e quem abre o DevTools o veem. */
function _erroImp(onde) { return function (e) { try { console.error("[MARÉ] falha em " + onde + ":", e); } catch (_) {} }; }

window.addEventListener('load', function(){ if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} } });

/* ===== A referência completa (HANDOVER_IMPRENSA §1, item 4) =====
   Regra 0 da página: nada escrito à mão que dependa do dado. A data da edição vem do banco; a de
   acesso é a de hoje, de quem está lendo, que é o que uma referência pede. */
(function datasDaReferencia(){
  const põe = (id, v) => { const e = document.getElementById(id); if (e && v != null && v !== '') e.textContent = v; };

  fetch('data/meta.json').then(r => r.ok ? r.json() : null).then(M => {
    if (!M) return;
    põe('relData2', M.atualizado_em || M.corte);
  }).catch(_erroImp("imprensa:16"));

  const hoje = new Date();
  põe('citarAcesso', String(hoje.getDate()).padStart(2, '0') + '/'
    + String(hoje.getMonth() + 1).padStart(2, '0') + '/' + hoje.getFullYear());
})();

/* ===== "Esta semana no MARÉ" (HANDOVER_IMPRENSA §1, item 2) =====
 *
 * Seis cartões compactos. O RÓTULO é texto editorial e vive no catálogo; o VALOR, a referência de
 * período e a fonte vêm de `data/imprensa/semana.json`, escritos aqui — nenhum número desta seção
 * está no HTML. Quais seis a página mostra é decisão de layout, e por isso a lista está aqui e no
 * contrato da página; o que cada um vale é do gerador da edição.
 *
 * Cartão que o gerador marcou sem coleta, ou que não veio na edição, diz "sem coleta até o corte" —
 * nunca zero, nunca travessão (regra dos números: zero medido e ausência de dado são coisas
 * distintas). Zero medido sai por extenso.
 */
(function estaSemana(){
  const IDS = ['capitais_com_plano', 'decretos_na_semana', 'reconhecimentos_na_semana',
               'municipios_aviso_inmet', 'desembolsado_no_mes', 'ufs_dengue_alerta'];
  const M = window.MonitorMapas;
  if (!M) return;

  /* Dinheiro em cartão compacto vai em milhões com uma casa, a mesma forma do "mês a mês" do
     Financiamento; abaixo de um milhão, o valor inteiro. */
  function valorDoCartao(c) {
    if (c.valor === 0) return 'zero';
    if (c.unidade === 'reais') {
      return c.valor >= 1e6 ? 'R$ ' + M.numBR(c.valor / 1e6, 1) + ' milhões'
                            : 'R$ ' + M.numBR(c.valor);
    }
    return M.numBR(c.valor, Number.isInteger(c.valor) ? 0 : 1);
  }

  /* A data do cartão é a da consulta à fonte, e só ela. O gerador às vezes põe PROSA nesse campo
     ("desde 29/06/2026", que é o início do El Niño, e "nível atual"): dali sai uma data que não é a
     da consulta, e o cartão passaria a dizer que foi atualizado em junho. Então o campo só vale
     quando é uma data inteira, com hora ou sem; fora disso fica a data da edição, que é quando o
     número foi lido. */
  function dataDaConsulta(c) {
    const v = String(c.consultado_em || '').trim();
    return /^\d{2}\/\d{2}\/\d{4}( \d{2}:\d{2})?$/.test(v) ? M.dataBR(v) : null;
  }

  fetch('data/imprensa/semana.json').then(r => r.ok ? r.json() : null).then(S => {
    if (!S) return;
    const porId = {};
    (S.cartoes || []).forEach(c => { porId[c.id] = c; });
    const edicao = (S.indices || {}).edicao || S.gerado_em || null;

    IDS.forEach(id => {
      const valor = document.getElementById('semanaValor_' + id);
      const ref = document.getElementById('semanaRef_' + id);
      const c = porId[id];
      if (!valor) return;
      if (!c || c.sem_coleta || c.valor == null) {
        valor.textContent = 'sem coleta até o corte';
        if (ref) ref.textContent = '';
        if (c) M.credito('semanaFonte_' + id, {fontes: c.fonte, data: null, url: c.url_fonte || null});
        return;
      }
      valor.textContent = valorDoCartao(c);
      /* Horário não entra nesta página (editoria): referência com data e hora sai só com a data. */
      if (ref) ref.textContent = (M.dataBR(c.referencia) && /\d{2}:\d{2}/.test(c.referencia))
        ? M.dataBR(c.referencia) : (c.referencia || '');
      M.credito('semanaFonte_' + id, {fontes: c.fonte, data: dataDaConsulta(c) || edicao,
                                      url: c.url_fonte || null});
    });
  }).catch(_erroImp("imprensa:62"));
})();
