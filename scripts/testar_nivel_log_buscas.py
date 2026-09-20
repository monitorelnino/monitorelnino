#!/usr/bin/env python3
"""Autoteste do vocabulário controlado de `nivel` em log_buscas.json (19/09/2026).

Motivo: o ensaio da rodada antecipada de 19/09/2026 derrubou o portão obrigatório
`verificar_consistencia.py` com "log_buscas[22208]: nivel inválido: municipal". A chamada de
`log_busca()` que registra a REDAÇÃO de dados pessoais num documento preservado
(coletores_base.py, §LGPD art. 6º, III) passava nivel="municipal", valor que nunca existiu no
vocabulário controlado — bug latente desde 12/09/2026, que só dispara quando o documento
preservado contém CPF a redigir, e que por isso não aparecia nos portões rodados sobre o dado
já commitado.

Os testes abaixo são NEGATIVOS por construção: t1 falha se "municipal" voltar a ser aceito
como nível (o vocabulário não pode ser afrouxado para acomodar o bug), e t2 falha se a chamada
de redação voltar a passar um nível fora do vocabulário.
"""
import ast
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from coletores_base import rodar_autoteste  # noqa: E402

NIVEIS_ESPERADOS = {None, "nacional", "estadual", "municipal_completo"}


def _niveis_do_portao():
    """Lê _NIVEIS de verificar_consistencia.py sem importar o módulo (que roda ao importar)."""
    fonte = (RAIZ / "verificar_consistencia.py").read_text(encoding="utf-8")
    m = re.search(r"^\s*_NIVEIS\s*=\s*(\{[^}]*\})", fonte, re.M)
    assert m, "_NIVEIS não localizado em verificar_consistencia.py"
    return set(ast.literal_eval(m.group(1)))


def _niveis_passados_a_log_busca():
    """Todo literal nivel=... nas chamadas de log_busca() em coletores_base.py."""
    fonte = (RAIZ / "coletores_base.py").read_text(encoding="utf-8")
    arvore = ast.parse(fonte)
    achados = []
    for no in ast.walk(arvore):
        if not isinstance(no, ast.Call):
            continue
        alvo = no.func.id if isinstance(no.func, ast.Name) else getattr(no.func, "attr", None)
        if alvo != "log_busca":
            continue
        for kw in no.keywords:
            if kw.arg == "nivel" and isinstance(kw.value, ast.Constant):
                achados.append(kw.value.value)
    return achados


def t1():
    """O vocabulário controlado não foi afrouxado para aceitar 'municipal'."""
    niveis = _niveis_do_portao()
    return niveis == NIVEIS_ESPERADOS and "municipal" not in niveis


def t2():
    """Nenhuma chamada de log_busca() em coletores_base.py passa nível fora do vocabulário."""
    passados = _niveis_passados_a_log_busca()
    return bool(passados) and all(v in NIVEIS_ESPERADOS for v in passados)


def t3():
    """A chamada da redação de dados pessoais existe e usa nivel=None (sem nível territorial).

    Não pode virar 'municipal_completo': esse valor tem sentido próprio no §2.1 (bateria
    municipal completa) e o portão exige municipio e uf estruturados junto dele.
    """
    fonte = (RAIZ / "coletores_base.py").read_text(encoding="utf-8")
    arvore = ast.parse(fonte)
    for no in ast.walk(arvore):
        if not isinstance(no, ast.Call):
            continue
        alvo = no.func.id if isinstance(no.func, ast.Name) else getattr(no.func, "attr", None)
        if alvo != "log_busca":
            continue
        # a chamada da redação é a que monta `resultados` com esse texto (f-string → JoinedStr)
        if "redação de dados pessoais" not in ast.unparse(no):
            continue
        niveis = [kw.value for kw in no.keywords if kw.arg == "nivel"]
        return (len(niveis) == 1
                and isinstance(niveis[0], ast.Constant)
                and niveis[0].value is None)
    return False


sys.exit(rodar_autoteste({
    "vocabulário de nivel intacto (não aceita 'municipal')": t1,
    "log_busca() em coletores_base.py só usa níveis do vocabulário": t2,
    "log da redação de dados pessoais usa nivel=None": t3,
}))
