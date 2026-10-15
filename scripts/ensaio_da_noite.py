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

        # 15/10/2026 (F58): o livro de fontes também — cada elo marca a SUA fonte no mesmo município.
        livro = tmp / "data" / "fontes_consultadas.json"

        def marca(*fontes):
            return json.dumps({"municipios": {"5002704": {"nivel_verificacao": "nacional",
                               "ultima_verificacao": "2026-10-15", "fontes": [
                                   {"fonte": f, "data": "2026-10-15", "resultado": "r"} for f in fontes]}}})

        base = _pista("base1", "5002209")
        caminho.write_text(_fila(base), encoding="utf-8", newline="\n")
        livro.write_text(marca("DOU"), encoding="utf-8", newline="\n")
        g("add", "-A"); g("commit", "-qm", "a fila de ontem")

        # O elo B (diários) grava e empurra primeiro.
        g("checkout", "-qb", "elo_b")
        do_b = _pista("diarios1", "5002704")
        caminho.write_text(_fila(base, do_b), encoding="utf-8", newline="\n")
        livro.write_text(marca("DOU", "QD"), encoding="utf-8", newline="\n")
        g("add", "-A"); g("commit", "-qm", "diarios")

        # O elo A (busca web) estava correndo em paralelo e grava a SUA pista.
        g("checkout", "-q", "main")
        do_a = _pista("buscaweb1", "5003207")
        caminho.write_text(_fila(base, do_a), encoding="utf-8", newline="\n")
        livro.write_text(marca("DOU", "Busca web"), encoding="utf-8", newline="\n")
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
        fontes = sorted(f["fonte"] for f in json.loads(livro.read_text(encoding="utf-8"))
                        ["municipios"]["5002704"]["fontes"])
        if fontes != ["Busca web", "DOU", "QD"]:
            diz(f"  ✗ o livro de fontes perdeu consulta na união: {fontes} (F58)")
            return False
        # F59: entre a união e o `rebase --continue` não se regenera nada — derivado fora do
        # `git add` deixava a árvore suja e o rebase recusava nas cinco tentativas.
        wf = (pathlib.Path(__file__).resolve().parents[1] / ".github/workflows/_coletor.yml").read_text(encoding="utf-8")
        trecho = wf.split("if python3 scripts/unir_conflito_de_rodada.py; then", 1)[-1].split("git rebase --continue", 1)[0]
        if "verificar_derivados" in trecho:
            diz("  ✗ o coletor regenera derivados entre a união e o `rebase --continue` (F59)")
            return False
        diz(f"  ✓ dois elos em paralelo: conflito real, união pela base comum, "
            f"3 pistas e as 3 consultas do livro preservadas — zero perda")
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


# ─────────────── 7. o carimbo que recusava a noite (A2-02) ───────────────

def ensaio_carimbo_nao_recusa_a_noite(diz) -> bool:
    """`data/saude_pipeline.json` com carimbos distintos nos dois lados UNE.

    É a causa que perdeu a noite de 07→08/10: todo elo commita este arquivo, cada um grava a hora
    em que rodou, e o resolvedor recusava divergência em qualquer escalar. O laço tentava cinco
    vezes a mesma união e desistia; diários, descoberta, juiz e dois sinais foram para artefato.
    """
    import unir_conflito_de_rodada as u
    with tempfile.TemporaryDirectory() as t:
        tmp = pathlib.Path(t)
        g = _repo(tmp)
        caminho = tmp / "data" / "saude_pipeline.json"
        caminho.parent.mkdir(parents=True, exist_ok=True)

        def doc(execucoes, carimbo):
            return json.dumps({"formato_versao": 2, "atualizado_em": carimbo,
                               "execucoes": execucoes}, ensure_ascii=False, indent=1) + "\n"

        base = [{"i": 1}]
        caminho.write_text(doc(base, "2026-10-07T23:00:00"), encoding="utf-8", newline="\n")
        g("add", "-A"); g("commit", "-qm", "ontem")

        g("checkout", "-qb", "elo_b")
        caminho.write_text(doc(base + [{"i": 2}], "2026-10-08T02:40:00"),
                           encoding="utf-8", newline="\n")
        g("add", "-A"); g("commit", "-qm", "juiz")

        g("checkout", "-q", "main")
        caminho.write_text(doc(base + [{"i": 3}], "2026-10-08T01:13:00"),
                           encoding="utf-8", newline="\n")
        g("add", "-A"); g("commit", "-qm", "diarios")

        if g("merge", "elo_b", "-m", "colisao", pode_falhar=True) == 0:
            diz("  ✗ o ensaio não produziu conflito: ele não está medindo o que diz medir")
            return False
        resolvidos, _, recusados = u.resolver(repo=tmp)
        if recusados:
            diz(f"  ✗ o resolvedor RECUSOU o carimbo — é a causa de 07→08 de volta: {recusados[0]}")
            return False
        d = json.loads(caminho.read_text(encoding="utf-8"))
        execucoes = sorted(x["i"] for x in d["execucoes"])
        if execucoes != [1, 2, 3]:
            diz(f"  ✗ perda de execução na união: ficaram {execucoes}")
            return False
        if d.get("atualizado_em") != "2026-10-08T02:40:00":
            diz(f"  ✗ o carimbo não venceu pelo maior: {d.get('atualizado_em')}")
            return False
        diz("  ✓ carimbo distinto nos dois lados: união pela base comum, 3 execuções, "
            "carimbo pelo maior — a noite não se perde")
        return True


# ─────────────── 8. o passo da guarda com o shell do Actions (A2-01) ───────────────

