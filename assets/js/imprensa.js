const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
// ===== imprensa.html · release da edição (handover de 01/10/2026) =====
// O release é o texto aprovado, e todo número dele vem do banco — inclusive os da SEMANA, que são
// os MESMOS cartões da grade acima: mesma janela, mesma fonte, mesmo critério. Dois números iguais
// na mesma página com contas diferentes é o defeito que a regra 0 existe para impedir.
(function releaseDaEdicao(){
  /* O release VEM PRONTO de data/imprensa/semana.json (`texto_pronto`). A versao anterior montava
     a frase no HTML, com um `<span>` por numero, e as regras de redacao do handover — frase sem
     dado omitida, concordancia com o numero, populacao arredondada — ficavam espalhadas entre o
     HTML e tres blocos de JS. Agora ha um autor so, com autoteste: o motor. */
  const alvo = document.getElementById('releaseTexto');
  if (!alvo) return;
  fetch('data/imprensa/semana.json').then(r => r.ok ? r.json() : null).then(S => {
    const texto = (S || {}).texto_pronto;
    if (!texto) { alvo.innerHTML = '<p class="u-muted">Release não carregado nesta edição.</p>'; return; }
    alvo.innerHTML = texto.split(/\n\s*\n/).map(p => '<p>' + esc(p) + '</p>').join('');
  }).catch(() => {});
})();

(function(){
  const ul = document.getElementById('listaNaoSuspenso'); const ul2 = document.getElementById('listaSuspenso'); if (!ul && !ul2) return;
  fetch('data/calendario/dispositivos.json').then(r => r.ok ? r.json() : null).then(D => {
    if (!D || !Array.isArray(D.nao_suspenso)) { if (ul) ul.innerHTML = '<li class="u-muted">Lista não carregada; ver o calendário eleitoral.</li>'; return; }
    if (ul) ul.innerHTML = D.nao_suspenso.map(x => '<li><strong>' + esc(x.item) + ':</strong> ' + esc(x.base) + '</li>').join('');
  }).catch(() => { if (ul) ul.innerHTML = '<li class="u-muted">Lista não carregada; ver o calendário eleitoral.</li>'; });
})();

window.addEventListener('load', function(){ if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} } });

// 14/09/2026 (pedido de Patricia, 13/09): "O que a lei deixa aberto" vira nota para a imprensa — mesma fonte e o
// mesmo desenho de linha da página do calendário (data/calendario/dispositivos.json, campo nao_suspenso).
(function(){
  const ul = document.getElementById('listaNaoSuspenso'); const ul2 = document.getElementById('listaSuspenso'); if (!ul && !ul2) return;
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  fetch('data/calendario/dispositivos.json').then(r => r.ok ? r.json() : null).then(D => {
    if (!D || !Array.isArray(D.nao_suspenso)) { if (ul) ul.innerHTML = '<li class="u-muted">Lista não carregada; ver o calendário eleitoral.</li>'; if (ul2) ul2.innerHTML = '<li class="u-muted">Lista não carregada.</li>'; return; }
    if (ul) ul.innerHTML = D.nao_suspenso.map(x => '<li><strong>' + esc(x.item) + ':</strong> ' + esc(x.base) + ' <span class="u-muted">(' + esc(x.status) + ')</span></li>').join('');
    if (ul2 && Array.isArray(D.dispositivos)) ul2.innerHTML = D.dispositivos.filter(x => x.bloqueia && x.bloqueia !== '—').map(x => '<li><strong>' + esc(x.bloqueia.split('.')[0].split(', nos')[0]) + '</strong> <span class="u-muted">(' + esc(x.dispositivo) + ')</span></li>').join('');
  }).catch(() => { if (ul) ul.innerHTML = '<li class="u-muted">Lista não carregada; ver o calendário eleitoral.</li>'; if (ul2) ul2.innerHTML = '<li class="u-muted">Lista não carregada.</li>'; });
})();

// 30/09/2026: o calendário compacto da imprensa saiu do código, com as outras duas telas de
// calendário (decisão da editoria). O que ele mostrava vive na METODOLOGIA.

