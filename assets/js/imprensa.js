const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
// ===== imprensa.html · release da edição (handover de 01/10/2026) =====
// O release é o texto aprovado, e todo número dele vem do banco — inclusive os da SEMANA, que são
// os MESMOS cartões da grade acima: mesma janela, mesma fonte, mesmo critério. Dois números iguais
// na mesma página com contas diferentes é o defeito que a regra 0 existe para impedir.
/* 03/10/2026 (handover do blog e da imprensa): o release gerado e a grade "Esta semana em
   números" SAÍRAM da Imprensa. O que muda toda semana vive no boletim do blog, escrito pela
   editoria; aqui fica o PONTEIRO — a data da edição, três números congelados nela e o caminho.
   O motor da semana continua existindo: é dele que o boletim tira os números. */
(function ponteiroDoBoletim(){
  const alvo = document.getElementById('boletimNumeros');
  if (!alvo) return;
  Promise.all([
    fetch('data/blog/boletim_mais_recente.json').then(r => r.ok ? r.json() : null).catch(() => null),
    fetch('data/blog/posts.json').then(r => r.ok ? r.json() : null).catch(() => null),
  ]).then(([boletim, posts]) => {
    const secao = document.getElementById('boletim');
    const lista = Array.isArray(posts) ? posts : ((posts || {}).posts || []);
    const ed = lista.filter(p => (p.etiqueta || '') === 'Boletim')[0];
    if (!boletim || !(boletim.numeros || []).length) { if (secao) secao.hidden = true; return; }
    const data = document.getElementById('boletimData');
    if (data) data.textContent = 'Edição de ' + (boletim.edicao || '');
    const link = document.getElementById('boletimLink');
    if (link && ed) { link.href = ed.url; link.textContent = 'ler o boletim de ' + (ed.data_br || ''); }
    else if (link) { link.href = 'blog.html'; link.textContent = 'ver o blog'; }
    alvo.innerHTML = boletim.numeros.slice(0, 3).map(n =>
      '<div class="cartao-numero">'
      + '<p class="cartao-numero-valor">' + esc(n.valor) + '</p>'
      + '<p class="cartao-numero-rotulo">' + esc(n.rotulo) + '</p>'
      + '<p class="cartao-numero-fonte">' + esc(n.fonte || '') + '</p></div>').join('');
  });
})();


// 03/10/2026: os blocos que escreviam em `listaNaoSuspenso` e `listaSuspenso` saíram. Os dois
// `id` não existem em nenhuma página desde que a editoria tirou o período eleitoral da
// Imprensa e de Prefeituras (01/10) — eram código escrevendo no vazio, e um deles era uma
// metade órfã, deixada por um corte meu de 03/10. O canário do site publicado procurava
// justamente essa lista para provar que o script da página roda.
window.addEventListener('load', function(){ if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} } });

// 14/09/2026 (pedido de Patricia, 13/09): "O que a lei deixa aberto" vira nota para a imprensa — mesma fonte e o
// mesmo desenho de linha da página do calendário (data/calendario/dispositivos.json, campo nao_suspenso).

// 30/09/2026: o calendário compacto da imprensa saiu do código, com as outras duas telas de
// calendário (decisão da editoria). O que ele mostrava vive na METODOLOGIA.

// ===== imprensa.html · "Esta semana em números" (handover de 01/10/2026) =====
// A grade é DESENHADA a partir de data/imprensa/semana.json, na ordem dos grupos que o arquivo
// declara. Não há cartão escrito no HTML: é assim que a regra 0 da página ("nada escrito à mão que
// dependa do dado") deixa de depender de vigilância e passa a ser estrutural.
//
// Variação ao lado do número, com seta e valor, SEM cor de bom/ruim: a página não diz ao leitor se
// subir é bom. Cartão sem coleta mostra "sem dado nesta edição" e o motivo — nunca zero.
/* ===== Os seis números do topo (01/10/2026) =====
   Regra 0 da página: nada escrito à mão que dependa do dado. Os dois índices, os quatro contadores,
   as duas versões e as datas vêm todos do banco, a cada publicação.

   "Última semana" são os 7 dias até a data da edição, contados PELA DATA DO ATO — a data em que o
   plano saiu no diário, ou em que o decreto foi assinado —, e não pela data em que o MARÉ o
   localizou. As duas podem distar semanas, e a segunda mede o nosso trabalho, não o do ente. */
