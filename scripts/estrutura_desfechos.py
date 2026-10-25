"""Estrutura comum dos arquivos de desfechos de saúde (data/saude_desfechos/<desfecho>.json).

Funções puras para a série por UF, a faixa habitual 2019–2025 por quintis congelados, o último
valor, os cortes do mapa e o documento final. A escrita e a leitura são injetadas (`gravar_fn`,
`ler_fn`) e o autoteste roda sem tocar em data/. Arquivo existente nunca é sobrescrito aqui: a
página atual continua lendo o que já existe até a seção nova entrar.

Ausência de dado é lacuna declarada (uf fora de `serie`), nunca zero.
"""
from __future__ import annotations

import bisect
import json
import os
import sys

ANOS_FAIXA = (2019, 2025)
PASTA = os.path.join("data", "saude_desfechos")
CADENCIAS = {"dia", "semana", "mes", "ano"}
SCHEMA = "estrutura_desfechos/1"
CAMPOS_OBRIGATORIOS = ("desfecho", "fonte", "cadencia", "preliminar", "parcial", "ate", "serie", "ultimo")


def quintis(valores) -> list | None:
    """Cortes p0, p20, p40, p60, p80, p100 por interpolação linear. None com menos de cinco valores."""
    v = sorted(float(x) for x in valores if isinstance(x, (int, float)) and not isinstance(x, bool))
    if len(v) < 5:
        return None
    cortes = []
    for k in range(6):
        pos = (len(v) - 1) * k / 5
        i = int(pos)
        frac = pos - i
        cortes.append(v[i] if i + 1 >= len(v) else v[i] + (v[i + 1] - v[i]) * frac)
    return cortes


def classe_no_quintil(valor, cortes) -> int | None:
    """1 (mais baixo) a 5 (mais alto) pelos cortes congelados; None sem valor ou sem cortes."""
    if not isinstance(valor, (int, float)) or isinstance(valor, bool) or not cortes or len(cortes) != 6:
        return None
    return min(5, max(1, bisect.bisect_right(cortes[1:5], valor) + 1))


def serie_por_uf(registros, campo_uf, campo_periodo, campo_valor) -> dict:
    """{UF: {periodo: valor}}. Registro sem valor numérico não entra: ausência continua ausência."""
    out: dict = {}
    for r in registros:
        uf, per, val = r.get(campo_uf), r.get(campo_periodo), r.get(campo_valor)
        if not uf or per is None or not isinstance(val, (int, float)) or isinstance(val, bool):
            continue
        out.setdefault(uf, {})[per] = val
    return out


def faixa_habitual(serie: dict, anos=ANOS_FAIXA) -> dict:
    """Quintis congelados sobre todos os pares UF×período de `anos` (inclusive)."""
    lo, hi = anos
    valores = [v for uf in serie.values() for per, v in uf.items() if isinstance(per, int) and lo <= per <= hi]
    return {"anos": [lo, hi], "cortes": quintis(valores), "n": len(valores)}


def ultimo_valor(serie_uf: dict):
    """(periodo, valor) do período mais recente da UF, ou None."""
    if not serie_uf:
        return None
    per = max(serie_uf)
    return per, serie_uf[per]


def cortes_do_mapa(serie: dict, faixa: dict) -> dict:
    """{UF: classe 1–5} do último valor de cada UF. UF sem dado não aparece."""
    out = {}
    for uf, s in serie.items():
        u = ultimo_valor(s)
        if u is not None:
            c = classe_no_quintil(u[1], faixa.get("cortes"))
            if c is not None:
                out[uf] = c
    return out


def montar_documento(desfecho, fonte, cadencia, serie, ate, preliminar: bool, parcial: bool,
                     ufs_esperadas=()) -> dict:
    """Documento final. `ate` é o último período consolidado (ano, mês ou semana, conforme a cadência)."""
    if not desfecho or not fonte or cadencia not in CADENCIAS:
        raise ValueError("desfecho, fonte e cadencia (dia|semana|mes|ano) são obrigatórios")
    faixa = faixa_habitual(serie)
    ultimo = {}
    for uf, s in serie.items():
        u = ultimo_valor(s)
        if u is not None:
            ultimo[uf] = {"periodo": u[0], "valor": u[1], "classe": classe_no_quintil(u[1], faixa["cortes"])}
    lacuna = sorted(set(ufs_esperadas) - set(serie))
    return {
        "schema": SCHEMA,
        "desfecho": desfecho,
        "fonte": fonte,
        "cadencia": cadencia,
        "ate": ate,
        "preliminar": bool(preliminar),
        "parcial": bool(parcial),
        "faixa_habitual": faixa,
        "serie": serie,
        "ultimo": ultimo,
        "mapa": cortes_do_mapa(serie, faixa),
        "lacuna_ufs": lacuna,
    }


def validar_documento(doc: dict) -> list:
    """Lista de problemas (vazia = válido). Esquema, não conteúdo."""
    erros = [f"falta {c}" for c in CAMPOS_OBRIGATORIOS if c not in doc]
    if doc.get("schema") != SCHEMA:
        erros.append("schema diferente")
    if doc.get("cadencia") not in CADENCIAS:
        erros.append("cadencia inválida")
    for uf, s in (doc.get("serie") or {}).items():
        if not isinstance(s, dict) or any(not isinstance(v, (int, float)) or isinstance(v, bool) for v in s.values()):
            erros.append(f"série inválida em {uf}")
    return erros


