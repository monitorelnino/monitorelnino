const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
// ===== imprensa.html · release da edição (handover de 01/10/2026) =====
// O release é o texto aprovado, e todo número dele vem do banco — inclusive os da SEMANA, que são
// os MESMOS cartões da grade acima: mesma janela, mesma fonte, mesmo critério. Dois números iguais
// na mesma página com contas diferentes é o defeito que a regra 0 existe para impedir.
/* 03/10/2026 (handover do blog e da imprensa): o release gerado e a grade "Esta semana em
   números" SAÍRAM da Imprensa. O que muda toda semana vive no boletim do blog, escrito pela
   editoria; aqui fica o PONTEIRO — a data da edição, três números congelados nela e o caminho.
   O motor da semana continua existindo: é dele que o boletim tira os números. */
/* 04/10/2026 (handover da rotina semanal): o ponteiro do boletim vira o ponteiro dos TEXTOS. Dois
   links, título e data, um por linha da rotina. Sem número: o que muda toda semana é o texto, e
   número repetido aqui seria uma terceira cópia a conferir. */
/* 05/10/2026 (handover da preparacao programatica, item 7): `ponteiroDosTextos` SAIU. O bloco
   "Textos desta semana" deixou a pagina de imprensa -- o blog e o menu, e o ponteiro era uma
   terceira copia a conferir. O codigo sai junto com o elemento: script que escreve num `id` que
   nao existe mais e codigo morto, e foi assim que `listaNaoSuspenso` ficou orfao em 03/10. */


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

  /* 05/10/2026 (itens 7 e 7-B): o bloco "Os indices nesta edicao" e a VERSAO na referencia
     sairam da pagina. A manchete sai da imprensa (os indices vivem nas paginas) e a versao nao
     serve ao leitor, porque o codigo nao e distribuido. O codigo que lia `data/indice.json` e
     `data/monitor_saude.json` so para escreve-los sai junto -- menos a leitura de saude, que
     continua, porque o molde do "Como os indices sao calculados" depende de quantos estados
     estao verificados. */
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

/* ===== Os dois moldes gerados da pagina (handover de 05/10/2026, itens 7-B e 7-C) =====
 *
 * Frase que depende do dado nao se escreve a mao: e molde no catalogo, resolvido aqui com o dado
 * em maos. Sao dois.
 *
 *   1. "Como os indices sao calculados", MARE Saude: enquanto os 27 estados nao estiverem
 *      verificados, a frase diz de quantos e a media. Quando os 27 estiverem, a frase SOME --
 *      porque ai a media ja e nacional, e o qualificador passaria a negar o que o numero e.
 *   2. "Com que frequencia o site e atualizado?": a cadencia vem de
 *      `data/cadencia_publicacao.json`, que o gerador le do gatilho do publicador. Trocar um
 *      horario no workflow muda a frase sozinho.
 *
 * Os dois marcam `data-conteudo-fixado`: quem escreve a partir de dado marca, senao a `aplicar`
 * seguinte do catalogo reescreve com o molde nao resolvido. Foi a corrida medida no Financiamento.
 */
(function moldesGerados(){
  const C = window.MonitorCatalogo;
  if (!C || !C.pronto) return;

  function porDado(elemento, html) {
    if (!elemento || html == null) return;
    elemento.innerHTML = html;
    elemento.setAttribute('data-conteudo-fixado', '1');
  }

  C.pronto.then(function () {
    const TODAS = 27;

    fetch('data/monitor_saude.json').then(r => r.ok ? r.json() : null).then(sa => {
      const res = (sa || {}).resumo || {};
      const verificadas = res.verificadas;
      if (verificadas == null) return;        /* sem o numero, fica o texto de reserva */
      const parcial = verificadas >= TODAS
        ? ''
        : (C.texto('imprensa.calculo.saude_parcial', { n: verificadas }) || '');
      const t = C.texto('imprensa.calculo.saude', { parcial: parcial });
      porDado(document.getElementById('calculoSaude'), t && t.replace(/\s+$/, ''));
    }).catch(() => {});

    fetch('data/cadencia_publicacao.json').then(r => r.ok ? r.json() : null).then(cad => {
      const vezes = (cad || {}).publicacoes_por_dia;
      if (!vezes) return;                     /* zero nao vira frase: fica o texto de reserva */
      porDado(document.getElementById('perguntaFrequencia'),
              C.texto('imprensa.perguntas.entender.5', { n: vezes }));
    }).catch(() => {});
  });
})();
