// As quatro datas do rodapé, iguais em todas as páginas que mostram dado (editoria, 24/10/2026):
// última atualização, corte dos dados, última coleta e última publicação. Só descreve o que existe
// nos arquivos; a marcação traz a cópia estática (`preencher_fallback_estatico.py`) e este arquivo
// a atualiza. Sem a data, a cópia estática fica como está: nada se afirma por inferência.
(function () {
  "use strict";
  const poe = (id, v) => { const el = document.getElementById(id); if (el && v) el.textContent = v; };
  const brDeIso = s => { const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(s || "")); return m ? m[3] + "/" + m[2] + "/" + m[1] : ""; };
  const json = u => fetch(u).then(r => r.ok ? r.json() : null).catch(() => null);
  Promise.all([json("data/meta.json"), json("data/saude_pipeline.json")]).then(([meta, pip]) => {
    const publicacao = meta && (meta.atualizado_em || meta.corte);
    poe("metaAtualizado", publicacao);
    poe("corteDados", meta && meta.corte);
    poe("metaPublicacao", publicacao);
    if (pip) return poe("metaColeta", brDeIso(pip.atualizado_em));
    return json("data/verificacao_resumo.json").then(r => poe("metaColeta", brDeIso(r && r.ultima_rodada_log)));
  });
})();
