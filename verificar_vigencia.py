#!/usr/bin/env python3
"""Vigência AUTOMÁTICA (governança de 27/08/2026: sem fila humana; roda em toda
atualização do índice, antes do recálculo).

1) PARSER DE DATAS BRASILEIRAS IMPERFEITAS, com regra conservadora declarada:
   "dd/mm/aaaa" -> exata; "mm/aaaa" -> último dia do mês (conservador: menor
   idade possível); "dd/mm e dd/mm/aaaa" ou listas -> a data MAIS RECENTE;
   "mm-mm/aaaa" (intervalo de meses) -> último dia do mês final. O campo
   original nunca é sobrescrito: grava-se `data_norm` (ISO) ao lado.
2) REGRA DE VIGÊNCIA (apenas categoria decreto; jamais toca pontuação, que é
   zero por Correção B): idade <= 180 dias -> vigencia "ativo"; acima ->
   "prazo_tipico_vencido" (rótulo honesto: prazo TÍPICO de SE; o ato pode ter
   sido prorrogado, e a varredura de revogação/prorrogação do Querido Diário
   corrige em execuções futuras). Sem data parseável -> "indeterminada".
Efeito no site: o campo `vigencia` acompanha o registro na tabela e na consulta.
Uso: python3 verificar_vigencia.py [--check]
"""
import datetime, json, pathlib, re, sys

RAIZ = pathlib.Path(__file__).parent
LIMIAR = 180
ULT = {1:31,2:28,3:31,4:30,5:31,6:30,7:31,8:31,9:30,10:31,11:30,12:31}


def parse_data_br(s):
    """Retorna date ou None. Regra conservadora documentada no cabeçalho."""
    if not s: return None
    s = s.strip()
    completas = re.findall(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if completas:
        ds = []
        for d, m, a in completas:
            try: ds.append(datetime.date(int(a), int(m), int(d)))
            except ValueError: pass
        if ds: return max(ds)
    m = re.fullmatch(r"(\d{1,2})/(\d{4})", s)
    if m:
        mes, ano = int(m.group(1)), int(m.group(2))
        if 1 <= mes <= 12: return datetime.date(ano, mes, ULT[mes])
    m = re.fullmatch(r"(\d{1,2})\s*[-a]\s*(\d{1,2})/(\d{4})", s)
    if m:
        mes, ano = int(m.group(2)), int(m.group(3))
        if 1 <= mes <= 12: return datetime.date(ano, mes, ULT[mes])
    return None


def main():
    """Percorre os decretos do banco, classifica cada um em ativo, prazo_tipico_vencido ou indeterminada pela data extraída, e grava o campo vigencia; roda a cada atualização, sem expirar registro por conta própria."""
    mun = json.load(open(RAIZ / "data" / "municipios.json", encoding="utf-8"))
    if "--check" in sys.argv:
        n = sum(1 for m in mun if m.get("categoria") == "decreto" and "vigencia" in m)
        print(f"OK vigência automática presente em {n} decretos"); return 0
    hoje = datetime.date.today()
    ativo = vencido = indet = 0
    for m in mun:
        if m.get("categoria") != "decreto": continue
        d = parse_data_br(m.get("data"))
        if d is None:
            m["vigencia"] = "indeterminada"; m.pop("data_norm", None); indet += 1; continue
        m["data_norm"] = d.isoformat()
        if (hoje - d).days <= LIMIAR:
            m["vigencia"] = "ativo"; ativo += 1
        else:
            m["vigencia"] = "prazo_tipico_vencido"; vencido += 1
    json.dump(mun, open(RAIZ / "data" / "municipios.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    velho = RAIZ / "data" / "vigencia_revisar.json"
    if velho.exists(): velho.unlink()
    print(f"OK vigência automática: {ativo} ativos · {vencido} prazo típico vencido · {indet} indeterminadas (fila humana extinta)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