def ensaio_guarda_com_o_shell_do_actions(diz) -> bool:
    """O passo da guarda decide pelo `rc` do script, com `bash -e` e com `bash -eo pipefail`.

    Era aqui que a regra morava e não valia: `if ! cmd | tee` devolve o status do `tee`, que é
    sempre 0, e o Actions roda `bash -e` quando o passo não declara `shell:`. Este ensaio executa
    o passo dos DOIS jeitos e exige a mesma decisão.
    """
    import subprocess
    with tempfile.TemporaryDirectory() as t:
        tmp = pathlib.Path(t)
        falso = tmp / "guarda.py"
        falso.write_text("import sys\nprint('· COLETA ADIADA: fora da janela')\nsys.exit(1)\n",
                         encoding="utf-8", newline="\n")
        passo = tmp / "passo.sh"
        passo.write_text(
            # A forma a prova de `-e`: com `shell: bash` o Actions roda `bash -eo pipefail`,
            # e `cmd; rc=$?` aborta no proprio cmd que falha, antes de ler o rc.
            "rc=0\n"
            'python3 "$1" > /tmp/guarda_ensaio.txt 2>&1 || rc=$?\n'
            'cat /tmp/guarda_ensaio.txt > /dev/null\n'
            'if [ "$rc" -eq 0 ]; then echo pode=1; else echo pode=0; fi\n',
            encoding="utf-8", newline="\n")
        for shell in (["bash", "-e"], ["bash", "-eo", "pipefail"]):
            r = subprocess.run(shell + [str(passo), str(falso)],
                               capture_output=True, text=True, timeout=60)
            if "pode=0" not in r.stdout:
                diz(f"  ✗ com `{' '.join(shell)}` o passo decidiu {r.stdout.strip()!r} — "
                    f"a guarda não barra")
                return False
        # E a forma ANTIGA tem de falhar com `bash -e`: é a prova de que o defeito existia.
        antigo = tmp / "antigo.sh"
        antigo.write_text('if ! python3 "$1" | tee /dev/null; then echo pode=0; else echo pode=1; fi\n',
                          encoding="utf-8", newline="\n")
        r = subprocess.run(["bash", "-e", str(antigo), str(falso)],
                           capture_output=True, text=True, timeout=60)
        if "pode=1" not in r.stdout:
            diz("  ✗ a forma antiga NÃO reproduziu o defeito — o ensaio não está medindo nada")
            return False
        diz("  ✓ o passo da guarda decide pelo `rc` nos dois shells, e a forma antiga "
            "(`if ! cmd | tee`) ainda responde `pode=1` com `bash -e` — defeito reproduzido e "
            "corrigido")
        return True


# ─────────────── 9. publicador: portão vermelho não repõe o domínio (A2-04) ───────────────

def ensaio_portao_vermelho_nao_repoe_o_dominio(diz) -> bool:
    """A condição do deploy, avaliada como o Actions a avalia.

    O passo "Repor o site" tinha `if: always()`: repunha o domínio depois de o portão de dado
    reprovar ou de o push ser cancelado. Aqui a condição é lida do YAML e exercitada nos quatro
    casos que importam.
    """
    fonte = (pathlib.Path(__file__).resolve().parent.parent
             / ".github" / "workflows" / "publicar_dados.yml").read_text(encoding="utf-8")
    i = fonte.find("- name: Repor o site no domínio")
    if i < 0:
        diz("  ✗ não achei o passo que repõe o domínio")
        return False
    bloco = fonte[i:i + 600]
    if "always()" in bloco.split("run:")[0]:
        diz("  ✗ o passo que repõe o domínio ainda tem `always()` — portão vermelho republica")
        return False
    condicao = bloco.split("if:", 1)[1].split("env:")[0] if "if:" in bloco else ""
    for exigido in ("steps.push.outcome == 'success'", "success()"):
        if exigido not in condicao:
            diz(f"  ✗ a condição do deploy não exige {exigido!r}: {' '.join(condicao.split())}")
            return False
    if "houve" not in condicao:
        diz("  ✗ a condição não trata o caso `houve=0` (nada a empurrar, portões verdes)")
        return False
    diz("  ✓ o domínio só se repõe com push bem-sucedido, ou com nada a empurrar e portões "
        "verdes — portão vermelho não republica")
    return True


def ensaio_fila_de_runner_nao_e_falha(diz) -> bool:
    """10. Run à espera de runner conta como noite aberta — nos três lugares que decidem isso.

    A noite de 08→09/10/2026 custou dois elos. Às 01:09 a corrente abriu; às 01:11:03 o vigia
    contou as execuções da janela, o run tinha status `queued` (sem runner ainda), o filtro só
    aceitava `in_progress`, `success` e `failure`, e a conta deu ZERO. O vigia concluiu que a noite
    não havia aberto e disparou a corrente de novo. Com um grupo de concorrência só na `main`, o
    GitHub guarda um run em execução e UM pendente: o terceiro disparo cancelou o pendente.
    Morreram `diarios / coletar` e `triagem / coletar`, os dois antes do primeiro passo, com zero
    passos executados e sem log nenhum.

    Este ensaio reprova se qualquer um dos três decisores voltar a tratar fila como falha: a
    função `painel_da_noite.trabalhou`, o filtro do vigia e o filtro da guarda de abertura. E
    reprova também se `cancelled` ou `skipped` passar a contar — a reserva tem de refazer esses.
    """
    import re
    import pathlib
    import sys

    raiz = pathlib.Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(raiz / "scripts"))
    from painel_da_noite import trabalhou

    ok = True
    for estado in ("queued", "requested", "waiting", "pending", "in_progress"):
        if not trabalhou(estado):
            diz(f"   ✗ `trabalhou({estado})` devolve falso: fila de runner tratada como falha")
            ok = False
    for estado in ("cancelled", "skipped", "timed_out"):
        if trabalhou(estado):
            diz(f"   ✗ `trabalhou({estado})` devolve verdadeiro: a reserva não refaria a coleta")
            ok = False
    if not trabalhou("cancelled", feito=True):
        diz("   ✗ o marcador do elo deixou de vencer a conclusão")
        ok = False

    ESPERA = re.compile(r"queued\|requested\|waiting\|pending\|in_progress")
    for arquivo, quem in ((".github/workflows/vigia_da_abertura.yml", "o vigia"),
                          (".github/workflows/noturno_diarios.yml", "a guarda de abertura")):
        fonte = (raiz / arquivo).read_text(encoding="utf-8")
        if not ESPERA.search(fonte):
            diz(f"   ✗ {quem} ({arquivo}) não conta run na fila de runner como noite aberta")
            ok = False

    vigia = (raiz / ".github/workflows/vigia_da_abertura.yml").read_text(encoding="utf-8")
    if "abertura-atrasada" not in vigia:
        diz("   ✗ o vigia dispara a corrente sem conferir a tolerância da abertura")
        ok = False

    if ok:
        diz("   ✓ fila de runner conta como noite aberta nos três decisores; cancelado e pulado "
            "seguem fora; o vigia só age depois da tolerância")
    return ok


