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



# §184 (23/09/2026): o vocabulário de `decisao`, que é irmão do de `nivel` e tem a mesma armadilha.
# Defeito real: o §181 fez a sonda de camada registrar o silêncio como "nada localizado", valor
# reservado à bateria municipal completa — a chamada quebrava no assert e, se passasse, o portão de
# consistência reprovaria. Nunca rodou porque só dispara em execução com rede.
def t3():
    """'nada localizado' sem bateria municipal completa continua proibido."""
    import coletores_base as cb
    try:
        cb.log_busca("sonda de painéis", 1, ["x.gov.br"], "nada localizado", uf="PR")
        return False
    except AssertionError:
        return True


def t4():
    """'consultado sem achado' é aceito sem nível — é sonda de UF, não verificação municipal."""
    import ast as _ast
    import pathlib as _p
    fonte = (_p.Path(__file__).resolve().parent.parent / "coletores_base.py").read_text(encoding="utf-8")
    arvore = _ast.parse(fonte)
    for no in _ast.walk(arvore):
        if isinstance(no, _ast.FunctionDef) and no.name == "log_busca":
            texto = _ast.get_source_segment(fonte, no) or ""
            return '"consultado"' in texto and '"nada localizado"' not in texto.split("assert")[1][:200]
    return False


def t5():
    """Nenhum script registra 'nada localizado' sem passar nivel='municipal_completo'."""
    import pathlib as _p
    raiz = _p.Path(__file__).resolve().parent.parent
    suspeitos = []
    for arq in list(raiz.glob("*.py")) + list(raiz.glob("scripts/*.py")):
        if arq.name in ("coletores_base.py", "verificar_consistencia.py", "recalcular_mare.py",
                        "migrar_v224_verificacao.py", "testar_nivel_log_buscas.py",
                        "verificar_robustez_atualizacao.py", "gerar_cobertura_declarada.py"):
            continue
        for linha in arq.read_text(encoding="utf-8").split("\n"):
            if '"nada localizado"' in linha and "log_busca" in linha and "municipal_completo" not in linha:
                suspeitos.append(f"{arq.name}: {linha.strip()[:80]}")
    return not suspeitos

sys.exit(rodar_autoteste({"§184 'nada localizado' sem bateria municipal reprova": t3,
                          "§184 'consultado sem achado' entra no vocabulário": t4,
                          "§184 nenhum script loga 'nada localizado' sem o nível": t5,
                          
    "vocabulário de nivel intacto (não aceita 'municipal')": t1,
    "log_busca() em coletores_base.py só usa níveis do vocabulário": t2,
    "log da redação de dados pessoais usa nivel=None": t3,
}))
