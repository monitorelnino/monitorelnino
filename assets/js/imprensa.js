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

/* ===== "Esta semana no MARÉ" e "Como os índices funcionam" (HANDOVER_IMPRENSA §1 item 2, §3 e §4.2) =====
 *
 * Seis cartões compactos. O RÓTULO é texto editorial e vive no catálogo; o VALOR, a referência de
 * período e a fonte vêm de `data/imprensa/semana.json`, escritos aqui — nenhum número desta seção
 * está no HTML. Quais seis a página mostra é decisão de layout, e por isso a lista está aqui e no
 * contrato da página; o que cada um vale é do gerador da edição.
 *
 * Cartão que o gerador marcou sem coleta, ou que não veio na edição, diz "sem coleta até o corte" —
 * nunca zero, nunca travessão (regra dos números: zero medido e ausência de dado são coisas
 * distintas). Zero medido sai por extenso.
 *
 * A definição de cada índice é escrita por uma função só, a partir de `meta.json` e
 * `monitor_saude.json`, e publicada no mesmo arquivo em `definicao_dos_indices`. A página só a
 * exibe: quando a definição mudar, o texto muda sozinho, aqui e na Saúde, e nunca divergem.
 * Enquanto o campo não existir no dado, fica o texto do catálogo, que é o que a definição em vigor
 * produz — lacuna declarada da classe, sem nada inventado e sem quebrar. Nenhum número de versão
 * sai para o leitor (editoria, 05/10).
 *
 * As duas seções vivem do MESMO arquivo, então a página o lê UMA vez (lição do #889): dois `fetch`
 * do mesmo JSON eram duas requisições e dois caminhos de erro para o mesmo dado.
 */
(function aSemanaEOsIndices(){
  const IDS = ['capitais_com_plano', 'decretos_na_semana', 'reconhecimentos_na_semana',
               'municipios_aviso_inmet', 'desembolsado_no_mes', 'ufs_dengue_alerta'];
  const ALVOS = {legal: 'indicesLegalTexto', saude: 'indicesSaudeTexto'};
  const M = window.MonitorMapas;

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

  function cartoes(S) {
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
  }

  /* Arquivo que não vem, ou que vem quebrado, é o mesmo fato que arquivo sem cartão: cada cartão diz
     "sem coleta até o corte", frase que `cartoes` já escreve. Sair antes dela deixava os seis cartões
     VAZIOS, que é o que a régua dos números proíbe. O erro segue indo ao console, para o portão ver. */
  fetch('data/imprensa/semana.json').then(r => r.ok ? r.json() : {})
    .catch(e => (_erroImp('imprensa:semana')(e), {})).then(S => {
    /* O texto da semana (dois parágrafos) é do gerador da edição, não desta página: aqui ele só
       aparece. Entra quando o gerador é o da reforma — o que se prova pela presença de
       `definicao_dos_indices`, que só ele escreve. Antes disso o texto trazia "ciclo" sozinho, que a
       editoria tirou desta página, e a seção fica com os seis cartões.
       Em coluna única, e não nas duas colunas do handover: a colunação dos textos saiu do site
       inteiro em 16/10 (editoria), e a regra vence o handover. Divergência no contrato. */
    const texto = document.getElementById('semanaTexto');
    if (texto && S.definicao_dos_indices && S.texto_pronto) {
      texto.replaceChildren(...String(S.texto_pronto).split(/\n\s*\n/).map(par => {
        const p = document.createElement('p');
        p.textContent = par.trim();
        return p;
      }).filter(p => p.textContent));
      texto.hidden = false;
    }
    if (M) cartoes(S);
    const def = S.definicao_dos_indices;
    if (def) Object.keys(ALVOS).forEach(k => {
      const e = document.getElementById(ALVOS[k]);
      if (e && def[k]) { e.textContent = def[k]; e.setAttribute('data-conteudo-fixado', '1'); }
    });
  }).catch(_erroImp("imprensa:semana"));
})();