def ensaio_marcador_sobrevive_ao_push(diz) -> bool:
    """11. O marcador do elo sobrevive ao push perdido — e a pergunta tem um dono.

    Noite de 08→09/10/2026, defeito (b). `diarios` (run 37875038703) coletou onze minutos; o laço
    de rebase-e-push do passo 1a falhou nas cinco tentativas; o dado saiu como artefato
    `coleta-perdida-diarios-37875038703`. O marcador `data/noite/<noite>/diarios.feito` era gravado
    na árvore e **chegava à `main` no mesmo commit do dado** — então morreu junto. Para a guarda de
    abertura e para o vigia, aquela coleta nunca aconteceu.

    Reprova se a pergunta "este elo trabalhou?" voltar a ter mais de um dono, se o artefato do
    marcador deixar de ser a segunda prova (ou passar a valer para outro elo ou outra noite), ou
    se o elo deixar de subir o marcador ANTES do commit.
    """
    import pathlib
    import sys

    raiz = pathlib.Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(raiz / "scripts"))
    from marcador_de_elo import nome_do_artefato, trabalhou

    ok = True
    feito, prova = trabalhou("diarios", "2026-10-09", lambda c: True, [])
    if not feito or "árvore" not in prova:
        diz("   ✗ o marcador na árvore deixou de ser prova")
        ok = False
    if not trabalhou("diarios", "2026-10-09", lambda c: False,
                     [nome_do_artefato("diarios", "2026-10-09")])[0]:
        diz("   ✗ push perdido com artefato do marcador NÃO conta como trabalho — a reserva "
            "refaria a coleta e duplicaria o lote")
        ok = False
    for errado in (nome_do_artefato("diarios", "2026-10-08"),
                   nome_do_artefato("juiz", "2026-10-09"),
                   "coleta-perdida-diarios-37875038703"):
        if trabalhou("diarios", "2026-10-09", lambda c: False, [errado])[0]:
            diz(f"   ✗ `{errado}` passou a provar coleta de `diarios` em 2026-10-09")
            ok = False
    if trabalhou("diarios", "2026-10-09", lambda c: False, [])[0]:
        diz("   ✗ sem prova nenhuma o elo conta como trabalhado")
        ok = False

    coletor = (raiz / ".github/workflows/_coletor.yml").read_text(encoding="utf-8")
    if "feito-" not in coletor or "upload-artifact" not in coletor:
        diz("   ✗ o elo não sobe mais o marcador como artefato: push perdido volta a apagá-lo")
        ok = False
    elif coletor.index("Guardar o marcador fora do commit") > coletor.index("item 1a)"):
        diz("   ✗ o marcador sobe DEPOIS do passo de commit — artefato que depende do push não "
            "prova nada")
        ok = False
    for arquivo, quem in ((".github/workflows/noturno_diarios.yml", "a guarda de abertura"),
                          (".github/workflows/vigia_da_abertura.yml", "o vigia")):
        linhas = (raiz / arquivo).read_text(encoding="utf-8").splitlines()
        # A MENÇÃO não basta: o comentário cita o script, e foi assim que o observador do
        # despachante existiu por dias como promessa escrita. O que vale é a CHAMADA.
        if not any("marcador_de_elo.py" in l and not l.strip().startswith("#") for l in linhas):
            diz(f"   ✗ {quem} ({arquivo}) decide sozinha se o elo trabalhou, sem o dono da "
                f"pergunta")
            ok = False

    if ok:
        diz("   ✓ as duas provas valem, só para o elo e a noite certos; o marcador sobe antes do "
            "commit; guarda e vigia usam o mesmo dono")
    return ok


def ensaio_coleta_perdida_volta_para_dentro(diz) -> bool:
    """12. O artefato da coleta perdida é reaplicado pelo elo seguinte.

    Defeito (a), passo 1a. O laço de rebase-e-push guarda o trabalho num artefato quando o push
    morre, e o comentário dele prometia que "o elo seguinte o reaplica
    (`scripts/reaplicar_noite.py`)". O script existia desde 08/10 e **nada o chamava**: os cinco
    artefatos da noite de 08→09 — 18 MB cada, um deles com horas de coleta de diários — ficaram no
    GitHub esperando alguém, e expiram em catorze dias.

    Reprova se nenhum elo chamar a reaplicação, se ela rodar DEPOIS da coleta (o que deixaria o
    reaplicado fora do commit desta noite), se rodar sem escrever, ou se deixar de ser idempotente
    pelo marcador `.reaplicado`.
    """
    import pathlib
    import sys

    raiz = pathlib.Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(raiz / "scripts"))
    from reaplicar_noite import caminho_do_reaplicado, elo_e_run

    ok = True
    coletor = (raiz / ".github/workflows/_coletor.yml").read_text(encoding="utf-8")
    if "reaplicar_noite.py" not in coletor:
        diz("   ✗ nenhum elo reaplica o que a noite perdeu: o artefato fica no GitHub até expirar")
        ok = False
    else:
        if coletor.index("reaplicar_noite.py") > coletor.index("- name: Coletar"):
            diz("   ✗ a reaplicação roda DEPOIS da coleta — o que voltou não entra no commit "
                "desta noite")
            ok = False
        chamadas = [l for l in coletor.splitlines()
                    if "reaplicar_noite.py" in l and "run:" in l]
        if not chamadas:
            diz("   ✗ a reaplicação aparece só em comentário: nenhum passo a executa")
            ok = False
        elif not any("--aplicar" in l for l in chamadas):
            diz("   ✗ a reaplicação roda em modo relatório: ela não escreve nada")
            ok = False

    if elo_e_run("coleta-perdida-sinais-fisicos-37711285165") != ("sinais-fisicos", "37711285165"):
        diz("   ✗ o nome do artefato deixou de ser lido: elo com hífen se partiu")
        ok = False
    if ".reaplicado" not in caminho_do_reaplicado("2026-10-09", "diarios"):
        diz("   ✗ a reaplicação perdeu o marcador de idempotência — cada noite reaplicaria tudo "
            "de novo")
        ok = False
    if ok:
        diz("   ✓ o elo reaplica antes de coletar, com escrita, uma vez só por artefato")
    return ok


