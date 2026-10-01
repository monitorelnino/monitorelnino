const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
// ===== imprensa.html · bloco 1 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
(function(){
  fetch('data/indice.json').then(r=>r.json()).then(idx=>{ const ufs=Object.keys(idx).filter(k=>k.length===2); const tot=ufs.map(u=>idx[u].total); const media=Math.round(tot.reduce((a,b)=>a+b,0)/27*10)/10; const txt=media.toLocaleString('pt-BR',{minimumFractionDigits:1});
    const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = String(v); };
    set('relMedia', txt);
    // 16/09/2026 (pedido da editoria): o site não ranqueia nem compara estados entre si — o release não
    // nomeia mais os dois primeiros e os dois últimos por nota (removido: ord/relTopo/relBase).
    fetch('data/resposta/por_uf.json').then(r => r.ok ? r.json() : null).then(R => { if (!R) return; const N = R.nacional;
      set('relDecretados', N.n_municipios.toLocaleString('pt-BR')); set('relReconhecidos', (N.reconhecidos ?? '—').toLocaleString('pt-BR')); set('relPrimeiroDecreto', N.primeiro_decreto || '—');
      set('relPopMilhoes', ((N.pop_sob_decreto || 0) / 1e6).toFixed(1).replace('.', ','));
      // 16/09/2026 (handover): relQ1/relQ3 são CONTAGENS de estados num cruzamento antecipação × resposta — nunca
      // nomeiam qual estado (a editoria vetou nomear/ordenar estados por posição em 16/09, §73); computado ao vivo
      // de indice.json + resposta/por_uf.json, sem depender de um arquivo dedicado (o antigo resposta/quadrantes.json
      // foi removido no mesmo pedido).
      fetch('data/indice.json').then(rr => rr.ok ? rr.json() : null).then(IDX => { if (!IDX) return;
        const ufsR = Object.keys(R.uf); let q1 = 0, q3 = 0;
        ufsR.forEach(uf => { const idxUf = (IDX[uf] || {}).total; const fr = R.uf[uf].fracao_municipios || 0;
          if (idxUf == null || fr <= 0.05) return; if (idxUf >= 50) q1++; else q3++; });
        set('relQ1', q1); set('relQ3', q3);
      }).catch(() => {});
    }).catch(() => {});
    fetch('data/calendario/fontes_suspensas.json').then(r => r.ok ? r.json() : null).then(F => { if (!F) return;
      set('relSuspensas', Object.values(F.fontes || {}).filter(f => f.suspensa).length);
    }).catch(() => {});
    // 15/09/2026: mais números do release lidos do dado — planos municipais (percentual_uf.n_plano), estados com plano do ciclo (estados.json)
    fetch('data/percentual_uf.json').then(r => r.ok ? r.json() : null).then(P => { if (!P) return; const n = Object.values(P).reduce((a, i) => a + (i.n_plano || 0), 0).toLocaleString('pt-BR'); set('relPlanosMun', n); }).catch(() => {});
    fetch('data/estados.json').then(r => r.ok ? r.json() : null).then(E => { if (!E) return; const c = k => (E.ufs || []).filter(u => k.includes(u.status)); const ufsDe = k => c(k).map(u => u.uf).sort().join(', ');
      ['relNovo', 'relNovo2'].forEach(i => set(i, c(['NOVO']).length)); set('relNovoUFs', ufsDe(['NOVO'])); set('relTodoAno', c(['VIG']).length); set('relElab', c(['ELAB']).length); set('relLacUFs', ufsDe(['LAC']) || 'nenhum'); }).catch(() => {});
  }).catch(()=>{});
  // 16/09/2026 (pedido da editoria): "O que mudou" (feed + relDataAnterior) saiu da página — bloco removido.
  fetch('data/meta.json').then(r=>r.json()).then(m=>{ (document.getElementById('relCorte')||{}).textContent=m.corte||'—'; document.getElementById('relData').textContent=(m.atualizado_em||m.corte||'');
     (document.getElementById('relData2')||{}).textContent=(m.atualizado_em||m.corte||'');
  }).catch(()=>{});
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

// ===== imprensa.html · "Esta semana em números" (§253, 27/09/2026) =====
// Números vêm de data/imprensa/semana.json, gerado por gerar_imprensa_semana.py. Texto fixo no
// HTML nunca contém número — o portão scripts/verificar_imprensa.py confere a paridade entre o
// que a página mostra e o que o dado diz. Zero é zero; sem coleta é "sem coleta", nunca zero.
(function () {
  const fmt = v => {
    if (v === null || v === undefined) return 'sem coleta';
    if (typeof v === 'number' && !Number.isInteger(v)) return v.toFixed(1).replace('.', ',');
    if (typeof v === 'number') return v.toLocaleString('pt-BR');
    return String(v);
  };
  const dia = iso => {
    if (!iso) return null;
    const p = String(iso).slice(0, 10).split('-');
    return p.length === 3 ? p[2] + '/' + p[1] : String(iso);
  };

  fetch('data/imprensa/semana.json').then(r => r.ok ? r.json() : null).then(S => {
    if (!S || !S.cartoes) return;

    const dlg = document.getElementById('detalheSemana');
    const dlgTitulo = document.getElementById('detalheSemanaTitulo');
    const dlgCorpo = document.getElementById('detalheSemanaCorpo');
    const fechar = document.getElementById('detalheSemanaFechar');
    if (fechar && dlg) fechar.addEventListener('click', () => dlg.close());

    S.cartoes.forEach(c => {
      const valor = document.querySelector('[data-imprensa="' + c.id + '"]');
      if (valor) valor.textContent = c.sem_coleta ? 'sem coleta' : fmt(c.valor);

      // O rótulo de um cartão pode trazer a escala da fonte (ex.: EAQI e o limiar), que é dado.
      const titulo = document.querySelector('[data-imprensa-titulo="' + c.id + '"]');
      if (titulo && c.rotulo) titulo.textContent = c.rotulo;

      // Período, fonte e hora da consulta: o cartão não existe sem eles.
      const meta = document.querySelector('[data-imprensa-meta="' + c.id + '"]');
      if (meta) {
        // O portão 19 proíbe travessão como pontuação de frase, e os campos `fonte` e `documento`
        // do dado trazem travessão ("INMET — avisos ativos..."). Troca na APRESENTAÇÃO, por
        // vírgula; o dado fica como a fonte o entregou.
        const semTravessao = t => String(t).replace(/\s+—\s+/g, ', ').replace(/—/g, ',');
        // 01/10/2026: UMA linha, "Fonte · data", e nada mais. Saíram "primeira medição", a nota
        // de critério e o nome do arquivo: são bastidor da coleta, não o que a redação precisa ler
        // para citar o número. O período continua visível onde ele importa — no rótulo do cartão e
        // no texto pronto abaixo da grade.
        const partes = [];
        if (c.fonte) partes.push(String(c.fonte).split(/\s*[—(]/)[0].trim());
        const quando = c.consultado_em || (c.periodo && c.periodo.fim && dia(c.periodo.fim));
        if (quando) partes.push(String(quando).replace('T', ' '));
        meta.textContent = partes.map(semTravessao).join(' · ') || 'sem dado';
      }

      const botao = document.querySelector('[data-imprensa-lista="' + c.id + '"]');
      if (botao) {
        if (!c.lista || !c.lista.length) { botao.hidden = true; return; }
        botao.hidden = false;
        botao.addEventListener('click', () => {
          if (!dlg) return;
          dlgTitulo.textContent = c.rotulo || c.id;
          dlgCorpo.innerHTML = c.lista.map(item => {
            const chave = [item.municipio, item.capital, item.uf].filter(Boolean).join(' · ');
            const detalhe = [];
            if (item.valor !== undefined) detalhe.push(fmt(item.valor));
            if (item.data) detalhe.push(dia(item.data));
            if (item.causa) detalhe.push(item.causa);
            if (item.documento) detalhe.push(item.documento);
            if (item.hora) detalhe.push(item.hora);
            const alvo = item.url
              ? '<a href="' + esc(item.url) + '" target="_blank" rel="noopener">' + esc(detalhe.join(' · ') || 'documento') + '</a>'
              : esc(detalhe.join(' · '));
            return '<dt>' + esc(chave) + '</dt><dd>' + alvo + '</dd>';
          }).join('');
          dlg.showModal();
        });
      }
    });

    const frase = document.getElementById('semanaTextoPronto');
    if (frase && S.texto_pronto) frase.textContent = S.texto_pronto;

    // Os cartões que o handover pede e que o dado ainda não sustenta ficam DECLARADOS, com o
    // motivo — silêncio aqui viraria a impressão de que nada falta.
    const faltam = document.getElementById('semanaNaoCalculaveis');
    if (faltam && (S.nao_calculaveis || []).length) {
      faltam.hidden = false;
      faltam.textContent = 'Ainda sem dado que os sustente: '
        + S.nao_calculaveis.map(x => x.rotulo).join(' · ') + '.';
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
      if (res.verificadas != null) põe('topoSaudeNota', 'média de ' + res.verificadas + ' estados verificados');
    }
    if (sa.versao != null) põe('citarVersaoSaude', String(sa.versao));
  }).catch(() => {});

  fetch('data/percentual_uf.json').then(r => r.ok ? r.json() : null).then(P => {
    if (!P) return;
    põe('topoPlanos', n(Object.values(P).reduce((a, i) => a + (i.n_plano || 0), 0)));
  }).catch(() => {});

  fetch('data/resposta/por_uf.json').then(r => r.ok ? r.json() : null).then(R => {
    if (R && R.nacional) põe('topoDecretos', n(R.nacional.n_municipios));
  }).catch(() => {});

  // Os dois contadores semanais são os mesmos cartões de "Esta semana em números": mesma janela,
  // mesma fonte, mesmo critério. Dois números iguais na mesma página com contas diferentes seria
  // o defeito que a regra 0 existe para impedir.
  fetch('data/imprensa/semana.json').then(r => r.ok ? r.json() : null).then(S => {
    if (!S || !S.cartoes) return;
    const de = id => (S.cartoes.find(c => c.id === id) || {}).valor;
    const planos = de('planos_no_periodo'), decretos = de('decretos_no_periodo');
    if (planos != null) põe('topoPlanosSemana', n(planos));
    if (decretos != null) põe('topoDecretosSemana', n(decretos));
  }).catch(() => {});

  fetch('data/meta.json').then(r => r.ok ? r.json() : null).then(M => {
    if (!M) return;
    ['relData', 'relData2'].forEach(i => põe(i, M.atualizado_em || M.corte));
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