// ===== imprensa.html · "Esta semana em números" (handover de 01/10/2026) =====
// A grade é DESENHADA a partir de data/imprensa/semana.json, na ordem dos grupos que o arquivo
// declara. Não há cartão escrito no HTML: é assim que a regra 0 da página ("nada escrito à mão que
// dependa do dado") deixa de depender de vigilância e passa a ser estrutural.
//
// Variação ao lado do número, com seta e valor, SEM cor de bom/ruim: a página não diz ao leitor se
// subir é bom. Cartão sem coleta mostra "sem dado nesta edição" e o motivo — nunca zero.
(function gradeDaSemana(){
  const alvo = document.getElementById('gradeSemana');
  if (!alvo) return;
  /* Como cada numero e escrito, e por que:
     - DINHEIRO em reais, abreviado como no Financiamento ("R$ 150,9 mi"): o valor ao centavo num
       cartao de topo ocupa a largura toda e nao se le de relance;
     - POPULACAO arredondada em milhao, com uma casa — foi o que a editoria pediu, e o inteiro daria
       precisao que o recorte nao tem;
     - ZERO por extenso ("nenhum ato", "nenhum plano"): "0 planos publicados" se le como falha de
       sistema, e "nenhum plano publicado" se le como o fato que e. R$ 0 fica R$ 0, porque ali o
       zero e de dinheiro e se le sem tropeco. */
  const ZERO_POR_EXTENSO = {
    planos_na_semana: 'nenhum plano', atos_federais_semana: 'nenhum ato',
    mudaram_faixa: 'nenhum estado', decretos_na_semana: 'nenhum município',
    reconhecimentos_na_semana: 'nenhum município', populacao_decretos_na_semana: 'ninguém',
    municipios_alerta_cemaden: 'nenhum município', municipios_aviso_inmet: 'nenhum município',
    decreto_e_alerta_ao_mesmo_tempo: 'nenhum município', focos_24h: 'nenhum foco',
    capitais_ar_ruim_ou_pior: 'nenhuma capital', ufs_dengue_alerta: 'nenhum estado',
  };
  const reais = v => {
    const abs = Math.abs(v);
    if (abs >= 1e9) return 'R$ ' + (v / 1e9).toFixed(1).replace('.', ',') + ' bi';
    if (abs >= 1e6) return 'R$ ' + (v / 1e6).toFixed(1).replace('.', ',') + ' mi';
    if (abs >= 1e3) return 'R$ ' + (v / 1e3).toFixed(1).replace('.', ',') + ' mil';
    return 'R$ ' + v.toLocaleString('pt-BR', {maximumFractionDigits: 0});
  };
  const milhoes = v => v >= 1e6
    ? (v / 1e6).toFixed(1).replace('.', ',') + (v < 2e6 ? ' milhão' : ' milhões')
    : v.toLocaleString('pt-BR');
  const fmtCartao = c => {
    const v = c.sem_coleta ? null : c.valor;
    if (v === null || v === undefined) return 'sem dado nesta edição';
    if (v === 0 && ZERO_POR_EXTENSO[c.id]) return ZERO_POR_EXTENSO[c.id];
    if (c.unidade === 'reais') return reais(Number(v));
    if (c.unidade === 'pessoas') return milhoes(Number(v));
    if (c.unidade === '°C') return (v > 0 ? '+' : '') + String(v).replace('.', ',') + ' °C';
    if (typeof v === 'number' && !Number.isInteger(v)) return v.toFixed(1).replace('.', ',');
    if (typeof v === 'number') return v.toLocaleString('pt-BR');
    return String(v);
  };
  const fmt = v => {
    if (v === null || v === undefined) return 'sem dado nesta edição';
    if (typeof v === 'number' && !Number.isInteger(v)) return v.toFixed(1).replace('.', ',');
    if (typeof v === 'number') return v.toLocaleString('pt-BR');
    return String(v);
  };
  const dia = iso => {
    if (!iso) return null;
    const p = String(iso).slice(0, 10).split('-');
    return p.length === 3 ? p[2] + '/' + p[1] : String(iso);
  };
  const semTravessao = t => String(t).replace(/\s+—\s+/g, ', ').replace(/—/g, ',');
  const GRUPOS = [['preparacao', 'Preparação'], ['emergencias', 'Emergências'],
                  ['risco_agora', 'Risco agora'], ['dinheiro', 'Dinheiro'], ['saude', 'Saúde']];

  fetch('data/imprensa/semana.json').then(r => r.ok ? r.json() : null).then(S => {
    if (!S || !S.cartoes) return;
    const dlg = document.getElementById('detalheSemana');
    const dlgTitulo = document.getElementById('detalheSemanaTitulo');
    const dlgCorpo = document.getElementById('detalheSemanaCorpo');
    const fechar = document.getElementById('detalheSemanaFechar');
    if (fechar && dlg) fechar.addEventListener('click', () => dlg.close());

    const linhaDeFonte = c => {
      const partes = [];
      if (c.fonte && c.fonte !== '—') partes.push(String(c.fonte).split(/\s*[—(]/)[0].trim());
      const quando = c.consultado_em || (c.periodo && c.periodo.fim && dia(c.periodo.fim));
      if (quando) partes.push(String(quando).replace('T', ' '));
      return partes.map(semTravessao).join(' · ');
    };
    const variacao = c => {
      if (c.variacao === null || c.variacao === undefined) return '';
      const seta = c.variacao > 0 ? '↑' : (c.variacao < 0 ? '↓' : '=');
      const n = Math.abs(c.variacao).toLocaleString('pt-BR');
      return '<span class="cartao-numero-variacao">' + seta + ' ' + n
        + '<span class="sr-only"> em relação à semana anterior</span></span>';
    };

    GRUPOS.forEach(([chave, titulo]) => {
      /* Cartao sem dado SAI da grade (handover de 02/10): um cartao que diz "sem dado nesta edicao"
         e explica a razao tecnica ocupa um terco da linha para nao informar nada. O rotulo dele vai
         para a linha unica abaixo dos grupos, que e onde a lacuna fica legivel sem roubar o lugar
         de um numero. */
      const cartoes = S.cartoes.filter(c => c.grupo === chave && !c.sem_coleta);
      if (!cartoes.length) return;
      const bloco = document.createElement('div');
      bloco.className = 'imprensa-grupo';
      bloco.innerHTML = '<p class="selo">' + esc(titulo) + '</p>'
        + '<div class="grade-numeros grade-numeros--3"></div>';
      const grade = bloco.querySelector('.grade-numeros');
      cartoes.forEach(c => {
        const cartao = document.createElement('div');
        cartao.className = 'cartao-numero cartao-numero--' + chave;
        cartao.dataset.cartao = c.id;
        cartao.innerHTML =
          '<p class="cartao-numero-valor">' + esc(fmtCartao(c)) + '</p>'
          + variacao(c)
          + '<p class="cartao-numero-rotulo">' + esc(c.rotulo || c.id) + '</p>'
          + '<p class="cartao-numero-fonte">' + esc(linhaDeFonte(c) || (c.nota || '')) + '</p>';
        if (c.lista && c.lista.length && dlg) {
          const b = document.createElement('button');
          b.type = 'button';
          b.className = 'link-pequeno';
          b.textContent = 'Ver quais';
          b.addEventListener('click', () => {
            dlgTitulo.textContent = c.rotulo || c.id;
            dlgCorpo.innerHTML = c.lista.map(item => {
              const chaveItem = [item.municipio, item.nome, item.uf].filter(Boolean).join(' · ');
              const detalhe = [];
              if (item.valor !== undefined) detalhe.push(fmt(item.valor));
              if (item.data) detalhe.push(dia(item.data));
              if (item.causa) detalhe.push(item.causa);
              if (item.documento) detalhe.push(item.documento);
              const texto = detalhe.join(' · ');
              const alvoItem = item.url
                ? '<a href="' + esc(item.url) + '" target="_blank" rel="noopener">'
                  + esc(texto || 'documento') + '</a>'
                : esc(texto);
              return '<dt>' + esc(chaveItem) + '</dt><dd>' + alvoItem + '</dd>';
            }).join('');
            dlg.showModal();
          });
          cartao.appendChild(b);
        }
        grade.appendChild(cartao);
      });
      alvo.appendChild(bloco);
    });

    // O que o handover pede e o dado ainda não sustenta fica DECLARADO: silêncio aqui viraria a
    // impressão de que nada falta.
    const faltam = document.getElementById('semanaNaoCalculaveis');
    const sem = S.cartoes.filter(c => c.sem_coleta);
    const baixar = document.getElementById('baixarNumeros');
    if (baixar && S.gerado_em) baixar.href = 'dados-abertos/imprensa/numeros-' + S.gerado_em + '.csv';
    if (faltam && sem.length) {
      faltam.hidden = false;
      faltam.textContent = 'Sem dado nesta edição: ' + sem.map(c => c.rotulo).join(' · ') + '.';
    }
  }).catch(() => {});
})();

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