def ensaio_despachante_nao_depende_do_cron(diz) -> bool:
    """13. O despachante tem um observador que não passa pelo cron do GitHub.

    Defeito (c). O cabeçalho do `despachante.yml` declara quatro observadores independentes, e o
    segundo — "o relógio da nuvem do Claude, por `relogio.yml` (evento push, não cron)" — **não
    existia na árvore**. Dos quatro, três dependiam do mesmo agendador: o cron do próprio
    despachante, o oportunista (que só roda quando outro workflow AGENDADO roda) e o vigia (cron).
    Quando o cron do GitHub atrasa, caem juntos — e a abertura da noite falhou três vezes em cinco
    dias por isso.

    Reprova se o relógio sem cron desaparecer, se passar a depender de `schedule`, se deixar de
    reagir ao push do ramo `relogio`, se não chamar o despachante, ou se o despachante deixar de
    aceitar disparo externo.
    """
    import pathlib

    raiz = pathlib.Path(__file__).resolve().parents[1]
    ok = True
    relogio = raiz / ".github/workflows/relogio.yml"
    if not relogio.exists():
        diz("   ✗ `relogio.yml` não existe: o observador que não é cron é só uma promessa escrita "
            "no cabeçalho do despachante")
        return False
    fonte = relogio.read_text(encoding="utf-8")
    if "schedule:" in fonte:
        diz("   ✗ o relógio sem cron passou a ter `schedule`: voltou para o mesmo agendador")
        ok = False
    if "branches: [relogio]" not in fonte.replace("'", "").replace('"', ""):
        diz("   ✗ o relógio não reage mais ao push do ramo `relogio`")
        ok = False
    if "despachar_temporizadores.py" not in fonte:
        diz("   ✗ o relógio não chama o despachante — tiquetaquear sozinho não dispara nada")
        ok = False
    despachante = (raiz / ".github/workflows/despachante.yml").read_text(encoding="utf-8")
    if "workflow_dispatch" not in despachante:
        diz("   ✗ o despachante não aceita disparo externo: nenhum observador o alcança")
        ok = False
    if ok:
        diz("   ✓ há um observador por evento `push`, fora do agendador, e ele chama o "
            "despachante")
    return ok


def ensaio_pendente_cancelado_pela_fila_e_refeito(diz) -> bool:
    """14. Pendente cancelado pela fila é refeito — e a fila deixa de cancelar.

    Abertura de 09→10/10: às 01:09–01:10 o despachante disparou vários elos do grupo `noturno`; a
    triagem entrou, os diários ficaram pendentes, e o pendente seguinte os CANCELOU às 01:14, sem
    passo executado (o GitHub guarda um só pendente por grupo). O despachante das 02:26 contou o
    run cancelado como "houve execução na janela" e não refez; os diários só rodaram às 07:42.

    Reprova se: (a) um run cancelado/pulado voltar a contar para o temporizador; (b) a reserva
    deixar de refazer o elo sem marcador cujo run foi cancelado, ou refizer por cima de tentativa
    aberta; (c) a vez na noite deixar três elos simultâneos sem rodar os três, em ordem.
    """
    import datetime as dt
    from despachar_temporizadores import esta_devido, plano_da_reserva
    from vez_na_noite import quem_vem_antes

    ok = True
    agora = dt.datetime(2026, 10, 10, 2, 26)
    t = {"id": "abertura-da-noite", "workflow": "noturno_diarios.yml",
         "janela": {"inicio_utc": "01:00", "fim_utc": "09:00"}, "cron_primario": "7 1 * * *"}
    cancelado = {"createdAt": "2026-10-10T01:10:45Z", "status": "completed",
                 "conclusion": "cancelled"}
    if not esta_devido(t, [cancelado], agora):
        diz("   ✗ o temporizador conta o run cancelado na fila como execução da janela")
        ok = False
    r = plano_da_reserva({"noturno_diarios.yml": [cancelado]}, set(), agora)
    if [x.get("elo") for x in r] != ["diarios"]:
        diz("   ✗ a reserva não refaz o elo sem marcador cujo run foi cancelado na fila")
        ok = False
    aberto = {"createdAt": "2026-10-10T02:20:00Z", "status": "queued"}
    if plano_da_reserva({"noturno_diarios.yml": [cancelado, aberto]}, set(), agora):
        diz("   ✗ a reserva refaria por cima de tentativa ainda na fila")
        ok = False
    fila = [{"databaseId": 38012115315, "status": "in_progress"},      # triagem
            {"databaseId": 38012085139 + 10**6, "status": "queued"},     # diários
            {"databaseId": 38012085139 + 2 * 10**6, "status": "queued"}]  # o terceiro
    rodaram = []
    while fila:
        livres = [x for x in fila if not quem_vem_antes(x["databaseId"], fila)]
        if not livres:
            diz("   ✗ a vez na noite entrou em impasse")
            return False
        rodaram.append(livres[0]["databaseId"])
        fila = [x for x in fila if x is not livres[0]]
    if len(rodaram) != 3 or rodaram != sorted(rodaram):
        diz("   ✗ três elos simultâneos não rodam os três, por ordem de chegada")
        ok = False
    if ok:
        diz("   ✓ pendente cancelado pela fila é refeito; a vez na noite roda os três sem cancelar")
    return ok


def ensaio_env_usada_e_exportada(diz) -> bool:
    """15. Toda `env.X` lida pelo coletor foi exportada antes.

    10/10/2026 (F31 do catálogo): o passo do artefato lia `${{ env.NOITE }}` e nenhum passo
    escrevia `NOITE` em `$GITHUB_ENV` — o artefato `feito-<elo>-<noite>` nunca existiu, e o ensaio
    11 passou verde com o defeito porque testava a função, não o workflow. Reprova variável de
    `env.` usada em `.github/workflows/_coletor.yml` sem `X=` gravado em `$GITHUB_ENV` nem bloco
    `env:` que a declare.
    """
    import pathlib
    import re as _re

    fonte = (pathlib.Path(__file__).resolve().parents[1] / ".github/workflows/_coletor.yml"
             ).read_text(encoding="utf-8")
    usadas = set(_re.findall(r"\$\{\{\s*env\.([A-Z_][A-Z0-9_]*)", fonte))
    exportadas = set(_re.findall(r"echo\s+\"?([A-Z_][A-Z0-9_]*)=[^\n]*>>\s*\"?\$GITHUB_ENV", fonte))
    declaradas = set(_re.findall(r"^\s+([A-Z_][A-Z0-9_]*):\s", fonte, _re.M))
    faltam = sorted(usadas - exportadas - declaradas)
    if faltam:
        diz("   ✗ `env.` lida sem ter sido exportada no coletor: " + ", ".join(faltam))
        return False
    diz(f"   ✓ as {len(usadas)} variável(is) `env.` lidas pelo coletor são exportadas antes")
    return True


