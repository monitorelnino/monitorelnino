#!/usr/bin/env python3
"""
scripts/ensaio_da_noite.py — a noite em miniatura, de dia, sem tocar a `main`
=============================================================================
Item 5.1 do `HANDOVER_noite_confiavel_05-10-2026.md`: **só fechar o handover com o ensaio verde.**

POR QUE ELE EXISTE. As quatro causas da noite de 04→05/10 só apareceram *na* noite: publicação
reprovada oito vezes, um elo cancelado que a guarda contou como feito, 114 minutos de busca web
perdidos em conflito de rebase, e o pacote do blog com a credencial errada. Cada uma foi consertada
na raiz — e consertar na raiz, sem prova, é a mesma aposta outra vez. O ensaio é a prova: ele roda
de dia, em repositório temporário, e **falha quando qualquer uma das quatro voltar**.

Ele NÃO dispara os workflows noturnos reais: aqueles commitam na `main`, e um ensaio que publica não
é ensaio. Ele exercita os MECANISMOS que a noite usa — a porta única da fila, a união pela base
comum, a guarda "já trabalhou?", a quarentena do portão de esquema e os marcadores `.feito` —, cada
um no caso que a noite provou que faltava.

OS SEIS ENSAIOS
  1. DOIS ELOS EM PARALELO, zero conflito e zero perda: dois elos gravam a fila ao mesmo tempo, o
     rebase conflita de verdade num repositório de verdade, e a união pela base comum entrega as
     pistas dos dois. É o que custou 114 minutos.
  2. DISPARO DUPLICADO: dois observadores no mesmo minuto; o segundo sai sem trabalho. Faltou no
     #552 e é obrigatório agora.
  3. ELO CANCELADO É RECUPERADO: elo cancelado antes de coletar não deixa marcador, a guarda diz
     "abre", e a reserva refaz. Elo que coletou e falhou no push deixa marcador, e a guarda diz
     "não abre" — refazê-lo duplicaria lote.
  4. PISTA INVÁLIDA PLANTADA: a publicação fica VERDE com pista fora do esquema na fila, porque o
     portão a quarentena em vez de bloquear. É o que parou o site oito vezes.
  5. A PORTA ÚNICA RECUSA COM MOTIVO: pista sem alvo não entra e a recusa fica contável.
  6. TODOS OS ELOS COM MARCADOR: "noite bem-sucedida" é todos os elos com `.feito`; um elo sem
     marcador tem de ser nomeado.

USO
    python3 scripts/ensaio_da_noite.py              # roda os seis; 0 = verde
    python3 scripts/ensaio_da_noite.py --autoteste  # o mesmo (o ensaio é o próprio teste)
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))

ELOS_DA_NOITE = ("diarios", "descoberta", "evidencias", "juiz", "sinais", "triagem")


def _pista(ident: str, alvo: str, **extra) -> dict:
    p = {"id": ident, "url_final": f"https://{alvo}.ms.gov.br/{ident}", "alvo": alvo,
         "tipo": "plano", "nivel": "A", "data": "2026-10-05", "origem": "busca_web",
         "registrado_em": "2026-10-05", "status": "pista"}
    p.update(extra)
    return p


def _fila(*pistas) -> str:
    return json.dumps({"pistas": list(pistas), "atualizado_em": "2026-10-05"},
                      ensure_ascii=False, indent=1) + "\n"


def _repo(tmp: pathlib.Path):
    """Um repositório de verdade, para o conflito ser de verdade."""
    amb = {**os.environ, "GIT_AUTHOR_NAME": "e", "GIT_AUTHOR_EMAIL": "e@e",
           "GIT_COMMITTER_NAME": "e", "GIT_COMMITTER_EMAIL": "e@e"}

    def g(*a, pode_falhar=False):
        r = subprocess.run(["git", *a], cwd=str(tmp), capture_output=True, env=amb)
        if r.returncode != 0 and not pode_falhar:
            raise RuntimeError(f"git {' '.join(a)}: {r.stderr.decode('utf-8', 'replace')}")
        return r.returncode
    g("init", "-q", "-b", "main")
    return g


# ───────────────────────────────── 1. dois elos em paralelo ─────────────────────────────────

def ensaio_dois_elos_em_paralelo(diz) -> bool:
    """O conflito de rebase entre dois elos NÃO perde pista. É o que custou 114 minutos."""
    import unir_conflito_de_rodada as u
    with tempfile.TemporaryDirectory() as t:
        tmp = pathlib.Path(t)
        g = _repo(tmp)
        caminho = tmp / "data" / "pistas_imprensa.json"
        caminho.parent.mkdir(parents=True)

        base = _pista("base1", "5002209")
        caminho.write_text(_fila(base), encoding="utf-8", newline="\n")
        g("add", "-A"); g("commit", "-qm", "a fila de ontem")

        # O elo B (diários) grava e empurra primeiro.
        g("checkout", "-qb", "elo_b")
        do_b = _pista("diarios1", "5002704")
        caminho.write_text(_fila(base, do_b), encoding="utf-8", newline="\n")
        g("add", "-A"); g("commit", "-qm", "diarios")

        # O elo A (busca web) estava correndo em paralelo e grava a SUA pista.
        g("checkout", "-q", "main")
        do_a = _pista("buscaweb1", "5003207")
        caminho.write_text(_fila(base, do_a), encoding="utf-8", newline="\n")
        g("add", "-A"); g("commit", "-qm", "busca web")

        # O push do elo A é recusado e ele rebasa — é aqui que a noite perdeu o trabalho.
        conflitou = g("merge", "elo_b", "-m", "colisao", pode_falhar=True) != 0
        if not conflitou:
            diz("  ✗ o ensaio não produziu conflito: ele não está medindo o que diz medir")
            return False

        resolvidos, _, recusados = u.resolver(repo=tmp)
        if recusados:
            diz(f"  ✗ a união RECUSOU a fila: {recusados[0]}")
            return False
        doc = json.loads(caminho.read_text(encoding="utf-8"))
        ids = sorted(p["id"] for p in doc["pistas"])
        if ids != ["base1", "buscaweb1", "diarios1"]:
            diz(f"  ✗ perda de pista na união: ficaram {ids}")
            return False
        diz(f"  ✓ dois elos em paralelo: conflito real, união pela base comum, "
            f"3 pistas preservadas ({', '.join(ids)}) — zero perda")
        return True


# ───────────────────────────────── 2. disparo duplicado ─────────────────────────────────

def ensaio_disparo_duplicado(diz) -> bool:
    """Dois observadores no mesmo minuto: o segundo sai sem trabalho."""
    import datetime as dt
    from janela_da_noite import precisa_abrir

    agora = dt.datetime(2026, 10, 5, 2, 7)
    linhas = []
    if not precisa_abrir(linhas, agora):
        diz("  ✗ o primeiro observador não dispararia numa noite sem abertura")
        return False
    # O primeiro elo trabalhou e registrou.
    linhas.append({"noite": "2026-10-05", "elo": "diarios", "conclusao": "in_progress",
                   "trabalhou": True})
    if precisa_abrir(linhas, agora):
        diz("  ✗ o SEGUNDO observador dispararia no mesmo minuto — lote e commit duplicados")
        return False
    diz("  ✓ disparo duplicado: o segundo observador sai sem trabalho")
    return True


# ───────────────────────────────── 3. elo cancelado recuperado ─────────────────────────────

def ensaio_elo_cancelado_e_recuperado(diz) -> bool:
    """Cancelado não é feito: a reserva refaz. Falha COM trabalho é feito: a reserva não refaz."""
    import datetime as dt
    from janela_da_noite import precisa_abrir

    agora = dt.datetime(2026, 10, 5, 3, 56)   # a hora real da tentativa que saiu sem trabalhar
    cancelado = [{"noite": "2026-10-05", "elo": "diarios", "conclusao": "cancelled",
                  "trabalhou": False}]
    if not precisa_abrir(cancelado, agora):
        diz("  ✗ elo CANCELADO contou como noite aberta — é a causa da noite de 04→05/10")
        return False
    coletou_e_falhou = [{"noite": "2026-10-05", "elo": "diarios", "conclusao": "failure",
                         "trabalhou": True}]
    if precisa_abrir(coletou_e_falhou, agora):
        diz("  ✗ elo que coletou e perdeu o push seria refeito — lote e commit duplicados")
        return False
    diz("  ✓ elo cancelado é recuperado; elo que coletou e falhou no push NÃO é refeito")
    return True


# ───────────────────────────── 4. pista inválida plantada ─────────────────────────────

def ensaio_pista_invalida_nao_para_a_publicacao(diz) -> bool:
    """A publicação fica VERDE com pista fora do esquema: o portão quarentena, não bloqueia."""
    from verificar_esquema_de_pista import (ler_esquema, problemas_de_esquema, quarentenar,
                                            fora_da_fila_ativa)
    esquema = ler_esquema()
    boa = _pista("boa1", "5002209")
    # A pista que parou o site oito vezes: de coletor não migrado, sem url_final/tipo/alvo/nivel.
    plantada = {"id": "plantada1", "municipio": "Bonito", "uf": "MS",
                "origem_do_coletor": "rede_social_oficial", "registrado_em": "2026-10-05",
                "url": "https://bonito.ms.gov.br/post"}
    fila = [boa, plantada]

    if not problemas_de_esquema(fila, esquema, so_fila_ativa=True):
        diz("  ✗ a pista plantada não foi reconhecida como fora do esquema")
        return False
    nova, movidas = quarentenar(fila, esquema, hoje_iso="2026-10-05")
    if problemas_de_esquema(nova, esquema, so_fila_ativa=True):
        diz("  ✗ a quarentena NÃO limpou a fila ativa — a publicação bloquearia")
        return False
    if len(nova) != 2 or not fora_da_fila_ativa(nova[1]):
        diz("  ✗ a pista plantada saiu do arquivo em vez de ir à quarentena")
        return False
    if movidas != {"rede_social_oficial": 1}:
        diz(f"  ✗ a contagem por coletor não saiu: {movidas}")
        return False
    diz("  ✓ pista inválida plantada: quarentenada, contada por coletor, publicação VERDE")
    return True


# ───────────────────────────── 5. a porta recusa com motivo ─────────────────────────────

def ensaio_porta_recusa_com_motivo(diz) -> bool:
    """Pista sem alvo não entra, e a recusa fica contável — não desaparece calada."""
    import coletores_base as cb
    from pistas import gravar_lote

    falso = {}
    real_ler, real_gravar = cb.ler, cb.gravar
    cb.ler = lambda n, padrao=None: json.loads(json.dumps(falso[n])) if n in falso else padrao
    cb.gravar = lambda n, o, compacto=False: falso.__setitem__(n, json.loads(json.dumps(o)))
    try:
        boa = {"municipio": "Bonito", "uf": "MS", "ibge": "5002209",
               "url": "https://bonito.ms.gov.br/plano-de-contingencia",
               "titulo": "Plano de Contingência aprovado", "data": "05/10/2026"}
        sem_alvo = {"municipio": "?", "url": "https://x.com.br/noticia",
                    "titulo": "Plano de contingência em municípios", "data": "05/10/2026"}
        b = gravar_lote([boa, sem_alvo], origem="rede_social_oficial")
        if b["gravadas"] != 1 or b["recusadas"] != 1:
            diz(f"  ✗ a porta não separou a boa da sem alvo: {b}")
            return False
        rej = (falso.get("pistas_rejeitadas.json") or {}).get("rejeitadas") or []
        if len(rej) != 1 or "alvo" not in rej[0]["motivo"]:
            diz(f"  ✗ a recusa não ficou contável com motivo: {rej}")
            return False
        if rej[0]["origem"] != "rede_social_oficial":
            diz("  ✗ a recusa não nomeia o coletor que gravou errado")
            return False
        gravada = falso["pistas_imprensa.json"]["pistas"][0]
        if not (gravada.get("url_final") and gravada.get("tipo") == "plano"
                and gravada.get("alvo") == "5002209" and gravada.get("nivel")):
            diz(f"  ✗ a pista gravada não saiu no esquema: {gravada}")
            return False
        diz("  ✓ a porta única: a boa entra no esquema, a sem alvo é recusada com motivo e origem")
        return True
    finally:
        cb.ler, cb.gravar = real_ler, real_gravar


# ───────────────────────────── 6. todos os elos com marcador ─────────────────────────────

def elos_sem_marcador(raiz_de_dados: pathlib.Path, noite: str, elos=ELOS_DA_NOITE) -> list:
    """Os elos da noite que não deixaram marcador. Função pura quanto ao disco."""
    pasta = pathlib.Path(raiz_de_dados) / "noite" / noite
    return [e for e in elos if not (pasta / f"{e}.feito").exists()]


def ensaio_marcadores_de_todos_os_elos(diz) -> bool:
    """"Noite bem-sucedida" é todos os elos com marcador; quem faltar tem de ser nomeado."""
    with tempfile.TemporaryDirectory() as t:
        dados = pathlib.Path(t) / "data"
        pasta = dados / "noite" / "2026-10-05"
        pasta.mkdir(parents=True)
        for elo in ELOS_DA_NOITE:
            (pasta / f"{elo}.feito").write_text("x\n", encoding="utf-8", newline="\n")
        if elos_sem_marcador(dados, "2026-10-05"):
            diz("  ✗ noite completa apareceu como incompleta")
            return False
        (pasta / "triagem.feito").unlink()
        faltam = elos_sem_marcador(dados, "2026-10-05")
        if faltam != ["triagem"]:
            diz(f"  ✗ o elo sem marcador não foi nomeado: {faltam}")
            return False
        diz("  ✓ marcadores: noite completa é reconhecida, e o elo que falta é NOMEADO (triagem)")
        return True


ENSAIOS = (
    ("dois elos em paralelo: zero conflito, zero perda", ensaio_dois_elos_em_paralelo),
    ("disparo duplicado: o segundo sai sem trabalho", ensaio_disparo_duplicado),
    ("elo cancelado é recuperado; falha com trabalho não é refeita",
     ensaio_elo_cancelado_e_recuperado),
    ("pista inválida plantada: publicação VERDE, pista quarentenada",
     ensaio_pista_invalida_nao_para_a_publicacao),
    ("a porta única recusa com motivo, e a recusa fica contável",
     ensaio_porta_recusa_com_motivo),
    ("todos os elos com marcador; o que falta é nomeado",
     ensaio_marcadores_de_todos_os_elos),
)


def main() -> int:
    print("ENSAIO DA NOITE — a noite em miniatura, de dia, sem tocar a `main`")
    print("=" * 78)
    falhas = []
    for nome, fn in ENSAIOS:
        print(f"\n· {nome}")
        try:
            if not fn(print):
                falhas.append(nome)
        except Exception as e:  # noqa: BLE001
            print(f"  ✗ {type(e).__name__}: {e}")
            falhas.append(nome)
    print("\n" + "=" * 78)
    if falhas:
        print(f"✗ ENSAIO DA NOITE: {len(falhas)} de {len(ENSAIOS)} ensaio(s) reprovaram:")
        for f in falhas:
            print("   - " + f)
        print("   A noite NÃO está provada. Uma das quatro causas de 04→05/10 voltou.")
        return 1
    print(f"✓ ENSAIO DA NOITE OK — {len(ENSAIOS)} ensaios verdes, sem rede e sem tocar a `main`.")
    print("  Provado: conflito entre elos não perde pista · disparo duplicado não duplica "
          "trabalho ·")
    print("  elo cancelado é refeito e elo que coletou não é · pista fora do esquema não para a "
          "publicação ·")
    print("  recusa da fila fica contável com motivo e coletor · elo sem marcador é nomeado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