(function numerosDoTopo(){
  const põe = (id, v) => { const e = document.getElementById(id); if (e && v != null && v !== '') e.textContent = v; };
  const n = v => Number(v).toLocaleString('pt-BR');

  fetch('data/indice.json').then(r => r.ok ? r.json() : null).then(idx => {
    if (!idx) return;
    const ufs = Object.keys(idx).filter(k => k.length === 2);
    if (!ufs.length) return;
    const media = Math.round(ufs.reduce((a, u) => a + idx[u].total, 0) / ufs.length * 10) / 10;
    põe('topoLegal', media.toLocaleString('pt-BR', {minimumFractionDigits: 1}));
    // A versão sai do próprio campo `metodo` do índice: ele começa por "v3.1 — …". Assim a versão
    // publicada é a do motor que calculou o número, e não uma string paralela que alguém atualiza.
    const m = String((idx[ufs[0]] || {}).metodo || '').match(/^v(\d+(?:\.\d+)*)/);
    if (m) põe('citarVersaoLegal', m[1]);
  }).catch(() => {});

  fetch('data/monitor_saude.json').then(r => r.ok ? r.json() : null).then(sa => {
    if (!sa) return;
    // O MARÉ Saúde NÃO tem número nacional hoje, e o próprio dado diz isso: o campo é
    // `media_das_verificadas`, e a nota que vem com ele é "a média cobre só as UFs verificadas e
    // não é um número nacional". A página de Saúde já publica esse número com o qualificador ao
    // lado, e aqui ele vai igual — sem o qualificador, uma média parcial viraria índice nacional,
    // que é exatamente o que a metodologia proíbe afirmar.
    const res = sa.resumo || {};
    if (res.media_das_verificadas != null) {
      põe('topoSaude', Number(res.media_das_verificadas).toLocaleString('pt-BR', {minimumFractionDigits: 1}));
      /* 01/10/2026 (decisão da editoria): o número só vira MANCHETE NACIONAL quando os 27 estados
         estiverem verificados. Antes disso ele sai com o rótulo que diz de quantos é a média — e o
         rótulo é a diferença entre publicar uma média parcial e publicar um índice nacional que
         ainda não existe. O corte é o próprio dado: 27 verificadas, não uma data. */
      const TODAS = 27;
      if (res.verificadas != null) {
        põe('topoSaudeNota', res.verificadas >= TODAS
          ? 'os ' + TODAS + ' estados verificados'
          : 'média dos ' + res.verificadas + ' estados verificados');
      }
    }
    if (sa.versao != null) põe('citarVersaoSaude', String(sa.versao));
  }).catch(() => {});

  fetch('data/meta.json').then(r => r.ok ? r.json() : null).then(M => {
    if (!M) return;
    ['relData', 'relData2', 'relDataRelease'].forEach(i => põe(i, M.atualizado_em || M.corte));
  }).catch(() => {});

  // "Acesso em" é a data de HOJE, de quem está lendo — é isso que uma referência pede.
  const hoje = new Date();
  põe('citarAcesso', String(hoje.getDate()).padStart(2, '0') + '/'
    + String(hoje.getMonth() + 1).padStart(2, '0') + '/' + hoje.getFullYear());
})();

/* Copiar o release: o texto que a redação leva é o que está na tela, já com os números do dia. */
(function copiarRelease(){
  const b = document.getElementById('copiarRelease'), alvo = document.getElementById('releaseTexto');
  if (!b || !alvo || !navigator.clipboard) return;
  b.addEventListener('click', () => {
    const txt = alvo.textContent.replace(/\s+/g, ' ').trim();
    navigator.clipboard.writeText(txt).then(() => {
      const antes = b.textContent;
      b.textContent = 'Texto copiado';
      setTimeout(() => { b.textContent = antes; }, 2000);
    }).catch(() => {});
  });
})();