def ensaio_fora_da_main_nao_empurra(diz) -> bool:
    """16. Elo disparado fora da `main` não empurra para a `main`.

    10/10/2026 (F32 do catálogo): o `_coletor.yml` partia da `main` e empurrava `HEAD:main` em
    qualquer ramo, e a guarda da janela não barra fora da `main` — um disparo no ramo `ensaio`
    gravaria na `main` de dia. Reprova se o passo de commit não sair antes do `git push` quando o
    ramo não é a `main`.
    """
    import pathlib

    fonte = (pathlib.Path(__file__).resolve().parents[1] / ".github/workflows/_coletor.yml"
             ).read_text(encoding="utf-8")
    i_commit = fonte.find("- name: Commit com rebase-e-push")
    i_push = fonte.find("git push", i_commit)
    trecho = fonte[i_commit:i_push] if i_commit >= 0 and i_push > i_commit else ""
    # 10/10/2026 (2-bis.2): o ramo é `RAMO` (o do disparo); a `main` e os ramos `ensaio-real/` empurram
    # para o PRÓPRIO ramo, qualquer outro não empurra. O empurrão tem de ir para `HEAD:${RAMO}`.
    guarda = '"${RAMO}" != "main"' in trecho and "ensaio-real/*" in trecho and "exit 0" in trecho
    alvo = 'HEAD:${RAMO}' in fonte[i_push:i_push + 200] or '"HEAD:${RAMO}"' in fonte[i_commit:]
    codigo = "\n".join(l for l in fonte[i_commit:].split("- name:", 2)[1].splitlines()
                       if not l.strip().startswith("#"))
    if not (guarda and alvo) or "HEAD:main" in codigo:
        diz("   ✗ o commit do coletor empurra para a `main` mesmo quando o elo roda em outro ramo")
        return False
    diz("   ✓ fora da `main`, o coletor não empurra nada para a `main`")
    return True


def ensaio_chamador_do_coletor_concede_o_que_ele_pede(diz) -> bool:
    """17. Todo workflow que chama o `_coletor.yml` concede as permissões que os jobs dele pedem.

    10/10/2026 (F35 do catálogo): o job `vez` do coletor (#627) declara `actions: read`; workflow
    reutilizável não pode pedir mais do que o chamador concede, e o GitHub recusa o run inteiro
    (`startup_failure`, zero jobs). `noturno_sinais`, `semanal_espin_e_links` e
    `semanal_sinais_e_links` concediam só `contents: read` — os sinais físicos pararam às 14:06 de
    10/10, e o ensaio real (run 38071990034) foi quem viu. Reprova chamador sem `actions: read`.
    """
    import pathlib
    import re as _re

    pasta = pathlib.Path(__file__).resolve().parents[1] / ".github/workflows"
    pede = "actions: read" in (pasta / "_coletor.yml").read_text(encoding="utf-8")
    faltam = []
    for p in sorted(pasta.glob("*.yml")):
        t = p.read_text(encoding="utf-8")
        if "uses: ./.github/workflows/_coletor.yml" not in t:
            continue
        bloco = _re.search(r"^permissions:\n((?:[ \t]+.*\n)+)", t, _re.M)
        if pede and not (bloco and _re.search(r"^\s+actions:\s*(read|write)", bloco.group(1), _re.M)):
            faltam.append(p.name)
    if faltam:
        diz("   ✗ chamador do coletor sem `actions: read` (o run nem começa): " + ", ".join(faltam))
        return False
    diz("   ✓ todo chamador do coletor concede o que os jobs dele pedem")
    return True


def ensaio_triagem_uma_vez_na_abertura(diz) -> bool:
    """19. Na abertura, a triagem nasce só da corrente — o despachante não dispara outra.

    11/10/2026 (F27 do catálogo): às 01:10 o despachante disparou a triagem (run 38100940441, "nenhuma
    triagem na janela") e às 01:13 o fim dos sinais disparou outra (38101135888). Reprova se o
    workflow da triagem tem gatilho de corrente e o registro deixa o despachante dispará-la antes do
    horário primário.
    """
    import datetime as _dt
    import json as _json
    import pathlib

    raiz = pathlib.Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(raiz / "scripts"))
    import despachar_temporizadores as dp
    wf = (raiz / ".github/workflows/noturno_triagem.yml").read_text(encoding="utf-8")
    reg = _json.loads((raiz / "config/temporizadores.json").read_text(encoding="utf-8"))
    tri = [t for t in reg["temporizadores"] if t.get("workflow") == "noturno_triagem.yml"]
    if "workflow_run:" in wf and any(dp.esta_devido(t, [], _dt.datetime(2026, 10, 11, 1, 10)) for t in tri):
        diz("   ✗ a triagem é elo da corrente e o despachante ainda a dispara na abertura")
        return False
    diz("   ✓ na abertura, só a corrente chama a triagem; o despachante espera o horário dela")
    return True


