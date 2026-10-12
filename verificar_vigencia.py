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
3) SÓ O ANO ("2026", "2025/2026") — A3-29, 12/10/2026: o ato caiu em algum dia entre 1º/01 do
   último ano citado e min(31/12, hoje). Se até o dia mais antigo possível está a <= 180 dias,
   "ativo"; se até o mais recente passou de 180, "prazo_tipico_vencido"; no meio, o ano não
   decide e grava-se "sem_data_de_dia" (não "indeterminada": a data existe, falta o dia).
   Registro que não é decreto perde `vigencia` (resquício de reclassificação).
   `vigencia_em` = dia em que a vigência mudou pela última vez (não o dia da rodada).
Efeito no site: o campo `vigencia` acompanha o registro na tabela e na consulta.
Uso: python3 verificar_vigencia.py [--check]
"""
import datetime, json, pathlib, re, sys
# §227: a data vem da REDAÇÃO, não do runner (que roda em UTC). A rodada de sábado 22h40
# em Brasília já é domingo em UTC, e o carimbo gravado em data/ sairia um dia adiante do que o
# leitor brasileiro viu.
from coletores_base import hoje_editorial, gravar  # noqa: E402

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


def intervalo_por_ano(s, hoje):
    """(mais_antiga, mais_recente) possíveis para data só com ano, ou None. Função pura."""
    anos = re.fullmatch(r"\s*(\d{4})(?:\s*/\s*(\d{4}))?\s*", s or "")
    if not anos:
        return None
    ano = int(anos.group(2) or anos.group(1))
    if ano > hoje.year:
        return None
    return datetime.date(ano, 1, 1), min(datetime.date(ano, 12, 31), hoje)


def classificar(data, hoje):
    """(vigencia, data_norm|None) de um decreto. Função pura: não lê nem grava nada."""
    d = parse_data_br(data)
    if d is not None:
        return ("ativo" if (hoje - d).days <= LIMIAR else "prazo_tipico_vencido"), d.isoformat()
    faixa = intervalo_por_ano(data, hoje)
    if faixa is None:
        return "indeterminada", None
    antiga, recente = faixa
    if (hoje - antiga).days <= LIMIAR:
        return "ativo", None
    if (hoje - recente).days > LIMIAR:
        return "prazo_tipico_vencido", None
    return "sem_data_de_dia", None


def _autoteste():
    h = datetime.date(2026, 10, 12)
    casos = [
        ("12/09/2026", ("ativo", "2026-09-12")),
        ("01/01/2026", ("prazo_tipico_vencido", "2026-01-01")),
        ("2026", ("sem_data_de_dia", None)),
        ("2025/2026", ("sem_data_de_dia", None)),
        ("2024", ("prazo_tipico_vencido", None)),
        ("2027", ("indeterminada", None)),
        ("", ("indeterminada", None)),
        ("sem data", ("indeterminada", None)),
    ]
    falhas = [(e, classificar(e, h), s) for e, s in casos if classificar(e, h) != s]
    ok_ativo = classificar("2026", datetime.date(2026, 3, 1)) == ("ativo", None)
    for f in falhas:
        print("  ✗", f)
    print(("  ✓ " if ok_ativo else "  ✗ ") + "ano corrente no começo do ano: ativo")
    import dis
    escreve = any(i.argval in ("gravar", "open") for i in dis.get_instructions(classificar))
    print(("  ✗ " if escreve else "  ✓ ") + "trava: classificar não lê nem grava")
    if falhas or not ok_ativo or escreve:
        print("✗ AUTOTESTE: falhou"); return 1
    print(f"✓ AUTOTESTE OK — {len(casos) + 2} casos, sem rede e sem escrita.")
    return 0


def main():
    """Percorre os decretos do banco, classifica cada um em ativo, prazo_tipico_vencido ou indeterminada pela data extraída, e grava o campo vigencia; roda a cada atualização, sem expirar registro por conta própria."""
    mun = json.load(open(RAIZ / "data" / "municipios.json", encoding="utf-8"))
    if "--check" in sys.argv:
        n = sum(1 for m in mun if m.get("categoria") == "decreto" and "vigencia" in m)
        por_ano = sum(1 for m in mun if m.get("categoria") == "decreto"
                      and m.get("vigencia") == "indeterminada"
                      and intervalo_por_ano(m.get("data"), hoje_editorial()))
        print(f"OK vigência automática presente em {n} decretos · {por_ano} indeterminadas por "
              f"data só com ano")
        return 1 if por_ano else 0
    hoje = hoje_editorial()
    cont = {}
    for m in mun:
        if m.get("categoria") != "decreto":
            m.pop("vigencia", None); m.pop("vigencia_em", None); continue
        vig, norm = classificar(m.get("data"), hoje)
        if m.get("vigencia") != vig or "vigencia_em" not in m:
            m["vigencia_em"] = hoje.isoformat()
        m["vigencia"] = vig
        if norm:
            m["data_norm"] = norm
        else:
            m.pop("data_norm", None)
        cont[vig] = cont.get(vig, 0) + 1
    ativo, vencido = cont.get("ativo", 0), cont.get("prazo_tipico_vencido", 0)
    indet = cont.get("indeterminada", 0)
    # §229: municipios.json é o banco do projeto. Esta é a SEGUNDA porta que o gravava direto no
    # destino (a outra era processar_contribuicoes.py), e as duas rodam no ciclo diário.
    gravar("municipios.json", mun)
    velho = RAIZ / "data" / "vigencia_revisar.json"
    if velho.exists(): velho.unlink()
    print(f"OK vigência automática: {ativo} ativos · {vencido} prazo típico vencido · "
          f"{cont.get('sem_data_de_dia', 0)} sem data de dia · {indet} indeterminadas (sem fila manual)")
    return 0


if __name__ == "__main__":
    sys.exit(_autoteste() if "--autoteste" in sys.argv else main())