def _caminho_permitido(caminho: str) -> bool:
    return os.path.dirname(os.path.normpath(caminho)) == os.path.normpath(PASTA) and caminho.endswith(".json")


def gravar_documento(caminho: str, doc: dict, gravar_fn=None, existe_fn=None) -> None:
    """Grava arquivo NOVO em data/saude_desfechos/. Recusa arquivo existente e caminho fora da pasta."""
    existe_fn = existe_fn or os.path.exists
    if not _caminho_permitido(caminho):
        raise ValueError(f"caminho fora de {PASTA}: {caminho}")
    if existe_fn(caminho):
        raise FileExistsError(f"arquivo existente não é sobrescrito por esta função: {caminho}")
    erros = validar_documento(doc)
    if erros:
        raise ValueError("; ".join(erros))
    if gravar_fn is None:
        with open(caminho, "w", encoding="utf-8", newline="\n") as f:
            json.dump(doc, f, ensure_ascii=False, indent=1, sort_keys=True)
            f.write("\n")
    else:
        gravar_fn(caminho, doc)


def ler_documento(caminho: str, ler_fn=None) -> dict:
    if ler_fn is not None:
        return ler_fn(caminho)
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def autoteste() -> int:
    """Offline, sem escrita em data/: usa dicionários e falsos."""
    falhas = []

    def ok(cond, nome):
        if not cond:
            falhas.append(nome)

    cortes = quintis([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    ok(cortes is not None and cortes[0] == 1 and cortes[-1] == 10 and len(cortes) == 6, "quintis básicos")
    ok(quintis([1, 2, 3]) is None, "quintis exige cinco valores")
    ok(quintis([1, None, "x", True, 2, 3, 4, 5]) is not None, "quintis ignora não numéricos")
    ok(classe_no_quintil(1, cortes) == 1 and classe_no_quintil(10, cortes) == 5, "classe nos extremos")
    ok(classe_no_quintil(None, cortes) is None and classe_no_quintil(3, None) is None, "classe sem valor")
    ok(classe_no_quintil(99, cortes) == 5 and classe_no_quintil(-99, cortes) == 1, "classe clampada")

    regs = [
        {"uf": "SC", "ano": 2019, "v": 3}, {"uf": "SC", "ano": 2020, "v": None},
        {"uf": "PR", "ano": 2020, "v": 0}, {"uf": "PR", "ano": 2021, "v": True},
        {"uf": "", "ano": 2021, "v": 4},
    ]
    s = serie_por_uf(regs, "uf", "ano", "v")
    ok(s == {"SC": {2019: 3}, "PR": {2020: 0}}, "série: ausência não vira zero; bool e UF vazia descartados")
    ok(ultimo_valor(s["PR"]) == (2020, 0), "último valor com zero preservado")
    ok(ultimo_valor({}) is None, "último valor vazio")

    base = {uf: {a: a - 2018 + i for a in range(2019, 2026)} for i, uf in enumerate(["AC", "AL", "AM", "BA", "CE"])}
    fx = faixa_habitual(base)
    ok(fx["n"] == 35 and fx["cortes"] is not None, "faixa habitual usa 2019–2025")
    base["XX"] = {2030: 999}
    ok(faixa_habitual(base)["n"] == 35, "faixa ignora anos fora de 2019–2025")
    mapa = cortes_do_mapa(base, fx)
    ok(set(mapa) == set(base) and mapa["CE"] == 5 and mapa["CE"] > mapa["AC"], "mapa por último valor, pelos cortes")

    doc = montar_documento("dengue_teste", "fonte fictícia de autoteste", "semana", base, 2025,
                           preliminar=True, parcial=False, ufs_esperadas=["AC", "AL", "RR"])
    ok(doc["lacuna_ufs"] == ["RR"], "UF sem dado vira lacuna declarada")
    ok(validar_documento(doc) == [], "documento montado é válido")
    ok(validar_documento({"schema": "outro"}) != [], "esquema inválido reprova")
    try:
        montar_documento("d", "f", "decada", base, 2025, False, False)
        ok(False, "cadência inválida recusada")
    except ValueError:
        pass

    escritas = {}

    def gravar_falso(c, d):
        escritas[c] = d

    gravar_documento(os.path.join(PASTA, "srag_teste.json"), doc, gravar_fn=gravar_falso, existe_fn=lambda c: False)
    ok(list(escritas) == [os.path.join(PASTA, "srag_teste.json")], "gravação de arquivo novo")
    for caminho, existe in [(os.path.join(PASTA, "dengue.json"), True), ("data/outro/x.json", False)]:
        try:
            gravar_documento(caminho, doc, gravar_fn=gravar_falso, existe_fn=lambda c, e=existe: e)
            ok(False, f"recusa de {caminho}")
        except (FileExistsError, ValueError):
            pass
    ok(len(escritas) == 1, "recusas não escrevem")
    lido = ler_documento("x", ler_fn=lambda c: doc)
    ok(lido is doc, "leitura injetada")

    for f in falhas:
        print("FALHOU:", f)
    print(f"autoteste estrutura_desfechos: {'OK' if not falhas else 'FALHOU'} ({len(falhas)} falhas)")
    return 1 if falhas else 0


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        sys.exit(autoteste())
    print(__doc__)