def ensaio_checagem_pre_noite_nao_e_cega(diz) -> bool:
    """20. A checagem pré-noite não afirma fila vazia quando o `gh` falha, nem julga a noite errada.

    F43: nem conta ramo `ensaio-real/*`/`coleta-dia/*` como fila, nem dá despachante morto quando o
    despacho rodou dentro do `relogio.yml`.

    11/10/2026 (F36, F37): runs 38101488701 e 38104258410 (cron atrasado para 01:20 e 02:10) julgaram
    a noite de 12/10 e disseram "nenhum run aberto" com seis elos rodando — `gh run list` não tem o
    campo `path`, e o erro virava lista vazia.
    """
    import datetime as _dt
    import pathlib

    raiz = pathlib.Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(raiz / "scripts"))
    import checagem_pre_noite as cp

    class _R:
        returncode, stdout, stderr = 1, "", 'Unknown JSON field: "path"'
    erros = []
    cp._gh_json(["run", "list"], erros, executar=lambda *a, **k: _R())
    fatos = {"portoes_main": {"conclusion": "success"}, "merges": [], "runs_abertos": [],
             "ultimo_run": {}, "segredos": {}, "ensaio_real": None, "erros_de_consulta": erros}
    cega = [x for x in cp.avaliar(fatos, _dt.datetime(2026, 10, 10, 23, 0))
            if x["pergunta"].startswith("as consultas")]
    ok = bool(cega) and not cega[0]["ok"]
    ok = ok and cp.atrasada(_dt.datetime(2026, 10, 11, 1, 20)) \
        and cp.noite_seguinte(_dt.datetime(2026, 10, 11, 1, 20)) == "2026-10-11"
    # F43 (11/10/2026): ramo de ensaio não é fila; despacho dentro do relógio é despachante vivo.
    ok = ok and cp.abertos_da_api([{"workflow_runs": [
        {"id": 1, "path": ".github/workflows/noturno_juiz.yml", "status": "queued",
         "head_branch": "ensaio-real/2026-10-11-9"}]}]) == []
    viva = [x for x in cp.avaliar(dict(fatos, erros_de_consulta=[], ultimo_run={
        "despachante.yml": "2026-10-11T19:06:00Z", "relogio.yml": "2026-10-11T20:08:00Z"}),
        _dt.datetime(2026, 10, 11, 20, 20)) if x["pergunta"].startswith("despachante")]
    ok = ok and bool(viva) and viva[0]["ok"]
    diz("   ✓ erro do `gh` deixa a checagem vermelha e nomeada; cron atrasado não julga a noite seguinte"
        if ok else "   ✗ a checagem pré-noite ainda é cega ao erro do `gh` ou julga a noite errada")
    return ok


def ensaio_fila_longa_ainda_commita(diz) -> bool:
    """18. Fila que passa do teto ainda chega ao commit; comentário não é comando.

    11/10/2026 (F38 e F39 do catálogo): a rotina semanal de sinais estourou o teto de 150 min
    quatro vezes seguidas (runs 37205422226, 38100963895, 38109274967, 38118915381) e não
    commitou nada — o arquivo de transferências ficou com 10 dias e a `main` vermelha. E cada linha
    de comentário da fila virava `saude_pipeline.py --rodar '#'`. Reprova se o passo Coletar não
    passar o prazo ao invólucro, se o prazo não for contado do início do job, ou se o laço, rodado
    de verdade no bash, tratar comentário como comando.
    """
    import pathlib
    import re as _re
    import subprocess as _sp

    raiz = pathlib.Path(__file__).resolve().parents[1]
    fonte = (raiz / ".github/workflows/_coletor.yml").read_text(encoding="utf-8")
    ok = True
    if 'JOB_INICIO_EPOCH=$(date -u +%s)" >> "$GITHUB_ENV"' not in fonte:
        diz("   ✗ o início do job não é marcado — o prazo não teria de onde contar")
        ok = False
    if '--prazo "$PRAZO" --rodar' not in fonte:
        diz("   ✗ o passo Coletar não passa o prazo ao invólucro")
        ok = False
    m = _re.search(r"(          while IFS= read -r cmd; do\n.*?\n          done) <<'COMANDOS'", fonte, _re.S)
    if not m:
        diz("   ✗ laço de comandos do coletor não encontrado")
        return False
    laco = "\n".join(l[10:] for l in m.group(1).splitlines()).replace(
        "python3 scripts/saude_pipeline.py", "echo RODOU")
    script = ("PRAZO=0\n" + laco + " <<'COMANDOS'\n"
              "  # comentário da fila\n\n  coletar_a.py --x 1\n#outro\n  coletar_b.py\nCOMANDOS\n")
    saida = _sp.run(["bash", "-e", "-o", "pipefail", "-c", script], capture_output=True, text=True)
    rodou = [l for l in saida.stdout.splitlines() if l.startswith("RODOU")]
    if rodou != ['RODOU --prazo 0 --rodar coletar_a.py --x 1', 'RODOU --prazo 0 --rodar coletar_b.py']:
        diz(f"   ✗ o laço rodou {rodou!r} (esperado: só os dois comandos, sem comentário)")
        ok = False
    sys.path.insert(0, str(raiz / "scripts"))
    import saude_pipeline as _sp_mod
    if _sp_mod.decidir_prazo(100.0, 90.0)[0] != "pular":
        diz("   ✗ comando que começaria sem tempo não é pulado")
        ok = False
    if ok:
        diz("   ✓ a coleta tem prazo contado do início do job, e só comando de verdade roda")
    return ok


def ensaio_passo_condicionado_existe_no_job(diz) -> bool:
    """21. Todo `steps.<id>` lido num job aponta para um passo do PRÓPRIO job.

    11/10/2026 (F40 do catálogo): o passo `janela` do monólito semanal ficou no job vizinho, e todo
    passo de coleta do job `atualizar` saiu `skipped` com o run verde desde 08/10 — a saúde parou em
    26/09 sem nenhum vermelho. Reprova se o validador de workflows acusar referência a passo
    inexistente no job.
    """
    import pathlib
    import subprocess as _sp

    raiz = pathlib.Path(__file__).resolve().parents[1]
    r = _sp.run([sys.executable, "scripts/validar_workflows.py"], cwd=raiz, capture_output=True,
                text=True)
    ruins = [l.strip() for l in r.stdout.splitlines() if "lê `steps." in l]
    if ruins:
        for l in ruins[:5]:
            diz("   " + l)
        return False
    diz("   ✓ nenhum job lê passo que não tem — condição de passo nunca resolve vazio calada")
    return True


def ensaio_deploy_falho_e_vermelho(diz) -> bool:
    """22. Deploy sem "Deploy is live" termina vermelho, não com aviso.

    11/10/2026 (F42 do catálogo): de 10:00 às 18:00 UTC o Netlify respondeu "Unauthorized: could not
    retrieve site" a cada publicação, e o passo de reposição do domínio só emitia aviso — publicador
    verde, domínio parado. Reprova se o validador de workflows acusar deploy que só avisa.
    """
    import pathlib
    import subprocess as _sp

    raiz = pathlib.Path(__file__).resolve().parents[1]
    r = _sp.run([sys.executable, "scripts/validar_workflows.py"], cwd=raiz, capture_output=True,
                text=True)
    ruins = [l.strip() for l in r.stdout.splitlines() if "(F42)" in l]
    if ruins:
        for l in ruins[:5]:
            diz("   " + l)
        return False
    diz('   ✓ todo deploy sem "Deploy is live" termina vermelho')
    return True


