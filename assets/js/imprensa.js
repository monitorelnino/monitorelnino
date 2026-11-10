/* Imprensa (redesenho de 26/10/2026, HANDOVER_IMPRENSA_REDESENHO_25-10-2026).
   Regra da página: nada que dependa do dado está escrito à mão. Textos vêm de conteudo/imprensa.json
   (o catálogo já os aplica); valores vêm de data/imprensa/semana.json (acumulado e indices) e de
   data/resposta/por_uf.json (nacional). Ausência é "sem coleta até o corte", nunca zero. */
(function () {
  'use strict';
  const M = window.MonitorMapas;

  function txtDoCatalogo(chave, fallback) {
    const n = document.querySelector('[data-conteudo="' + chave + '"]');
    return n ? n.textContent : fallback;
  }
  function ponha(id, v) { const e = document.getElementById(id); if (e) e.textContent = v; }
  function lacuna() { return txtDoCatalogo('imprensa.numeros.sem_coleta', 'sem coleta até o corte'); }
  function preenche(modelo, vars) {
    return String(modelo).replace(/\{(\w+)\}/g, (m, k) => (vars[k] != null ? vars[k] : m));
  }
  function acum(S, id) {
    const a = ((S && S.acumulado) || []).find(x => x.id === id);
    return a && !a.sem_coleta && a.valor != null ? a : null;
  }
  function fmt(v) { return M.numBR(v, Number.isInteger(v) ? 0 : 1); }

  fetch('data/imprensa/semana.json').then(r => r.ok ? r.json() : {}).catch(() => ({})).then(S => {
    // Atualização de cada cartão: a data que o gerador grava em gerado_em (ausente = lacuna).
    const atualizado = S && S.gerado_em ? S.gerado_em.split('-').reverse().join('/') : lacuna();
    // "Como citar": a edição é a data do motor; o acesso, o dia de quem lê. Os dois ficavam com o texto
    // de espera desde o redesenho de 26/10 — nenhum script os preenchia (09/11/2026).
    ponha('relData2', atualizado);
    ponha('citarAcesso', new Date().toLocaleDateString('pt-BR'));
    const tpl = document.getElementById('tplAtualizacao');
    // O catálogo reescreve o texto da fonte ao chegar: a linha entra depois dele.
    const cat = window.MonitorCatalogo;
    if (tpl) (cat ? cat.pronto : Promise.resolve()).then(() => {
      document.querySelectorAll('.cartao-numero > .cartao-numero-fonte').forEach(e => {
        const linha = tpl.content.cloneNode(true);
        linha.querySelector('.atualizacao-data').textContent = atualizado;
        e.append(' · ', linha);
      });
    });
    // 09/11/2026: só 7 dos 20 cartões eram preenchidos — os outros 13 tinham número em
    // data/imprensa/semana.json e mostravam "sem coleta até o corte". Agora cada cartão declara no HTML
    // (`data-acumulado`) de qual número do acumulado ele vem, e TODO cartão é preenchido daqui; o portão
    // verificar_imprensa_coerencia.py reprova cartão com número no acumulado e lacuna na tela.
    // Depois do catálogo: ele escreve o texto de espera ("sem coleta até o corte") no próprio valor, e
    // quem escrevesse antes dele seria apagado — era assim que até os cartões com número sumiam.
    (cat ? cat.pronto : Promise.resolve()).then(() => document.querySelectorAll('.cartao-numero[data-acumulado]').forEach(c => {
      const el = c.querySelector('.cartao-numero-valor');
      const vs = c.dataset.acumulado.split(/\s+/).map(id => acum(S, id));
      if (!el) return;
      if (vs.some(v => !v)) { el.textContent = lacuna(); return; }
      const n = x => (x === 0 ? 'zero' : fmt(x));
      el.textContent = vs.map(v => v.unidade === 'reais' ? M.reais(v.valor)
        : v.unidade === 'pessoas' ? M.numBR(v.valor / 1e6, 1) + ' mi' : n(v.valor)).join(' · ');
      // 10/11/2026: o número é do que foi coletado, e o período REAL vem com ele (início da série, dias com
      // dado, registro incompleto) — o texto fixo do HTML dizia "Desde 29/06" para uma soma que começa depois.
      const per = c.querySelector('.cartao-numero-variacao');
      if (per && vs.length === 1 && vs[0].periodo_molde && cat) per.textContent = cat.texto(vs[0].periodo_molde, vs[0].periodo_vars || {});
    }));
    fetch('data/resposta/por_uf.json').then(r => r.ok ? r.json() : {}).catch(() => ({})).then(P => {
      const N = (P && P.nacional) || {};
      const pr = N.prazo_reconhecimento || null;
      // A resposta do prazo de reconhecimento traz os números de hoje, do derivado de data/resposta.
      if (cat && pr && pr.p25 != null) cat.pronto.then(() => {
        const el = document.querySelector('[data-conteudo="imprensa.ler.emergencias.4.resposta"]');
        if (el) el.textContent = cat.texto('imprensa.ler.emergencias.4.resposta', { n: N.reconhecidos, p25: pr.p25, p75: pr.p75, p90: pr.p90 });
      });
      if (pr && pr.p25 != null) {
        ponha('numPer_reconhecidos', preenche(txtDoCatalogo('imprensa.numeros.reconhecidos.periodo', ''),
          { p25: fmt(pr.p25), p75: fmt(pr.p75) }));
      } else ponha('numPer_reconhecidos', txtDoCatalogo('imprensa.numeros.reconhecidos.sem_prazo', ''));
    });

    // Índices
    const I = (S && S.indices) || {};
      [['legal', I.mare_legal], ['saude', I.mare_saude]].forEach(([k, v]) => {
        if (v == null) return;
        ponha('indice_' + k + '_valor', fmt(v));
        const regua = document.getElementById('indice_' + k + '_regua');
        const marca = regua && regua.querySelector('.regua-faixas-marca i');
        if (marca) {
          const pos = Math.max(0, Math.min(100, Number(v)));
          marca.style.left = pos + '%';
        }
      });
  });

  // Glossário: busca enquanto se digita. 09/11/2026: chamava `window.BuscaLista`, que não existe no
  // site — o campo nunca filtrou nada. Agora filtra aqui: termo ou explicação que contenha o que se
  // digitou (sem acento, sem caixa), abre o que casou e esconde o grupo que ficou vazio.
  const campo = document.getElementById('glossarioBusca');
  if (campo) campo.addEventListener('input', () => {
    const q = M.nrm(campo.value);
    document.querySelectorAll('#glossarioGrupos > .cartao').forEach(g => {
      let algum = false;
      g.querySelectorAll('details').forEach(d => {
        const casa = !q || M.nrm(d.textContent).includes(q);
        d.hidden = !casa; d.open = !!q && casa; algum = algum || casa;
      });
      g.hidden = !algum;
    });
  });
})();
