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
    fetch('data/resposta/por_uf.json').then(r => r.ok ? r.json() : {}).catch(() => ({})).then(P => {
      const N = (P && P.nacional) || {};
      const pr = N.prazo_reconhecimento || null;

      // Emergências
      ponha('numValor_decretaram', N.n_municipios != null ? fmt(N.n_municipios) : lacuna());
      if (N.reconhecidos != null) ponha('numValor_reconhecidos', fmt(N.reconhecidos));
      else ponha('numValor_reconhecidos', lacuna());
      if (pr && pr.p25 != null) {
        ponha('numPer_reconhecidos', preenche(txtDoCatalogo('imprensa.numeros.reconhecidos.periodo', ''),
          { p25: fmt(pr.p25), p75: fmt(pr.p75) }));
      } else ponha('numPer_reconhecidos', txtDoCatalogo('imprensa.numeros.reconhecidos.sem_prazo', ''));
      ponha('numValor_pessoas_sob_decreto', N.pop_sob_decreto != null
        ? M.numBR(N.pop_sob_decreto / 1e6, 1) + ' mi' : lacuna());
      const pl = acum(S, 'municipios_plano_localizado');
      ponha('numValor_plano_localizado', pl ? fmt(pl.valor) : lacuna());

      // Sinais físicos
      const foc = acum(S, 'focos_desde_29_06');
      ponha('numValor_focos', foc ? fmt(foc.valor) : lacuna());

      // Saúde: o que o acumulado traz como lacuna declarada fica em lacuna
      const uf = acum(S, 'estados_acima_da_faixa_por_doenca');
      ponha('numValor_ufs_acima_faixa', uf ? fmt(uf.valor) : lacuna());

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
  });

  // Glossário: busca enquanto se digita (função comum BuscaLista)
  const campo = document.getElementById('glossarioBusca');
  if (campo && window.BuscaLista) {
    const itens = Array.from(document.querySelectorAll('#glossario details'));
    window.BuscaLista.montar(campo, itens);
  }
})();