def ensaio_painel_cheio_nao_perde_o_commit(diz) -> bool:
    """23. Painel da noite com 400+ linhas: nenhum corte, e a cabeça podada não recusa a união.

    12/10/2026 (F44 do catálogo): `painel_da_noite.py` cortava o painel em 400 linhas. Na noite
    11→12 ele chegou a 400, cada escrita passou a podar a cabeça, os lados deixaram de começar com
    a base e o resolvedor recusou — saúde, diários e triagem perderam o commit. Este ensaio monta o
    conflito com os dois lados podados (o pior caso, que é o do código antigo) e exige união sem
    perda; e lê o produtor para exigir que o corte não volte.
    """
    import inspect
    import painel_da_noite as pn
    import unir_conflito_de_rodada as u
    fonte = inspect.getsource(pn.registrar) + inspect.getsource(pn.recuperar_da_api)
    if "[-4" in fonte:
        diz("  ✗ o produtor do painel voltou a cortar a lista — é o F44 de volta")
        return False
    with tempfile.TemporaryDirectory() as t:
        tmp = pathlib.Path(t)
        g = _repo(tmp)
        caminho = tmp / "data" / "painel_da_noite.json"
        caminho.parent.mkdir(parents=True, exist_ok=True)

        def l(i, elo="x"):
            return {"noite": "2026-10-%02d" % (1 + i // 40), "elo": elo, "inicio": "%02d:%02d" % (
                1 + (i // 60) % 8, i % 60), "conclusao": "success"}

        def doc(linhas):
            return json.dumps({"_governanca": "g", "noites": linhas}, ensure_ascii=False,
                              indent=1) + "\n"

        base = [l(i) for i in range(400)]
        caminho.write_text(doc(base), encoding="utf-8", newline="\n")
        g("add", "-A"); g("commit", "-qm", "painel cheio")
        g("checkout", "-qb", "saude")
        caminho.write_text(doc((base + [l(500, "saude")])[-400:]), encoding="utf-8", newline="\n")
        g("add", "-A"); g("commit", "-qm", "saude")
        g("checkout", "-q", "main")
        caminho.write_text(doc((base + [l(501, "sinais"), l(502, "sinais")])[-400:]),
                           encoding="utf-8", newline="\n")
        g("add", "-A"); g("commit", "-qm", "sinais")
        if g("merge", "saude", "-m", "colisao", pode_falhar=True) == 0:
            diz("  ✗ o ensaio não produziu conflito: ele não está medindo o que diz medir")
            return False
        _, _, recusados = u.resolver(repo=tmp)
        if recusados:
            diz(f"  ✗ o resolvedor RECUSOU o painel podado — é o F44 de volta: {recusados[0]}")
            return False
        d = json.loads(caminho.read_text(encoding="utf-8"))["noites"]
        if len(d) != 403 or d[:400] != base:
            diz(f"  ✗ perda na união do painel: {len(d)} linhas (esperadas 403, base inteira)")
            return False
        diz("  ✓ painel com 400 linhas e cabeça podada nos dois lados: 403 linhas, nenhuma perdida")
        return True


def ensaio_coleta_perdida_de_dono_unico_volta(diz) -> bool:
    """24. Arquivo de dono único da coleta perdida volta pela regra de três vias (F45).

    12/10/2026: a reaplicação ignorava todo arquivo sem porta própria e marcava o artefato como
    reaplicado — clima municipal, enquadramento federal e cobertura do QD da rotina semanal de
    sinais se perderam em silêncio. Reprova se o `_coletor.yml` não escrever o manifesto da perda
    antes de subir o artefato, ou se a regra de três vias copiar por cima de outro escritor.
    """
    import pathlib
    import yaml
    import reaplicar_noite as rn
    raiz = pathlib.Path(__file__).resolve().parents[1]
    wf = yaml.safe_load((raiz / ".github/workflows/_coletor.yml").read_text(encoding="utf-8"))
    passos = [x for j in (wf.get("jobs") or {}).values() for x in (j.get("steps") or [])]
    nomes = [str(x.get("name") or "") for x in passos]
    i_man = next((i for i, n in enumerate(nomes) if n.startswith("Escrever o manifesto da coleta")), -1)
    i_art = next((i for i, n in enumerate(nomes) if n.startswith("Guardar as saídas")), -1)
    commit = next((str(x.get("run") or "") for x in passos if x.get("id") == "commit"), "")
    # F54: o upload-artifact v4 descarta arquivo oculto; manifesto com "." no nome nunca subia.
    if (not (0 <= i_man < i_art) or "alterados_do_elo" not in commit
            or any(p.startswith(".") for p in rn.MANIFESTO_DA_PERDA.split("/"))):
        diz("  ✗ o artefato da coleta perdida sobe sem o manifesto (base + alterados) — F45 de volta")
        return False
    alt = ["data/clima.json"]
    with tempfile.TemporaryDirectory() as t:
        d = pathlib.Path(t) / "c"
        ok = (rn.reaplicar_arquivo("data/clima.json", alt, "v1", "v1", "v2", d) == "copiado"
              and rn.reaplicar_arquivo("data/clima.json", alt, "v1", "v3", "v2", d).startswith("recusa")
              and rn.reaplicar_arquivo("data/outro.json", alt, "v1", "v1", "v2", d) == "fora")
    diz("  ✓ manifesto da perda antes do artefato; dono único volta, e nunca por cima de outro escritor"
        if ok else "  ✗ a regra de três vias da reaplicação copia por cima de outro escritor")
    return ok


def ensaio_segunda_falha_do_calor_mantem_a_lacuna(diz) -> bool:
    """25. Duas noites seguidas sem o painel de calor do MS mantêm a lacuna declarada (F46).

    13/10/2026: na 2ª noite de falha depois de `vencer_calor`, o coletor da saúde rebaixou
    `painel_calor_ms` de `lacuna` para `aguardando_primeira_coleta` e o portão de frescor deixou
    a `main` vermelha. Reprova se uma fonte que já coletou voltar a "aguardando primeira coleta".
    """
    import pathlib
    import sys as _sys
    from datetime import date
    raiz = pathlib.Path(__file__).resolve().parents[1]
    if str(raiz) not in _sys.path:
        _sys.path.insert(0, str(raiz))
    from coletar_saude import falha_calor
    ss = {"calor_excesso": {"coletado_em": "25/09/2026"}}
    f = {"status": "coletado"}
    for dia in (11, 12, 13):
        falha_calor(ss, f, "sem resposta", date(2026, 10, dia))
    ok = (f["status"] == "lacuna" and f.get("ultima_coleta_ok") == "25/09/2026"
          and (ss.get("calor_excesso_anterior") or {}).get("coletado_em") == "25/09/2026")
    diz("  ✓ terceira noite sem o painel segue lacuna com a última coleta boa" if ok
        else "  ✗ fonte que já coletou voltou a \"aguardando primeira coleta\" — F46 de volta")
    return ok


def ensaio_ensaio_real_fixa_a_noite(diz) -> bool:
    """26. O ensaio real fixa a noite no começo e não começa perto da noite de verdade (F47).

    12→13/10/2026: o cron das 18:13 chegou às 00:39; o ramo nasceu com a noite 2026-10-12, o juiz
    (01:01) gravou o marcador em 2026-10-13 e o condutor esperou na noite errada até o teto.
    Reprova se o workflow não gravar `.noite_do_ensaio` no ramo, se não tiver a guarda de hora,
    ou se a noite fixada deixar de valer para os elos do ramo depois da virada.
    """
    import datetime as dt
    import pathlib
    import tempfile
    import janela_da_noite as jn
    raiz = pathlib.Path(__file__).resolve().parents[1]
    wf = (raiz / ".github/workflows/ensaio_real_da_noite.yml").read_text(encoding="utf-8")
    estrutura = (jn.NOITE_DO_ENSAIO in wf and "--ensaio-pode-comecar" in wf)
    with tempfile.TemporaryDirectory() as t:
        tp = pathlib.Path(t)
        (tp / jn.NOITE_DO_ENSAIO).write_text("2026-10-12\n", encoding="utf-8", newline="\n")
        depois = dt.datetime(2026, 10, 13, 1, 1)
        fixa = (jn.noite_corrente(depois, "ensaio-real/2026-10-13-38328343011", tp) == "2026-10-12"
                and jn.noite_corrente(depois, "main", tp) == "2026-10-13")
    hora = (not jn.ensaio_pode_comecar(dt.datetime(2026, 10, 13, 0, 39))
            and jn.ensaio_pode_comecar(dt.datetime(2026, 10, 12, 18, 13)))
    ok = estrutura and fixa and hora
    diz("  ✓ noite do ensaio fixada no ramo; cron atrasado para a noite vira \"pulado, fora de hora\""
        if ok else "  ✗ o ensaio real pode atravessar a virada e esperar na noite errada — F47 de volta")
    return ok


def ensaio_busca_web_pelo_coletor(diz) -> bool:
    """27. A busca web coleta pelo `_coletor.yml`, com o prazo e o commit de todos (F48).

    08→13/10/2026: monólito com caminho próprio, sem o prazo do F38 — toda execução da noite
    morreu no teto sem commitar. Reprova se a busca web voltar a ter caminho de coleta próprio.
    """
    import pathlib
    import yaml
    raiz = pathlib.Path(__file__).resolve().parents[1]
    wf = yaml.safe_load((raiz / ".github/workflows/busca_web_cadencia.yml").read_text(encoding="utf-8"))
    jobs = list((wf.get("jobs") or {}).values())
    ok = bool(jobs) and all(str(j.get("uses") or "").endswith("/_coletor.yml") for j in jobs)
    diz("  ✓ busca web pelo `_coletor.yml` (prazo, janela, marcador, artefato, commit)" if ok
        else "  ✗ a busca web tem caminho de coleta próprio — F48 de volta")
    return ok


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
    ("7. carimbo distinto não recusa a noite", ensaio_carimbo_nao_recusa_a_noite),
    ("8. a guarda decide pelo `rc`, nos dois shells", ensaio_guarda_com_o_shell_do_actions),
    ("9. portão vermelho não repõe o domínio", ensaio_portao_vermelho_nao_repoe_o_dominio),
    ("10. fila de runner não é falha: o vigia não atropela a corrente",
     ensaio_fila_de_runner_nao_e_falha),
    ("11. o marcador do elo sobrevive ao push perdido", ensaio_marcador_sobrevive_ao_push),
    ("12. a coleta perdida volta para dentro, pela porta de cada arquivo",
     ensaio_coleta_perdida_volta_para_dentro),
    ("13. o despachante tem observador fora do cron do GitHub",
     ensaio_despachante_nao_depende_do_cron),
    ("14. pendente cancelado pela fila é refeito", ensaio_pendente_cancelado_pela_fila_e_refeito),
    ("15. toda `env.` lida pelo coletor é exportada antes", ensaio_env_usada_e_exportada),
    ("16. elo fora da `main` não empurra para a `main`", ensaio_fora_da_main_nao_empurra),
    ("17. chamador do coletor concede o que ele pede", ensaio_chamador_do_coletor_concede_o_que_ele_pede),
    ("18. fila longa ainda commita; comentário não é comando", ensaio_fila_longa_ainda_commita),
    ("19. na abertura, a triagem nasce só da corrente", ensaio_triagem_uma_vez_na_abertura),
    ("20. a checagem pré-noite não é cega nem julga a noite errada", ensaio_checagem_pre_noite_nao_e_cega),
    ("21. todo passo condicionado existe no próprio job", ensaio_passo_condicionado_existe_no_job),
    ("22. deploy falho é vermelho, não aviso", ensaio_deploy_falho_e_vermelho),
    ("23. painel cheio não perde o commit", ensaio_painel_cheio_nao_perde_o_commit),
    ("24. coleta perdida de dono único volta (três vias)",
     ensaio_coleta_perdida_de_dono_unico_volta),
    ("25. segunda falha do calor mantém a lacuna", ensaio_segunda_falha_do_calor_mantem_a_lacuna),
    ("26. o ensaio real fixa a noite e respeita a hora", ensaio_ensaio_real_fixa_a_noite),
    ("27. a busca web coleta pelo `_coletor.yml`", ensaio_busca_web_pelo_coletor),
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
