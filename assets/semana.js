// A SEMANA EPIDEMIOLÓGICA VIRA INTERVALO DE DATAS — e só o intervalo vai ao leitor.
// ==============================================================================
//
// Item 0 do handover "MARÉ Saúde: correção completa da página" (07/10/2026), regra da editoria
// para o SITE INTEIRO: o leitor não sabe o que é semana epidemiológica. Nenhuma página, legenda,
// eixo, tooltip, cartão ou texto gerado mostra "semana epidemiológica", "SE", "SE 33" nem
// "202637". O dado continua sendo coletado e guardado por semana — isso é da fonte, e não muda;
// o que muda é o que se escreve na tela.
//
// A REGRA, que é do Ministério da Saúde e não nossa: a semana vai de DOMINGO a SÁBADO, e a
// semana 1 de um ano é a primeira que tem PELO MENOS QUATRO DIAS de janeiro.
//
// "Pelo menos quatro dias de janeiro" tem uma forma mais curta e exata de calcular: numa semana
// que começa no domingo, o quarto dia é a QUARTA-FEIRA. Então a semana 1 é aquela cuja
// quarta-feira cai em janeiro — e, como só uma quarta-feira por ano cai entre os dias 1 e 7, ela
// é única. É assim que o cálculo abaixo é feito: acha-se a quarta-feira de 1 a 7 de janeiro, e o
// domingo dela é o começo da semana 1.
(function (raiz) {
  "use strict";

  const DIA = 86400000;
  const MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
                 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
  const MES_CURTO = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun',
                     'jul', 'ago', 'set', 'out', 'nov', 'dez'];

  /** O domingo em que começa a semana 1 do ano. Função pura, em UTC para não pegar fuso. */
  function domingoDaSemana1(ano) {
    // A quarta-feira entre 1 e 7 de janeiro: `getUTCDay()` dá 3 na quarta.
    for (let dia = 1; dia <= 7; dia++) {
      const d = new Date(Date.UTC(ano, 0, dia));
      if (d.getUTCDay() === 3) return new Date(d.getTime() - 3 * DIA);
    }
    return null;   // inalcançável: toda semana de sete dias tem uma quarta-feira
  }

  /** {inicio, fim} da semana `n` do `ano`, como Date em UTC. Função pura. */
  function semanaParaDatas(ano, n) {
    const num = Number(n);
    if (!Number.isInteger(num) || num < 1 || num > 53) return null;
    const base = domingoDaSemana1(Number(ano));
    if (!base) return null;
    const inicio = new Date(base.getTime() + (num - 1) * 7 * DIA);
    // Semana 53 só existe quando ela ainda pertence ao ano: se o começo dela já caiu no ano
    // seguinte pela regra dos quatro dias, o ano não tem 53 semanas e o pedido é inválido.
    if (num === 53) {
      const proxima = domingoDaSemana1(Number(ano) + 1);
      if (proxima && inicio.getTime() >= proxima.getTime()) return null;
    }
    return {inicio: inicio, fim: new Date(inicio.getTime() + 6 * DIA)};
  }

  /** "de 9 a 15 de agosto de 2026" · "de 30 de agosto a 5 de setembro de 2026". Pura. */
  function porExtenso(ano, n, comPreposicao) {
    const r = semanaParaDatas(ano, n);
    if (!r) return null;
    const di = r.inicio.getUTCDate(), mi = r.inicio.getUTCMonth(), ai = r.inicio.getUTCFullYear();
    const df = r.fim.getUTCDate(), mf = r.fim.getUTCMonth(), af = r.fim.getUTCFullYear();
    const pre = comPreposicao === false ? '' : 'de ';
    if (ai !== af) return pre + di + ' de ' + MESES[mi] + ' de ' + ai + ' a ' + df + ' de ' + MESES[mf] + ' de ' + af;
    if (mi !== mf) return pre + di + ' de ' + MESES[mi] + ' a ' + df + ' de ' + MESES[mf] + ' de ' + ai;
    return pre + di + ' a ' + df + ' de ' + MESES[mi] + ' de ' + ai;
  }

  /** "9–15/ago" — forma curta, para tooltip e eixo. Pura. */
  function curta(ano, n) {
    const r = semanaParaDatas(ano, n);
    if (!r) return null;
    const di = r.inicio.getUTCDate(), mi = r.inicio.getUTCMonth();
    const df = r.fim.getUTCDate(), mf = r.fim.getUTCMonth();
    return mi === mf ? di + '–' + df + '/' + MES_CURTO[mi]
                     : di + '/' + MES_CURTO[mi] + '–' + df + '/' + MES_CURTO[mf];
  }

  /** O mês em que a semana começa — é o rótulo do eixo horizontal dos gráficos semanais. Pura. */
  function mesDaSemana(ano, n) {
    const r = semanaParaDatas(ano, n);
    return r ? MES_CURTO[r.inicio.getUTCMonth()] : null;
  }

  /** "15 de agosto de 2026", do fim da semana — serve aos acumulados. Pura. */
  function fimPorExtenso(ano, n) {
    const r = semanaParaDatas(ano, n);
    if (!r) return null;
    return r.fim.getUTCDate() + ' de ' + MESES[r.fim.getUTCMonth()] + ' de ' + r.fim.getUTCFullYear();
  }

  /** dd/mm/aaaa do início da semana. Pura. */
  function inicioBR(ano, n) {
    const r = semanaParaDatas(ano, n);
    if (!r) return null;
    const p = v => String(v).padStart(2, '0');
    return p(r.inicio.getUTCDate()) + '/' + p(r.inicio.getUTCMonth() + 1) + '/' + r.inicio.getUTCFullYear();
  }

  const API = {semanaParaDatas, porExtenso, curta, mesDaSemana, fimPorExtenso, inicioBR,
               domingoDaSemana1, MESES, MES_CURTO};
  if (typeof module === 'object' && module.exports) module.exports = API;
  raiz.MonitorSemana = API;
})(typeof window !== 'undefined' ? window : globalThis);
