#!/usr/bin/env python3
"""Resolve o conflito de rebase da rodada de atualização — só onde a resolução é conhecida.

POR QUE ESTE ARQUIVO EXISTE (27/09/2026, §246)
==============================================
O passo de commit da rodada tenta `git rebase` seis vezes e desiste. Medido nas rodadas de
24 e 25/09: seis tentativas, seis conflitos idênticos, nestes arquivos —

    data/log_buscas.json  data/fontes_consultadas.json  data/pistas_imprensa.json
    data/pistas_revisao.json  docs/FILA_PISTAS.md  docs/MANIFEST_SHA256.txt

A causa estrutural: `data/log_buscas.json` tem 20,7 MB em UMA ÚNICA LINHA. Qualquer mudança
dos dois lados é conflito textual garantido, porque não existe linha para o git casar. E
`busca_web_cadencia.yml` commita esse arquivo a cada 2 horas, enquanto a rodada leva mais que
isso. O laço aborta e repete com o mesmo conteúdo: repetir só resolve *push recusado*, nunca
conflito.

O QUE ESTE SCRIPT RESOLVE, E O QUE ELE RECUSA
=============================================
Ele resolve DUAS classes, e recusa todo o resto. Recusar é o comportamento correto: arbitrar
uma mesclagem que ninguém decidiu é como se apagam evidências sem aviso. Em 23/09/2026 uma
união por CONTEÚDO produziu um log menor que cada um dos lados — quase 3.000 execuções
sumiram caladas. A regra do projeto nasceu daí: une-se pela BASE COMUM, nunca por conteúdo.

1. LOG QUE SÓ CRESCE (`data/log_buscas.json`, `data/historico_mudancas.json`)
   Formato: escalares no topo mais UMA lista que só recebe itens no fim.
   Resolução: `base + nossos_novos + deles_novos`, onde "novos" é o que vem depois dos
   `n` itens da base. Antes de unir, confere que os dois lados realmente COMEÇAM com a base
   item a item; se não começarem, o arquivo não se comportou como append-only nesta ocasião
   e o script RECUSA em vez de adivinhar. Depois de unir, confere que o total é maior ou
   igual a cada lado — a trava que faltava em 23/09.

2. ARQUIVO REGENERÁVEL (`docs/MANIFEST_SHA256.txt`, `docs/FILA_PISTAS.md`,
   `data/pistas_revisao.json`)
   São função de outros dados, não fonte. Casar linha a linha não faz sentido: resolve-se
   com a versão de cima (a `main`) e a cadeia canônica regenera depois. O script os NOMEIA na
   saída, em `REGENERAR=`, para que quem chamou saiba que precisa regenerar.

Tudo o mais é recusado com o nome do arquivo e o motivo. (As filas de pista e o livro de fontes,
recusados aqui até 05/10 e 15/10, unem-se hoje pela política dos seus produtores — ver abaixo.)

ESTÁGIOS DO GIT, E A ARMADILHA QUE NÃO SE APLICA AQUI
=====================================================
Num conflito, `git show :1:arquivo` é a BASE comum, `:2:` é "nosso" e `:3:` é "deles".
Durante um REBASE os dois últimos vêm invertidos em relação à intuição: "nosso" é o upstream
em que se está reaplicando, e "deles" é o commit da rodada sendo reaplicado. Para a classe 1
isso não importa — a união é simétrica. Para a classe 2 importa, e o script toma o `:2:`
justamente porque o derivado será regenerado de todo modo.

Uso:
    python3 scripts/unir_conflito_de_rodada.py            # resolve o que sabe, recusa o resto
    python3 scripts/unir_conflito_de_rodada.py --autoteste # prova, sem rede e sem tocar no repo

Saída: 0 se TODOS os caminhos em conflito foram resolvidos; 2 se algum foi recusado.
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent

# Chave da lista que só cresce, por arquivo. Só entra aqui o que a regra do projeto declara
# append-only — nada de inferir pelo formato, porque "tem uma lista" não é "só cresce".
LOGS_QUE_SO_CRESCEM = {
    "data/log_buscas.json": "execucoes",
    "data/historico_mudancas.json": "eventos",
    # 05/10/2026: o painel de saúde acrescenta uma linha por execução e nunca reescreve as
    # anteriores — é a mesma forma, e o portão `verificar_escritores.py` cobrou a classe.
    "data/saude_pipeline.json": "execucoes",
    # 05/10/2026: o painel da noite acrescenta um registro por elo por noite e nunca reescreve os
    # anteriores. Ele foi RECUSADO na triagem das 18:58 e levou a rodada junto -- o elo coletou e
    # perdeu o commit, que e exatamente a perda que a regra 3 da corrente existe para evitar.
    "data/painel_da_noite.json": "noites",
}



def gravar_no_formato_do_produtor(caminho, doc) -> None:
    """Escreve a união pela mesma porta que os produtores (`coletores_base.gravar_em`).

    13/10/2026: a união gravava estes logs compactos e os produtores, indentados; cada commit da
    noite reescrevia o arquivo inteiro de um formato para o outro (`saude_pipeline.json`,
    `painel_da_noite.json`: 0 ↔ 5–7 mil linhas), inflando o histórico e os conflitos."""
    sys.path.insert(0, str(RAIZ))
    from coletores_base import gravar_em
    gravar_em(caminho, doc)

# JSONL que so cresce: uma linha por registro, uniao pela base comum nas LINHAS.
# `data/log_buscas/<ano-mes>.jsonl` e o volume que saiu de `data/log_buscas.json` -- a mesma regra
# append-only, em outro formato, e ate hoje sem classe: ele recusava e parava a rodada.
PREFIXOS_JSONL_QUE_SO_CRESCEM = ("data/log_buscas/",)

# CONTADORES que só sobem. `data/funil/<data>.json` guarda, por etapa, quantas pistas passaram por
# cada peneira naquele dia, e `funil.registrar` SOMA a cada rodada — ninguém reescreve o número de
# ninguém. Dois elos que contaram no mesmo dia são dois acréscimos, e a união é a mesma de sempre,
# aplicada a número em vez de item de lista: `base + (nosso − base) + (deles − base)`.
# Lado que ficou MENOR que a base é decremento, não acréscimo, e aí se recusa.
PREFIXOS_CONTADORES_QUE_SO_CRESCEM = ("data/funil/",)

# Função de outros dados. Resolve-se com a versão de cima e regenera-se depois.
REGENERAVEIS = (
    "docs/MANIFEST_SHA256.txt",
    "docs/FILA_PISTAS.md",
    "data/pistas_revisao.json",
    # 05/10/2026: os dois sao funcao de outro dado e sao regerados pela cadeia canonica --
    # `scripts/gerar_resumo_do_log.py` e `gerar_card_municipios.py`, os dois dentro de
    # `scripts/verificar_derivados.sh`. Recusa-los era conservadorismo sem razao, pela mesma logica
    # do comentario de `dados-abertos/` logo abaixo, e os dois pararam a triagem de 05/10.
    "data/log_buscas_resumo.json",
    "data/municipios_card.json",
    # 15/10/2026: os dois são regerados pela cadeia (`recalcular_mare.py --write`,
    # `gerar_cobertura_declarada.py`) e foram recusados no push dos diários da noite 14→15.
    "data/verificacao_municipal.json",
    "data/cobertura_declarada_uf.json",
)

# 11/10/2026: derivados que NÃO estão na cadeia canônica (§273) e têm gerador próprio. Resolvem-se
# regerando a partir do arquivo-fonte já unido, aqui mesmo — "versão de cima e a cadeia regenera"
# não serve, porque a cadeia não os regera e `gerar_saude_pipeline.py --check` cobraria a diferença.
# Foi o conflito mais frequente dos PRs de 11/10: cada publicação reescreve o painel.
DERIVADOS_COM_GERADOR = {
    "docs/SAUDE_PIPELINE.md": ("data/saude_pipeline.json", ("scripts/gerar_saude_pipeline.py",)),
}

# §252 (27/09/2026): prefixos que o PRÓPRIO projeto já declara derivados, em
# `.claude/hooks/bloquear_derivados.py`: `dados-abertos/.+`, `feeds/.+\.xml`, `selos/.+\.svg`.
# Medido na rodada de 27/09 às 08h29: o resolvedor recusou
# `dados-abertos/verificacao_municipal.csv` por "política de mesclagem não decidida" — mas a
# política DELE está decidida desde sempre: é derivado, logo resolve com a versão de cima e a
# cadeia canônica regenera. Recusar derivado era conservadorismo sem razão, e custou a rodada.
# Fica como PREFIXO, não nome exato, porque o conjunto cresce com o dado (um CSV novo em
# dados-abertos/ nasce derivado, e não deve precisar de PR para ser resolvido).
PREFIXOS_REGENERAVEIS = ("dados-abertos/", "feeds/", "selos/")

# 05/10/2026 (item 2 do handover da noite confiável) — AS FILAS DE PISTA PASSAM A SER RESOLVÍVEIS.
#
# Até hoje `data/pistas_imprensa.json` era RECUSADO de propósito, e o cabeçalho deste arquivo dizia
# por quê: "os dois lados alteram os MESMOS registros (status de triagem) ... escolher qual vence é
# política de mesclagem — decisão da editoria, não deste script". Estava certo: a política não
# existia.
#
# Ela existe desde o PR #555. `scripts/pistas.py` é a única porta da fila e declara, com 46 casos de
# autoteste, o que acontece com cada caso: pista nova é validada e acrescentada; pista que já está
# lá tem os campos MESCLADOS; pista que só um lado conhece FICA. Esta classe aplica a mesma política
# ao conflito de rebase — e é por isso que ela pode existir agora e não podia antes.
#
# O que ela continua recusando, e é o núcleo da política: quando os dois lados mudaram o MESMO campo
# da MESMA pista para valores diferentes. Aí a pergunta "qual vence" é real, e adivinhar seria
# exatamente o que custou 3.000 execuções em 23/09. Na prática é raro, porque cada elo escreve
# campos distintos — a triagem escreve `triagem`, o seguimento escreve `seguimento`, o juiz escreve
# `status`.
#
# O ganho medido: a busca web perdeu 114 minutos de trabalho na noite de 04→05/10 porque o rebase
# conflitou quatro vezes nestes arquivos e o laço desistiu.
FILAS_DE_PISTA = (
    "data/pistas_imprensa.json",
    "data/pistas_descobertas.json",
    "data/pistas_doe.json",
    "data/pistas_sinais.json",
    "data/pistas_rejeitadas.json",
)


def _chave_de_pista(pista: dict) -> str:
    """A identidade da pista. A MESMA de `scripts/pistas.chave_da_pista` — duas definições de
    identidade produziriam duas filas diferentes que se acham iguais."""
    p = pista or {}
    ident = str(p.get("id") or "").strip()
    if ident:
        return "id:" + ident
    url = str(p.get("url_final") or p.get("url") or "").strip()
    return "url:" + url + "|" + str(p.get("alvo") or p.get("ibge") or p.get("uf") or "")


def _mesclar_pista(base: dict, nossa: dict, delas: dict) -> dict:
    """A pista com os campos dos dois lados. Levanta `Recusa` no conflito real. Função pura.

    A regra: parte-se da base e aplica-se o que cada lado MUDOU em relação a ela. Campo que só um
    lado tocou entra. Campo que os dois tocaram para o MESMO valor entra. Campo que os dois tocaram
    para valores DIFERENTES é a pergunta que ninguém decidiu — recusa.
    """
    b = dict(base or {})
    fora = dict(b)
    for campo in sorted(set(dict(nossa or {})) | set(dict(delas or {}))):
        na_base = b.get(campo, _AUSENTE)
        nosso_v = (nossa or {}).get(campo, _AUSENTE)
        deles_v = (delas or {}).get(campo, _AUSENTE)
        nos_mudou = nosso_v != na_base
        eles_mudou = deles_v != na_base
        if nos_mudou and eles_mudou and nosso_v != deles_v:
            raise Recusa(f"os dois lados mudaram o campo {campo!r} da mesma pista para valores "
                         f"diferentes — qual vence é política, e este script não adivinha")
        escolhido = nosso_v if nos_mudou else (deles_v if eles_mudou else na_base)
        if escolhido is _AUSENTE:
            fora.pop(campo, None)
        else:
            fora[campo] = escolhido
    return fora


def unir_fila_de_pistas(caminho, base_txt, nosso_txt, deles_txt):
    """Une a fila pela base comum, com a política da porta única. Devolve (doc, n_nosso, n_deles,
    n_uniao, n_mescladas).

    Nada se perde: pista que só um lado tem FICA, e a união nunca é menor que o maior dos lados —
    a mesma trava de 23/09, pelo mesmo motivo.
    """
    if nosso_txt is None or deles_txt is None:
        raise Recusa("um dos lados não tem o arquivo; isto não é acréscimo dos dois lados")
    nosso, deles = json.loads(nosso_txt), json.loads(deles_txt)
    base = json.loads(base_txt) if base_txt is not None else {}

    chave = None
    for candidata in ("pistas", "itens", "rejeitadas"):
        if isinstance(nosso.get(candidata), list) and isinstance(deles.get(candidata), list):
            chave = candidata
            break
    if chave is None:
        raise Recusa("os dois lados não trazem a mesma lista de pistas no formato esperado")

    lb = base.get(chave) if isinstance(base.get(chave), list) else []
    ln, ld = nosso[chave], deles[chave]
    por_chave_base = {_chave_de_pista(p): p for p in lb}
    por_chave_nosso = {_chave_de_pista(p): p for p in ln}
    por_chave_deles = {_chave_de_pista(p): p for p in ld}

    # A ORDEM é a da base, depois os acréscimos nossos, depois os deles. Ordem estável mantém o
    # diff legível e faz a união ser a mesma qualquer que seja o lado em que o rebase corre.
    ordem = [_chave_de_pista(p) for p in lb]
    ordem += [k for k in (_chave_de_pista(p) for p in ln) if k not in por_chave_base]
    vistas = set(ordem)
    ordem += [k for k in (_chave_de_pista(p) for p in ld)
              if k not in por_chave_base and k not in vistas]

    uniao, mescladas = [], 0
    for k in ordem:
        na_base = por_chave_base.get(k)
        nossa = por_chave_nosso.get(k)
        delas = por_chave_deles.get(k)
        if na_base is not None and nossa is not None and delas is not None:
            uniao.append(_mesclar_pista(na_base, nossa, delas))
            if nossa != delas:
                mescladas += 1
        else:
            uniao.append(nossa if nossa is not None else (delas if delas is not None else na_base))

    if len(uniao) < max(len(ln), len(ld)):
        raise Recusa(f"a união deu {len(uniao)}, menor que um dos lados ({len(ln)} e {len(ld)}) — "
                     f"recusado")

    fundido = dict(deles)
    for k, v in nosso.items():
        if k != chave and k not in fundido:
            fundido[k] = v
    fundido[chave] = uniao
    return fundido, len(ln), len(ld), len(uniao), mescladas


# 14/10/2026 (F55): dois índices que todo elo escreve e que o resolvedor recusava — o push dos
# diários da noite 13→14 caiu nos dois. O índice de evidências é endereçado pelo conteúdo: entrada
# nova de um lado entra; a mesma entrada mudada nos dois lados segue a regra da pista (campo a campo).
# O registro de robots é contador + trilha por host: os acessos se unem pela base comum (multiconjunto,
# teto de 200 do produtor), o total soma o que cada lado acrescentou.
# 15/10/2026: o livro de fontes (`data/fontes_consultadas.json`) por município, com a regra do
# próprio produtor (`coletores_base.marcar_fonte_consultada`): consultas dos dois lados pela janela
# de fontes, nível nunca rebaixa, a última verificação é a mais recente; fato binário mudado nos dois
# lados para valores diferentes segue a regra da pista (recusa). Diários e busca web escrevem fontes
# diferentes do mesmo município desde 14/10 — o push dos diários da noite 14→15 caiu nele.
INDICES_POR_CHAVE = {"data/evidencias.json": "itens", "data/robots_registro.json": "hosts",
                     "data/fontes_consultadas.json": "municipios"}


def _unir_municipio_do_livro(base: dict, nosso: dict, deles: dict) -> dict:
    if str(RAIZ) not in sys.path:
        sys.path.insert(0, str(RAIZ))
    from coletores_base import NIVEIS, janela_de_fontes
    proprios = ("fontes", "nivel_verificacao", "ultima_verificacao")
    resto = [{k: v for k, v in (x or {}).items() if k not in proprios} for x in (base, nosso, deles)]
    datas = [x["ultima_verificacao"] for x in (nosso, deles) if x.get("ultima_verificacao")]
    return {**_mesclar_pista(*resto),
            "nivel_verificacao": max((x.get("nivel_verificacao") or NIVEIS[0] for x in (nosso, deles)),
                                     key=NIVEIS.index),
            "ultima_verificacao": max(datas) if datas else None,
            "fontes": janela_de_fontes([f for x in (base, nosso, deles) for f in (x or {}).get("fontes") or []])}


def _unir_host(base: dict, nosso: dict, deles: dict) -> dict:
    b = base or {}
    acessos = _multiconjunto(b.get("acessos") or [], nosso.get("acessos") or [], deles.get("acessos") or [])
    t0 = int(b.get("total_acessos") or 0)
    return {**deles, **nosso, "acessos": acessos[-200:],
            "total_acessos": int(nosso.get("total_acessos") or 0) + int(deles.get("total_acessos") or 0) - t0,
            "ultimo_acesso": max(str(nosso.get("ultimo_acesso") or ""), str(deles.get("ultimo_acesso") or "")) or None,
            "primeiro_acesso": min(x for x in (nosso.get("primeiro_acesso"), deles.get("primeiro_acesso")) if x)
            if (nosso.get("primeiro_acesso") or deles.get("primeiro_acesso")) else None}


def unir_indice(caminho, base_txt, nosso_txt, deles_txt):
    """(doc, n_nosso, n_deles, n_uniao) do índice `{chave: {id: entrada}}`, pela base comum."""
    chave = INDICES_POR_CHAVE[caminho]
    if nosso_txt is None or deles_txt is None:
        raise Recusa("um dos lados não tem o arquivo; isto não é acréscimo dos dois lados")
    nosso, deles = json.loads(nosso_txt), json.loads(deles_txt)
    base = (json.loads(base_txt) if base_txt is not None else {}).get(chave) or {}
    a, b = nosso.get(chave) or {}, deles.get(chave) or {}
    mesclar = {"hosts": _unir_host, "municipios": _unir_municipio_do_livro}.get(chave, _mesclar_pista)
    uniao = dict(a)
    for k, v in b.items():
        if k not in a or a[k] == v:
            uniao[k] = v
        elif v != base.get(k):
            uniao[k] = v if a[k] == base.get(k) else mesclar(base.get(k), a[k], v)
    return {**deles, **nosso, chave: uniao}, len(a), len(b), len(uniao)


class _Ausente:
    """O campo não existe neste lado — distinto de existir com valor nulo."""
    def __repr__(self):
        return "<ausente>"


_AUSENTE = _Ausente()


def e_regeneravel(caminho: str) -> bool:
    """O caminho é função de outros dados, e portanto resolve com a versão de cima?"""
    return caminho in REGENERAVEIS or caminho.startswith(PREFIXOS_REGENERAVEIS)


# Campos que são CARIMBO de tempo, não dado: unem-se pelo maior. Nenhum deles é conteúdo que se
# possa perder — são a hora em que o arquivo foi escrito.
CARIMBOS = ("atualizado_em", "gerado_em", "atualizado", "gravado_em", "corte", "data_do_corte")


class Recusa(Exception):
    """O script não sabe resolver este caminho, e adivinhar apagaria dado."""


def git(*args, repo=None, binario=False):
    """Roda o git no repositório e devolve a saída; levanta se o git reprovar."""
    r = subprocess.run(["git", *args], cwd=str(repo or RAIZ), capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.decode('utf-8', 'replace').strip()}")
    return r.stdout if binario else r.stdout.decode("utf-8")


def em_conflito(repo=None):
    """Os caminhos que o git deixou sem resolver."""
    saida = git("diff", "--name-only", "--diff-filter=U", repo=repo)
    return [l.strip() for l in saida.splitlines() if l.strip()]


def estagio(caminho, n, repo=None):
    """O conteúdo do estágio n (1=base, 2=nosso, 3=deles), ou None se o estágio não existe."""
    try:
        return git("show", f":{n}:{caminho}", repo=repo, binario=True).decode("utf-8")
    except RuntimeError:
        return None


def e_contador_que_so_cresce(caminho: str) -> bool:
    """O caminho é um arquivo de contadores somados por rodada? Função pura."""
    return (str(caminho).startswith(PREFIXOS_CONTADORES_QUE_SO_CRESCEM)
            and str(caminho).endswith(".json"))


def unir_contadores(caminho, base_txt, nosso_txt, deles_txt):
    """União pela base comum em NÚMEROS: base + (nosso − base) + (deles − base). Função pura.

    `etapas` é um dicionário de etapa → {contagem: inteiro}, e cada rodada soma. Somar os dois
    acréscimos preserva o trabalho dos dois lados; escolher um lado jogaria fora o do outro, que é
    a perda que este arquivo inteiro existe para impedir.

    Campo fora de `etapas` que divirja é recusado: `data` e `formato_versao` não são contagem, e
    diferença neles quer dizer que os dois lados falam de coisas diferentes.
    """
    if nosso_txt is None or deles_txt is None:
        raise Recusa("um dos lados não tem o arquivo; isto não é acréscimo dos dois lados")
    nosso, deles = json.loads(nosso_txt), json.loads(deles_txt)
    base = json.loads(base_txt) if base_txt is not None else {}
    for nome, d in (("nosso", nosso), ("deles", deles)):
        if not isinstance(d, dict) or not isinstance(d.get("etapas"), dict):
            raise Recusa(f"o lado {nome} não tem 'etapas' no formato esperado")

    fora_de_etapas = set()
    for chave in set(nosso) | set(deles):
        if chave == "etapas" or chave == "atualizado_em":
            continue
        if nosso.get(chave) != deles.get(chave):
            fora_de_etapas.add(chave)
    if fora_de_etapas:
        raise Recusa("os campos fora de 'etapas' divergem: " + ", ".join(sorted(fora_de_etapas)))

    eb = (base.get("etapas") or {}) if isinstance(base, dict) else {}
    etapas, somados = {}, 0
    for etapa in sorted(set(nosso["etapas"]) | set(deles["etapas"])):
        b = eb.get(etapa) or {}
        n = nosso["etapas"].get(etapa) or {}
        d = deles["etapas"].get(etapa) or {}
        junto = {}
        for chave in sorted(set(b) | set(n) | set(d)):
            vb, vn, vd = b.get(chave, 0), n.get(chave, 0), d.get(chave, 0)
            for nome, v in (("nosso", vn), ("deles", vd), ("base", vb)):
                if not isinstance(v, int) or isinstance(v, bool):
                    raise Recusa(f"{etapa}.{chave}: o lado {nome} não é inteiro")
            for nome, v in (("nosso", vn), ("deles", vd)):
                if v < vb:
                    raise Recusa(f"{etapa}.{chave}: o lado {nome} ({v}) é menor que a base "
                                 f"({vb}) — houve decremento, e isto não é acréscimo")
            junto[chave] = vb + (vn - vb) + (vd - vb)
            somados += 1
        etapas[etapa] = junto

    fundido = dict(nosso)
    fundido["etapas"] = etapas
    carimbos = [x for x in (nosso.get("atualizado_em"), deles.get("atualizado_em")) if x]
    if carimbos:
        fundido["atualizado_em"] = max(carimbos)
    return fundido, len(nosso["etapas"]), len(deles["etapas"]), somados


def e_jsonl_que_so_cresce(caminho: str) -> bool:
    """O caminho é um JSONL append-only declarado? Função pura."""
    return (str(caminho).startswith(PREFIXOS_JSONL_QUE_SO_CRESCEM)
            and str(caminho).endswith(".jsonl"))


def _multiconjunto(base, nosso, deles) -> list:
    """base + o que cada lado tem A MAIS que a base, contando repetição (F50, 13/10/2026).

    Era "os dois lados começam com a base, item a item". Um ramo que já tinha unido a `main` uma
    vez deixava de começar com a base da segunda união (as linhas da `main` ficavam depois das
    dele) e era recusado; o dado de coleta de dia tinha de ser unido à mão. Por multiconjunto a
    ordem não importa, repetição continua contando (duas execuções idênticas são duas) e linha que
    um lado perdeu volta pela base: o resultado nunca é menor que nenhum lado."""
    if str(RAIZ / "scripts") not in sys.path:
        sys.path.insert(0, str(RAIZ / "scripts"))
    from painel_da_noite import unir_paineis
    try:
        return unir_paineis(nosso, deles, base=base)
    except ValueError as e:
        raise Recusa(str(e))


def unir_jsonl(caminho, base_txt, nosso_txt, deles_txt):
    """União pela base comum em LINHAS, por multiconjunto (`_multiconjunto`). Função pura.

    Mesma regra do log em JSON, no formato em que o volume da busca passou a ser gravado. Nunca
    deduplica por conteúdo: foi assim que uma união apagou quase 3.000 execuções em 23/09/2026.
    """
    if nosso_txt is None or deles_txt is None:
        raise Recusa("um dos lados não tem o arquivo; isto não é acréscimo dos dois lados")

    def linhas(txt):
        return [x for x in str(txt).splitlines() if x.strip()]

    lb = linhas(base_txt) if base_txt is not None else []
    ln, ld = linhas(nosso_txt), linhas(deles_txt)
    fundido = _multiconjunto(lb, ln, ld)
    return "\n".join(fundido) + "\n", len(ln), len(ld), len(fundido)


def unir_log(caminho, chave, base_txt, nosso_txt, deles_txt):
    """Une pela base comum, por multiconjunto. Recusa mudança de formato fora da lista."""
    if nosso_txt is None or deles_txt is None:
        raise Recusa("um dos lados não tem o arquivo; isto não é acréscimo dos dois lados")

    nosso, deles = json.loads(nosso_txt), json.loads(deles_txt)
    base = json.loads(base_txt) if base_txt is not None else {chave: []}
    for nome, d in (("nosso", nosso), ("deles", deles), ("base", base)):
        if not isinstance(d, dict) or not isinstance(d.get(chave), list):
            raise Recusa(f"o lado {nome} não tem a lista '{chave}' no formato esperado")

    lb, ln, ld = base[chave], nosso[chave], deles[chave]
    uniao = _multiconjunto(lb, ln, ld)

    # Os escalares do topo: vêm do lado de quem reaplica (deles), que é a rodada.
    #
    # CARIMBO NÃO É MUDANÇA DE FORMATO (08/10/2026, A2-02). Esta conferência recusava o conflito
    # quando QUALQUER escalar diferia — e `atualizado_em` difere sempre, porque cada elo grava a
    # hora em que rodou. `data/saude_pipeline.json` é commitado por todos os elos, então todo
    # conflito da noite caía aqui: na noite de 07→08/10 o laço tentou cinco vezes a mesma união e
    # perdeu diários inteiros (2h23 de coleta), uma descoberta, um juiz e dois sinais.
    #
    # Carimbo de tempo une pelo MAIOR, que é o que `unir_contadores` já fazia. Divergência nos
    # demais escalares continua sendo recusa: ali é mudança de formato, e para isso o script não
    # serve.
    escalares_n = {k: v for k, v in nosso.items() if k != chave}
    escalares_d = {k: v for k, v in deles.items() if k != chave}
    carimbos = {}
    for k in list(escalares_n):
        if k in CARIMBOS and k in escalares_d and escalares_n[k] != escalares_d[k]:
            carimbos[k] = max(str(escalares_n[k]), str(escalares_d[k]))
            escalares_n.pop(k)
            escalares_d.pop(k)
    if escalares_n != escalares_d:
        divergentes = sorted(set(escalares_n) ^ set(escalares_d)) or sorted(
            k for k in escalares_n if escalares_n.get(k) != escalares_d.get(k))
        raise Recusa(f"os campos fora de '{chave}' divergem entre os lados "
                     f"({divergentes}) — mudança de formato")

    fundido = dict(deles)
    fundido.update(carimbos)
    fundido[chave] = uniao
    return fundido, len(ln), len(ld), len(uniao)


def resolver(repo=None, escrever=True):
    """Resolve o que sabe. Devolve (resolvidos, regenerar, recusados)."""
    raiz = pathlib.Path(repo or RAIZ)
    resolvidos, regenerar, recusados, adiados = [], [], [], []

    for caminho in em_conflito(repo=repo):
        norm = caminho.replace("\\", "/")
        try:
            if norm in LOGS_QUE_SO_CRESCEM:
                chave = LOGS_QUE_SO_CRESCEM[norm]
                fundido, a, b, t = unir_log(
                    norm, chave,
                    estagio(norm, 1, repo=repo), estagio(norm, 2, repo=repo),
                    estagio(norm, 3, repo=repo))
                if escrever:
                    gravar_no_formato_do_produtor(raiz / norm, fundido)
                    git("add", "--", norm, repo=repo)
                resolvidos.append(f"{norm}: {a} + {b} → {t} (união pela base comum)")

            elif e_contador_que_so_cresce(norm):
                fundido, a, b, t = unir_contadores(
                    norm,
                    estagio(norm, 1, repo=repo), estagio(norm, 2, repo=repo),
                    estagio(norm, 3, repo=repo))
                if escrever:
                    (raiz / norm).write_text(
                        json.dumps(fundido, ensure_ascii=False, indent=1) + "\n",
                        encoding="utf-8", newline="\n")
                    git("add", "--", norm, repo=repo)
                resolvidos.append(f"{norm}: {a} + {b} etapa(s), {t} contagem(ns) somada(s) "
                                  f"(união pela base comum)")

            elif e_jsonl_que_so_cresce(norm):
                fundido, a, b, t = unir_jsonl(
                    norm,
                    estagio(norm, 1, repo=repo), estagio(norm, 2, repo=repo),
                    estagio(norm, 3, repo=repo))
                if escrever:
                    (raiz / norm).write_text(fundido, encoding="utf-8", newline="\n")
                    git("add", "--", norm, repo=repo)
                resolvidos.append(f"{norm}: {a} + {b} → {t} linha(s) (união pela base comum)")

            elif norm in FILAS_DE_PISTA:
                fundido, a, b, t, m = unir_fila_de_pistas(
                    norm,
                    estagio(norm, 1, repo=repo), estagio(norm, 2, repo=repo),
                    estagio(norm, 3, repo=repo))
                if escrever:
                    # Indentado, como `coletores_base.gravar` grava a fila: o diff do robô tem de
                    # continuar legível, e trocar o formato aqui mudaria o arquivo inteiro.
                    (raiz / norm).write_text(
                        json.dumps(fundido, ensure_ascii=False, indent=1) + "\n",
                        encoding="utf-8", newline="\n")
                    git("add", "--", norm, repo=repo)
                resolvidos.append(f"{norm}: {a} + {b} → {t} pista(s), {m} mesclada(s) "
                                  f"(união pela base comum, política de scripts/pistas.py)")

            elif norm in INDICES_POR_CHAVE:
                fundido, a, b, t = unir_indice(
                    norm,
                    estagio(norm, 1, repo=repo), estagio(norm, 2, repo=repo),
                    estagio(norm, 3, repo=repo))
                if escrever:
                    gravar_no_formato_do_produtor(raiz / norm, fundido)
                    git("add", "--", norm, repo=repo)
                resolvidos.append(f"{norm}: {a} + {b} → {t} entrada(s) (união pela base comum)")

            elif norm in DERIVADOS_COM_GERADOR:
                adiados.append(norm)
                continue

            elif e_regeneravel(norm):
                de_cima = estagio(norm, 2, repo=repo)
                if de_cima is None:
                    raise Recusa("o lado de cima não tem o arquivo")
                if escrever:
                    (raiz / norm).write_text(de_cima, encoding="utf-8", newline="\n")
                    git("add", "--", norm, repo=repo)
                resolvidos.append(f"{norm}: versão de cima (derivado, será regenerado)")
                regenerar.append(norm)

            else:
                raise Recusa("caminho sem resolução conhecida; a política de mesclagem dele "
                             "não está decidida")
        except Recusa as e:
            recusados.append(f"{norm}: {e}")
        except (json.JSONDecodeError, RuntimeError) as e:
            recusados.append(f"{norm}: {type(e).__name__}: {e}")

    # Os derivados com gerador próprio vêm por último: a fonte deles já está unida acima.
    for norm in adiados:
        fonte, gerador = DERIVADOS_COM_GERADOR[norm]
        if any(f"{fonte}:" in r for r in recusados) or fonte in em_conflito(repo=repo):
            recusados.append(f"{norm}: a fonte {fonte} não foi unida; o derivado não se regera")
            continue
        if escrever:
            r = subprocess.run([sys.executable, *gerador], cwd=raiz, capture_output=True, text=True)
            if r.returncode != 0:
                recusados.append(f"{norm}: o gerador {gerador[0]} falhou (rc={r.returncode})")
                continue
            git("add", "--", norm, repo=repo)
        resolvidos.append(f"{norm}: regerado de {fonte} já unido ({gerador[0]})")
    return resolvidos, regenerar, recusados


# ─────────────────────────── autoteste, sem rede e fora do repositório ───────────────────────

def _repo_com_conflito(tmp, caminho, base, nosso, deles):
    """Monta um repositório de verdade e provoca um conflito de verdade no caminho pedido."""
    r = pathlib.Path(tmp)
    amb = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}

    def g(*a, ok_falhar=False):
        p = subprocess.run(["git", *a], cwd=str(r), capture_output=True, env=amb)
        if p.returncode != 0 and not ok_falhar:
            raise RuntimeError(f"git {' '.join(a)}: {p.stderr.decode('utf-8','replace')}")
        return p.returncode

    def escrever(texto):
        alvo = r / caminho
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(texto, encoding="utf-8", newline="")

    g("init", "-q", "-b", "principal")
    if base is not None:
        escrever(base)
        g("add", "-A"); g("commit", "-qm", "base")
    else:
        (r / "semente.txt").write_text("x", encoding="utf-8", newline="\n")
        g("add", "-A"); g("commit", "-qm", "base")

    g("checkout", "-qb", "lado")
    escrever(deles)
    g("add", "-A"); g("commit", "-qm", "deles")

    g("checkout", "-q", "principal")
    escrever(nosso)
    g("add", "-A"); g("commit", "-qm", "nosso")

    # merge (não rebase) porque os estágios 1/2/3 são os mesmos e o teste fica legível
    g("merge", "lado", "-m", "colisao", ok_falhar=True)
    return r


def _log(chave, itens, **escalares):
    d = dict(escalares)
    d[chave] = itens
    return json.dumps(d, ensure_ascii=False, separators=(",", ":"))


def autoteste() -> int:
    falhas = []

    def checar(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    E = {"formato_versao": 2, "formato": "v2"}
    P = "data/log_buscas.json"

    # 1. o caso que acontece toda rodada: os dois lados acrescentaram
    with tempfile.TemporaryDirectory() as t:
        r = _repo_com_conflito(
            t, P,
            _log("execucoes", [{"i": 1}, {"i": 2}], **E),
            _log("execucoes", [{"i": 1}, {"i": 2}, {"i": 3}], **E),          # nosso: +1
            _log("execucoes", [{"i": 1}, {"i": 2}, {"i": 4}, {"i": 5}], **E))  # deles: +2
        res, reg, rec = resolver(repo=r)
        checar("conflito de acréscimo mútuo é resolvido", not rec and len(res) == 1)
        d = json.loads((r / P).read_text(encoding="utf-8"))
        checar("a união é base + nossos_novos + deles_novos, na ordem",
               [x["i"] for x in d["execucoes"]] == [1, 2, 3, 4, 5])
        checar("o total é maior ou igual a cada lado", len(d["execucoes"]) >= 4)
        checar("os escalares do topo sobrevivem",
               d.get("formato_versao") == 2 and d.get("formato") == "v2")
        checar("o caminho resolvido foi adicionado ao índice",
               not em_conflito(repo=r))

    # 1-b. O caso que perdeu a noite de 07→08/10 (A2-02): `data/saude_pipeline.json` com carimbos
    # diferentes nos dois lados, porque cada elo grava a hora em que rodou. Antes disto, recusa em
    # TODO conflito do arquivo que TODO elo commita.
    with tempfile.TemporaryDirectory() as t2:
        S = "data/saude_pipeline.json"
        r = _repo_com_conflito(
            t2, S,
            _log("execucoes", [{"i": 1}, {"i": 2}], formato_versao=2,
                 atualizado_em="2026-10-07T23:00:00"),
            _log("execucoes", [{"i": 1}, {"i": 2}, {"i": 3}], formato_versao=2,
                 atualizado_em="2026-10-08T01:13:00"),
            _log("execucoes", [{"i": 1}, {"i": 2}, {"i": 4}], formato_versao=2,
                 atualizado_em="2026-10-08T02:40:00"))
        res, reg, rec = resolver(repo=r)
        checar("dois lados com `atualizado_em` diferentes UNEM", not rec and len(res) == 1)
        d = json.loads((r / S).read_text(encoding="utf-8"))
        checar("a união do carimbo vence pelo maior",
               d.get("atualizado_em") == "2026-10-08T02:40:00")
        checar("nenhuma execução se perdeu na união",
               [x["i"] for x in d["execucoes"]] == [1, 2, 3, 4])
        checar("a união grava no formato do produtor (indentado), não compacto",
               (r / S).read_text(encoding="utf-8").startswith('{\n "'))

    # 1-c. Divergência que NÃO é carimbo continua sendo recusa: ali é mudança de formato.
    with tempfile.TemporaryDirectory() as t3:
        r = _repo_com_conflito(
            t3, P,
            _log("execucoes", [{"i": 1}], formato_versao=2),
            _log("execucoes", [{"i": 1}, {"i": 2}], formato_versao=2),
            _log("execucoes", [{"i": 1}, {"i": 3}], formato_versao=3))
        res, reg, rec = resolver(repo=r)
        checar("mudança de formato continua recusada", bool(rec) and not res)

    # 2. Um lado ENCURTOU a lista (o estrago de 23/09): a base devolve o que ele perdeu (F50)
    with tempfile.TemporaryDirectory() as t:
        r = _repo_com_conflito(
            t, P,
            _log("execucoes", [{"i": 1}, {"i": 2}, {"i": 3}], **E),
            _log("execucoes", [{"i": 1}], **E),                       # nosso: PERDEU dois
            _log("execucoes", [{"i": 1}, {"i": 2}, {"i": 3}, {"i": 9}], **E))
        res, reg, rec = resolver(repo=r)
        checar("lado que encurtou a lista não apaga nada: a base devolve o que ele perdeu",
               not rec and [x["i"] for x in json.loads((r / P).read_text(encoding="utf-8"))["execucoes"]]
               == [1, 2, 3, 9])

    # 3. Um lado reescreveu item da base: o original fica (a base) e o reescrito também (F50)
    with tempfile.TemporaryDirectory() as t:
        r = _repo_com_conflito(
            t, P,
            _log("execucoes", [{"i": 1}, {"i": 2}], **E),
            _log("execucoes", [{"i": 1}, {"i": 99}, {"i": 3}], **E),   # reescreveu o 2
            _log("execucoes", [{"i": 1}, {"i": 2}, {"i": 4}], **E))
        res, reg, rec = resolver(repo=r)
        checar("item reescrito não apaga o original: os dois ficam",
               not rec and [x["i"] for x in json.loads((r / P).read_text(encoding="utf-8"))["execucoes"]]
               == [1, 2, 99, 3, 4])

    # 4. NEGATIVO: caminho sem política decidida NÃO é adivinhado
    with tempfile.TemporaryDirectory() as t:
        r = _repo_com_conflito(t, "data/municipios.json",
                               '{"municipios":[{"a":1}]}', '{"municipios":[{"a":2}]}',
                               '{"municipios":[{"a":3}]}')
        res, reg, rec = resolver(repo=r)
        checar("caminho sem resolução conhecida é RECUSADO",
               not res and len(rec) == 1 and "não está decidida" in rec[0])

    # 4b. FILA DE PISTA (05/10/2026): a classe nova. Cada lado acrescentou uma pista; nada se perde.
    def _fila(*pistas):
        return json.dumps({"pistas": list(pistas), "atualizado_em": "2026-10-05"},
                          ensure_ascii=False)

    A = {"id": "a1", "url_final": "https://x/a", "alvo": "1", "tipo": "plano", "nivel": "A",
         "data": "2026-10-04", "origem": "busca_web", "status": "pista"}
    B = {"id": "b1", "url_final": "https://x/b", "alvo": "2", "tipo": "plano", "nivel": "B",
         "data": "2026-10-05", "origem": "imprensa", "status": "pista"}
    C = {"id": "c1", "url_final": "https://x/c", "alvo": "3", "tipo": "estrutura", "nivel": "C",
         "data": "2026-10-05", "origem": "diario", "status": "pista"}

    with tempfile.TemporaryDirectory() as t:
        r = _repo_com_conflito(t, "data/pistas_imprensa.json",
                               _fila(A), _fila(A, B), _fila(A, C))
        res, reg, rec = resolver(repo=r)
        checar("fila de pista: os acréscimos dos DOIS lados entram",
               not rec and len(res) == 1 and "3 pista(s)" in res[0])
        doc = json.loads((pathlib.Path(r) / "data/pistas_imprensa.json").read_text(encoding="utf-8"))
        checar("fila de pista: a união tem as três, na ordem base → nossas → delas",
               [x["id"] for x in doc["pistas"]] == ["a1", "b1", "c1"])

    with tempfile.TemporaryDirectory() as t:
        # Cada lado tocou um CAMPO DIFERENTE da mesma pista: é o caso comum da noite — a triagem
        # escreve `triagem`, o seguimento escreve `seguimento`. Os dois entram.
        r = _repo_com_conflito(t, "data/pistas_imprensa.json",
                               _fila(A),
                               _fila(dict(A, triagem="automatica")),
                               _fila(dict(A, seguimento={"data": "05/10/2026"})))
        res, reg, rec = resolver(repo=r)
        doc = json.loads((pathlib.Path(r) / "data/pistas_imprensa.json").read_text(encoding="utf-8"))
        checar("fila de pista: campos diferentes da mesma pista se MESCLAM",
               not rec and doc["pistas"][0].get("triagem") == "automatica"
               and doc["pistas"][0].get("seguimento", {}).get("data") == "05/10/2026")
        checar("fila de pista: a mescla é contada na saída", "1 mesclada(s)" in res[0])

    with tempfile.TemporaryDirectory() as t:
        # O MESMO campo, valores diferentes: a pergunta é real, e o script não a responde.
        r = _repo_com_conflito(t, "data/pistas_imprensa.json",
                               _fila(A),
                               _fila(dict(A, status="fechada — sem documento")),
                               _fila(dict(A, status="aplicada")))
        res, reg, rec = resolver(repo=r)
        checar("fila de pista: o MESMO campo com valores diferentes é RECUSADO",
               not res and len(rec) == 1 and "qual vence é política" in rec[0])

    with tempfile.TemporaryDirectory() as t:
        # Sem base comum (arquivo nasceu nos dois lados): a união é nossas + delas.
        r = _repo_com_conflito(t, "data/pistas_doe.json", None, _fila(A, B), _fila(A, C))
        res, reg, rec = resolver(repo=r)
        doc = json.loads((pathlib.Path(r) / "data/pistas_doe.json").read_text(encoding="utf-8"))
        checar("fila de pista sem base comum: nada se perde",
               not rec and sorted(x["id"] for x in doc["pistas"]) == ["a1", "b1", "c1"])

    with tempfile.TemporaryDirectory() as t:
        # A trava de 23/09, aplicada à fila: a união nunca é menor que o maior dos lados.
        r = _repo_com_conflito(t, "data/pistas_imprensa.json",
                               _fila(A), _fila(A, B), _fila(A, B, C))
        res, reg, rec = resolver(repo=r)
        doc = json.loads((pathlib.Path(r) / "data/pistas_imprensa.json").read_text(encoding="utf-8"))
        checar("fila de pista: a união nunca é menor que o maior dos lados",
               not rec and len(doc["pistas"]) == 3)

    # 05/10/2026 - as cinco classes que faltavam, e que pararam a triagem das 18:58.
    checar("JSONL do log de buscas tem classe", e_jsonl_que_so_cresce("data/log_buscas/2026-10.jsonl"))
    checar("JSON solto na mesma pasta NAO e tratado como JSONL",
           not e_jsonl_que_so_cresce("data/log_buscas/2026-10.json"))
    checar("JSONL de outra pasta nao entra por engano",
           not e_jsonl_que_so_cresce("data/outro/2026-10.jsonl"))
    _u = unir_jsonl("x.jsonl", "a\nb\n", "a\nb\nc\n", "a\nb\nd\n")
    checar("JSONL une pela base comum", _u[0] == "a\nb\nc\nd\n" and _u[3] == 4)
    checar("JSONL unido nunca e menor que um lado", _u[3] >= max(_u[1], _u[2]))
    checar("JSONL com remocao nao apaga: a base devolve a linha",
           unir_jsonl("x.jsonl", "a\nb\n", "a\n", "a\nb\nd\n")[0] == "a\nb\nd\n")
    checar("F50: ramo que ja uniu a main uma vez une de novo (ordem nao importa)",
           unir_jsonl("x.jsonl", "a\nm1\n", "a\nn1\nm1\n", "a\nm1\nm2\n")[0] == "a\nm1\nn1\nm2\n")
    checar("o funil do dia tem classe", e_contador_que_so_cresce("data/funil/2026-10-05.json"))
    checar("outro json nao entra como contador", not e_contador_que_so_cresce("data/meta.json"))
    _b = '{"data":"2026-10-05","formato_versao":1,"etapas":{"juiz":{"recebidas":10}}}'
    _n = '{"data":"2026-10-05","formato_versao":1,"etapas":{"juiz":{"recebidas":14}}}'
    _d = '{"data":"2026-10-05","formato_versao":1,"etapas":{"juiz":{"recebidas":13},"doe":{"x":2}}}'
    _f = unir_contadores("data/funil/x.json", _b, _n, _d)
    checar("contagem soma os dois acrescimos sobre a base",
           _f[0]["etapas"]["juiz"]["recebidas"] == 17)
    checar("etapa que so um lado tem entra inteira", _f[0]["etapas"]["doe"]["x"] == 2)
    checar("a uniao de contadores nunca fica menor que um lado",
           _f[0]["etapas"]["juiz"]["recebidas"] >= 14)
    try:
        unir_contadores("data/funil/x.json", _b,
                        '{"data":"2026-10-05","formato_versao":1,"etapas":{"juiz":{"recebidas":9}}}',
                        _d)
        checar("decremento e RECUSADO", False)
    except Recusa:
        checar("decremento e RECUSADO", True)
    try:
        unir_contadores("data/funil/x.json", _b, _n,
                        '{"data":"2026-10-04","formato_versao":1,"etapas":{"juiz":{"recebidas":13}}}')
        checar("campo fora de etapas divergente e RECUSADO", False)
    except Recusa:
        checar("campo fora de etapas divergente e RECUSADO", True)
    checar("o painel da noite e log que so cresce, pela chave `noites`",
           LOGS_QUE_SO_CRESCEM.get("data/painel_da_noite.json") == "noites")
    # F44: os dois lados podaram a cabeça da base (o corte de 400): une, e a base não se perde.
    with tempfile.TemporaryDirectory() as t:
        _l = lambda e, n, i: {"elo": e, "noite": n, "inicio": i}
        _base = [_l("a", "2026-10-11", "01:00"), _l("b", "2026-10-11", "01:10")]
        r = _repo_com_conflito(
            t, "data/painel_da_noite.json",
            json.dumps({"noites": _base}),
            json.dumps({"noites": _base[1:] + [_l("c", "2026-10-12", "01:05")]}),
            json.dumps({"noites": _base[1:] + [_l("d", "2026-10-12", "01:44")]}))
        res, reg, rec = resolver(repo=r)
        _f = json.loads((r / "data/painel_da_noite.json").read_text(encoding="utf-8"))["noites"]
        checar("F44: painel com cabeça podada nos dois lados é UNIDO, não recusado",
               not rec and [x["elo"] for x in _f] == ["a", "b", "c", "d"])
    checar("o resumo do log e o card de municipios sao regeneraveis",
           e_regeneravel("data/log_buscas_resumo.json") and e_regeneravel("data/municipios_card.json"))

    checar("data/pistas_revisao.json segue DERIVADO, não fila (ele é função da fila)",
           "data/pistas_revisao.json" in REGENERAVEIS
           and "data/pistas_revisao.json" not in FILAS_DE_PISTA)

    # 5. NEGATIVO: mudança de formato no meio do conflito não passa
    with tempfile.TemporaryDirectory() as t:
        r = _repo_com_conflito(
            t, P,
            _log("execucoes", [{"i": 1}], formato_versao=2, formato="v2"),
            _log("execucoes", [{"i": 1}, {"i": 2}], formato_versao=2, formato="v2"),
            _log("execucoes", [{"i": 1}, {"i": 3}], formato_versao=3, formato="v3"))
        res, reg, rec = resolver(repo=r)
        checar("divergência nos campos fora da lista é RECUSADA",
               not res and len(rec) == 1 and "mudança de formato" in rec[0])

    # 6. derivado resolve com a versão de cima e é NOMEADO para regeneração
    with tempfile.TemporaryDirectory() as t:
        r = _repo_com_conflito(t, "docs/MANIFEST_SHA256.txt",
                               "a\nb\n", "a\nDE_CIMA\n", "a\nDA_RODADA\n")
        res, reg, rec = resolver(repo=r)
        checar("derivado é resolvido com a versão de cima",
               not rec and (r / "docs/MANIFEST_SHA256.txt").read_text(encoding="utf-8")
               == "a\nDE_CIMA\n")
        checar("derivado é nomeado para regeneração",
               reg == ["docs/MANIFEST_SHA256.txt"])

    # 6b. derivado com gerador próprio (11/10/2026): regera a partir da fonte já unida
    with tempfile.TemporaryDirectory() as t:
        r = _repo_com_conflito(t, "docs/SAUDE_PIPELINE.md", "a\n", "a\nNOSSO\n", "a\nDELES\n")
        (r / "scripts").mkdir(exist_ok=True)
        (r / "scripts" / "gerar_saude_pipeline.py").write_text(
            "import pathlib\npathlib.Path('docs/SAUDE_PIPELINE.md').write_text('REGERADO\\n', "
            "encoding='utf-8', newline='\\n')\n", encoding="utf-8", newline="\n")
        res, reg, rec = resolver(repo=r)
        checar("painel de saúde é REGERADO, não escolhido de um lado",
               not rec and (r / "docs/SAUDE_PIPELINE.md").read_text(encoding="utf-8") == "REGERADO\n"
               and not em_conflito(repo=r))
    with tempfile.TemporaryDirectory() as t:
        r = _repo_com_conflito(t, "docs/SAUDE_PIPELINE.md", "a\n", "a\nNOSSO\n", "a\nDELES\n")
        (r / "scripts").mkdir(exist_ok=True)
        (r / "scripts" / "gerar_saude_pipeline.py").write_text(
            "raise SystemExit(3)\n", encoding="utf-8", newline="\n")
        res, reg, rec = resolver(repo=r)
        checar("gerador que falha RECUSA o derivado (não adivinha)",
               len(rec) == 1 and "falhou" in rec[0])

    # 7. a base pode não existir (arquivo criado dos dois lados) e ainda assim unir
    with tempfile.TemporaryDirectory() as t:
        r = _repo_com_conflito(
            t, P, None,
            _log("execucoes", [{"i": 1}], **E),
            _log("execucoes", [{"i": 2}], **E))
        res, reg, rec = resolver(repo=r)
        d = json.loads((r / P).read_text(encoding="utf-8")) if not rec else {}
        checar("sem base comum, a união é nosso + deles",
               not rec and [x["i"] for x in d["execucoes"]] == [1, 2])

    # 9. §252: derivado sob prefixo declarado resolve, em vez de ser recusado. O caso real da
    #    rodada de 27/09 às 08h29, que recusou dados-abertos/verificacao_municipal.csv.
    with tempfile.TemporaryDirectory() as t:
        r = _repo_com_conflito(t, "dados-abertos/verificacao_municipal.csv",
                               "a\nb\n", "a\nDE_CIMA\n", "a\nDA_RODADA\n")
        res, reg, rec = resolver(repo=r)
        checar("derivado sob dados-abertos/ é RESOLVIDO, não recusado",
               not rec and reg == ["dados-abertos/verificacao_municipal.csv"])
        checar("e resolve com a versão de cima",
               (r / "dados-abertos/verificacao_municipal.csv").read_text(encoding="utf-8")
               == "a\nDE_CIMA\n")

    # 10. NEGATIVO: caminho que NÃO é derivado nem log declarado segue recusado. O prefixo novo
    #     não pode ter virado uma porta larga.
    with tempfile.TemporaryDirectory() as t:
        r = _repo_com_conflito(t, "data/municipios.json", '[]', '[1]', '[2]')
        res, reg, rec = resolver(repo=r)
        checar("data/municipios.json segue RECUSADO (política não decidida)",
               not res and len(rec) == 1 and "não está decidida" in rec[0])

    # 8. O CASO DE 23/09, e o único que separa união-pela-base de dedução-por-conteúdo.
    #    Execuções IDÊNTICAS no log v2 são tentativas reais distintas e CONTAM. Uma dedução
    #    por conteúdo colapsaria as duas em uma e apagaria uma tentativa sem aviso — foi assim
    #    que quase 3.000 execuções sumiram. Sem esta asserção o autoteste passa com o defeito
    #    dentro: descoberto ao restaurar o defeito de propósito, em 27/09/2026.
    #    Os dois lados precisam DIFERIR em algo, senão o git mescla limpo e não há conflito
    #    para resolver — por isso cada um traz também uma execução só sua.
    with tempfile.TemporaryDirectory() as t:
        igual = {"municipio": "Recife", "consulta": "plano de contingência", "achou": 0}
        r = _repo_com_conflito(
            t, P,
            _log("execucoes", [], **E),
            _log("execucoes", [dict(igual), {"i": "nosso"}], **E),
            _log("execucoes", [dict(igual), {"i": "deles"}], **E))
        res, reg, rec = resolver(repo=r)
        d = json.loads((r / P).read_text(encoding="utf-8")) if not rec else {"execucoes": []}
        iguais = sum(1 for x in d["execucoes"] if x.get("municipio") == "Recife")
        checar("duas execuções idênticas são DUAS tentativas, não uma "
               "(nunca deduzir por conteúdo)", len(d["execucoes"]) == 4 and iguais == 2)

    # F55: os dois índices que todo elo escreve se unem; nada de um lado se perde.
    def _doc(chave, d):
        return json.dumps({"_governanca": "x", chave: d})
    with tempfile.TemporaryDirectory() as t:
        EV = "data/evidencias.json"
        r = _repo_com_conflito(t, EV, _doc("itens", {"a": {"ocr": 0}}),
                               _doc("itens", {"a": {"ocr": 1}, "b": {"x": 1}}),
                               _doc("itens", {"a": {"ocr": 0}, "c": {"x": 2}}))
        res, reg, rec = resolver(repo=r)
        d = json.loads((r / EV).read_text(encoding="utf-8")) if not rec else {"itens": {}}
        checar("F55: índice de evidências une as entradas novas e a mudança de um lado só",
               not rec and d["itens"] == {"a": {"ocr": 1}, "b": {"x": 1}, "c": {"x": 2}})
    with tempfile.TemporaryDirectory() as t:
        RB = "data/robots_registro.json"
        ac = lambda u: {"url": u, "quando": u}
        h0 = {"total_acessos": 1, "acessos": [ac("0")], "ultimo_acesso": "2026-10-13", "primeiro_acesso": "2026-09-28"}
        r = _repo_com_conflito(t, RB, _doc("hosts", {"x.br": h0}),
                               _doc("hosts", {"x.br": {**h0, "total_acessos": 2, "acessos": [ac("0"), ac("1")], "ultimo_acesso": "2026-10-14"}}),
                               _doc("hosts", {"x.br": {**h0, "total_acessos": 3, "acessos": [ac("0"), ac("2"), ac("3")]}, "y.br": h0}))
        res, reg, rec = resolver(repo=r)
        d = json.loads((r / RB).read_text(encoding="utf-8")) if not rec else {"hosts": {}}
        x = d["hosts"].get("x.br") or {}
        checar("F55: registro de robots soma os acessos dos dois lados, sem perder host",
               not rec and x.get("total_acessos") == 4 and len(x.get("acessos") or []) == 4
               and x.get("ultimo_acesso") == "2026-10-14" and "y.br" in d["hosts"])
    with tempfile.TemporaryDirectory() as t:
        LV = "data/fontes_consultadas.json"
        f = lambda fonte, dia: {"fonte": fonte, "data": dia, "resultado": "r"}
        m0 = {"nivel_verificacao": "nacional", "ultima_verificacao": "2026-10-13", "fontes": [f("DOU", "2026-10-13")]}
        r = _repo_com_conflito(t, LV, _doc("municipios", {"1": m0}),
                               _doc("municipios", {"1": {**m0, "ultima_verificacao": "2026-10-15",
                                                         "fontes": m0["fontes"] + [f("QD", "2026-10-15")]}}),
                               _doc("municipios", {"1": {**m0, "nivel_verificacao": "estadual", "ultima_verificacao": "2026-10-14",
                                                         "fontes": m0["fontes"] + [f("Busca web", "2026-10-14")]}}))
        res, reg, rec = resolver(repo=r)
        m = json.loads((r / LV).read_text(encoding="utf-8"))["municipios"]["1"] if not rec else {}
        checar("F58: livro de fontes une as consultas dos dois lados; nível não rebaixa",
               [x["fonte"] for x in m.get("fontes", [])] == ["DOU", "Busca web", "QD"]
               and m.get("nivel_verificacao") == "estadual" and m.get("ultima_verificacao") == "2026-10-15")

    if falhas:
        print(f"\n✗ UNIÃO DE CONFLITO: {len(falhas)} falha(s).")
        return 1
    print("\n✓ UNIÃO DE CONFLITO OK — une o que sabe pela base comum, recusa o resto.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv[1:]:
        return autoteste()

    resolvidos, regenerar, recusados = resolver()
    if not resolvidos and not recusados:
        print("Nada em conflito.")
        return 0
    for r in resolvidos:
        print(f"  resolvido  {r}")
    for r in recusados:
        print(f"  RECUSADO   {r}")
    if regenerar:
        print("REGENERAR=" + " ".join(regenerar))
    if recusados:
        print(f"::error::{len(recusados)} caminho(s) sem resolução conhecida; a rodada não "
              f"comita. Adivinhar a mesclagem apagaria dado sem aviso.")
        return 2
    print(f"{len(resolvidos)} caminho(s) resolvido(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
