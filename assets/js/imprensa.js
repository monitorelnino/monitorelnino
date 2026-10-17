/* imprensa.html (reforma de 17/10/2026, HANDOVER_IMPRENSA_16-10-2026).
   Regra 0 da página: nada escrito à mão que dependa do dado. "Esta semana no MARÉ" é desenhada a
   partir de data/imprensa/semana.json (gerado por gerar_imprensa_semana.py): os seis cartões, na
   ordem do handover, e o texto da semana (`texto_pronto`). Cartão ausente no dado ou sem coleta
   mostra a lacuna da classe, nunca zero nem travessão. */
function _erroImp(onde) { return function (e) { try { console.error("[MARÉ] falha em " + onde + ":", e); } catch (_) {} }; }

window.addEventListener('load', function(){ if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} } });

const SEMANA_CARTOES = ['decretos_na_semana', 'reconhecimentos_na_semana', 'populacao_decretos_na_semana',
  'planos_na_semana', 'municipios_aviso_inmet', 'municipios_alerta_cemaden'];

/* Número de cartão: zero por extenso; pessoas em mil ou milhões com uma casa. */
function valorDoCartao(c) {
  const v = Number(c.valor);
  if (v === 0) return 'zero';
  const umaCasa = x => x.toLocaleString('pt-BR', {minimumFractionDigits: 1, maximumFractionDigits: 1});
  if (c.unidade === 'pessoas' && v >= 1e6) return umaCasa(Math.round(v / 1e5) / 10) + ' milhões';
  if (c.unidade === 'pessoas' && v >= 1e3) return umaCasa(Math.round(v / 1e2) / 10) + ' mil';
  return v.toLocaleString('pt-BR');
}

(function semana() {
  const grade = document.getElementById('semanaCartoes'), texto = document.getElementById('semanaTexto');
  if (!grade || !texto) return;
  const C = window.MonitorCatalogo;
  const rotulo = id => (C && C.texto && C.texto(id)) || '';
  const linha = (cls, t) => { const p = document.createElement('p'); p.className = cls; p.textContent = t; return p; };
  const lacuna = () => rotulo('imprensa.semana.sem_coleta') || 'sem coleta até o corte';

  Promise.all([fetch('data/imprensa/semana.json').then(r => r.ok ? r.json() : null), C && C.pronto]).then(([S]) => {
    const porId = {}; ((S || {}).cartoes || []).forEach(c => { porId[c.id] = c; });
    const edicao = ((S || {}).indices || {}).edicao || '';
    SEMANA_CARTOES.forEach(id => {
      const c = porId[id], tem = c && !c.sem_coleta && c.valor != null;
      const el = document.createElement('div');
      el.className = 'cartao-numero cartao-numero--' + ((c && c.grupo) || 'preparacao');
      el.dataset.cartao = id;
      el.appendChild(linha('cartao-numero-rotulo', (c && c.rotulo) || rotulo('imprensa.semana.' + id)));
      const v = linha('cartao-numero-valor', tem ? valorDoCartao(c) : lacuna());
      v.id = 'semana_' + id;
      el.appendChild(v);
      const f = linha('cartao-numero-fonte', '');
      f.id = 'semanaFonte_' + id;
      el.appendChild(f);
      grade.appendChild(el);
      /* Data do cartão: a da consulta, quando o dado a traz; senão a da edição. */
      const data = String((c && c.consultado_em) || '').match(/^\d{2}\/\d{2}\/\d{4}/);
      if (window.MonitorMapas) MonitorMapas.credito(f.id, {fontes: (c && c.fonte) || '', data: tem ? (data ? data[0] : edicao) : null});
    });
    const pars = String((S || {}).texto_pronto || '').split(/\n\s*\n/).map(s => s.trim()).filter(Boolean);
    (pars.length ? pars : [lacuna()]).forEach((t, i, a) => texto.appendChild(linha(i === a.length - 1 ? 'u-mb-0' : '', t)));
  }).catch(_erroImp('imprensa:semana'));
})();

/* Referência completa: "Edição de" é a data da edição do site; "Acesso em", a de hoje, de quem lê. */
(function referencia() {
  const põe = (id, v) => { const e = document.getElementById(id); if (e && v) e.textContent = v; };
  fetch('data/meta.json').then(r => r.ok ? r.json() : null).then(M => {
    if (M) põe('relData2', M.atualizado_em || M.corte);
  }).catch(_erroImp('imprensa:referencia'));
  const hoje = new Date();
  põe('citarAcesso', String(hoje.getDate()).padStart(2, '0') + '/'
    + String(hoje.getMonth() + 1).padStart(2, '0') + '/' + hoje.getFullYear());
})();
