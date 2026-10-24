// As quatro datas do rodapé, iguais em todas as páginas que mostram dado (editoria, 24/10/2026):
// atualização, corte dos dados, coleta e publicação. O texto vive em `conteudo/_comum.json`
// (`rodape.datas.molde`); a marcação traz a cópia estática (`preencher_fallback_estatico.py`) e este
// arquivo a atualiza. Data que o arquivo não traz fica como está na cópia: nada se afirma por inferência.
(function () {
  "use strict";
  const brDeIso = s => { const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(s || "")); return m ? m[3] + "/" + m[2] + "/" + m[1] : ""; };
  const json = u => fetch(u).then(r => r.ok ? r.json() : null).catch(() => null);
  const linha = document.querySelector('[data-conteudo-html="rodape.datas.molde"]');
  const atual = id => { const el = document.getElementById(id); return el ? el.textContent : ""; };
  if (!linha || !window.MonitorCatalogo) return;
  Promise.all([json("data/meta.json"), json("data/saude_pipeline.json"), window.MonitorCatalogo.pronto]).then(async ([meta, pip]) => {
    const resumo = pip ? null : await json("data/verificacao_resumo.json");
    const publicacao = meta && (meta.atualizado_em || meta.corte);
    window.MonitorCatalogo.escrever(linha, "rodape.datas.molde", {
      atualizado: publicacao || atual("metaAtualizado"),
      corte: (meta && meta.corte) || atual("corteDados"),
      coleta: brDeIso(pip ? pip.atualizado_em : resumo && resumo.ultima_rodada_log) || atual("metaColeta"),
      publicacao: publicacao || atual("metaPublicacao"),
    });
  });
})();
