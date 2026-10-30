#!/usr/bin/env python3
"""Rejulga, com a prova já preservada, as decisões gravadas por uma versão anterior do codebook.

28/09/2026. A primeira passada real do juiz promoveu **cinco** registros, e quatro eram falsos:

  Salto/SP, Apucarana/PR, Goiânia/GO   nenhuma ocorrência de termo de plano nos 20.000 caracteres
                                       julgados (Apucarana casou em "Comitê Gestor do Programa
                                       Sandbox"; Goiânia saiu com data de 21/08/1959)
  Alagoinhas/BA                        "Plano de Contingência / PGR" dentro de condicionante de
                                       licença ambiental — obrigação imposta a um licenciado
  Serra/ES                             verdadeiro: "Art. 1º Fica instituído o Plano Municipal de
                                       Proteção e Defesa Civil (PMPDEC)"

A causa está no `juiz.py` e foi consertada lá (Etapa 4 passou a exigir verbo E instrumento na mesma
vizinhança, codebook 1.1). Este script cuida do que já estava gravado.

O QUE ELE FAZ
-------------
Relê a evidência preservada de cada decisão (pelo `hash_evidencia`, do disco, **sem rede**), rejulga
com o codebook em vigor e acrescenta o veredito novo. A decisão antiga **não é apagada**: recebe
`superada_por` com a versão nova e a data, e continua no arquivo. O registro de decisões é o que
alimenta a auditoria amostral semanal — apagar o erro tiraria da auditoria exatamente o caso que ela
precisa ver.

Decisão sem evidência no disco não é rejulgada (não houve documento lido; são as recusas de Etapa 0)
— ela volta à fila pela própria troca de versão do codebook, que é o caminho normal.

USO
  python3 scripts/rejulgar_decisoes_do_juiz.py              # relatório, nada escrito
  python3 scripts/rejulgar_decisoes_do_juiz.py --escrever
  python3 scripts/rejulgar_decisoes_do_juiz.py --autoteste
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

REGISTRO = RAIZ / "data" / "promocoes_automaticas.json"
EVIDENCIAS = RAIZ / "evidencias"


def pendente_de_rejulgamento(v: dict, versao_atual: str) -> bool:
    """Decisão de versão anterior, ainda não superada."""
    return v.get("codebook") != versao_atual and not v.get("superada_por")


def marcar_superada(v: dict, versao_nova: str, data: str) -> dict:
    """A decisão antiga fica, dizendo por quem foi superada. Nada se apaga."""
    v["superada_por"] = {"codebook": versao_nova, "em": data}
    return v


def caminho_da_evidencia(hash_evidencia, pasta=None):
    pasta = pasta or EVIDENCIAS
    if not hash_evidencia:
        return None
    # O texto extraído (.txt) é o que o juiz julgou; o .pdf ao lado é o byte original (15/10/2026:
    # a ordem alfabética entregava o PDF cru, e o rejulgamento recusava por "ente não confirmado").
    achados = sorted(pasta.glob(str(hash_evidencia) + ".*"), key=lambda a: a.suffix != ".txt")
    return achados[0] if achados else None


def autoteste() -> int:
    casos = []
    v_velha = {"codebook": "1.0 (27/09/2026)", "promove": True}
    casos.append(("decisão de versão anterior é rejulgada",
                  pendente_de_rejulgamento(v_velha, "1.1 (28/09/2026)")))
    casos.append(("decisão da versão em vigor não é rejulgada",
                  not pendente_de_rejulgamento({"codebook": "1.1 (28/09/2026)"}, "1.1 (28/09/2026)")))
    ja = dict(v_velha, superada_por={"codebook": "1.1 (28/09/2026)", "em": "2026-09-28"})
    casos.append(("decisão já superada não é rejulgada de novo",
                  not pendente_de_rejulgamento(ja, "1.1 (28/09/2026)")))

    antiga = {"codebook": "1.0 (27/09/2026)", "promove": True, "municipio": "Salto"}
    marcada = marcar_superada(dict(antiga), "1.1 (28/09/2026)", "2026-09-28")
    casos.append(("a decisão antiga permanece no arquivo, inteira",
                  marcada["promove"] is True and marcada["municipio"] == "Salto"))
    casos.append(("a decisão antiga diz por quem foi superada",
                  marcada["superada_por"]["codebook"] == "1.1 (28/09/2026)"))
    casos.append(("nada é apagado: a chave original do veredito continua lá",
                  "codebook" in marcada and marcada["codebook"] == "1.0 (27/09/2026)"))

    import tempfile
    with tempfile.TemporaryDirectory() as d:
        pasta = pathlib.Path(d)
        (pasta / ("a" * 64 + ".txt")).write_text("x", encoding="utf-8")  # escrita-nao-portavel-ok: arquivo de um caractere em diretório temporário do autoteste, nunca versionado
        casos.append(("acha a evidência pelo hash", caminho_da_evidencia("a" * 64, pasta) is not None))
        (pasta / ("a" * 64 + ".pdf")).write_text("%PDF", encoding="utf-8")  # escrita-nao-portavel-ok: diretório temporário do autoteste
        casos.append(("com .pdf ao lado, entrega o texto", caminho_da_evidencia("a" * 64, pasta).suffix == ".txt"))
        casos.append(("hash sem arquivo devolve None", caminho_da_evidencia("b" * 64, pasta) is None))
        casos.append(("hash vazio devolve None", caminho_da_evidencia(None, pasta) is None))

    # rodada paralela 1.8: o "antes" é a última decisão da chave; a fila passa pelas regras B
    hist = [{"pista_id": "p", "url": "u", "codebook": "1.5", "promove": True},
            {"pista_id": "p", "url": "u", "codebook": "1.7", "promove": False}]
    casos.append(("1.8: o antes é a decisão vigente da chave", vigentes(hist)[chave_18(hist[0])]["codebook"] == "1.7"))
    f = triar_fila_18([{"id": "a", "url": "https://www.reddit.com/r/x", "nivel": "A"},
                       {"id": "b", "url": "https://ouro.sc.gov.br/p.pdf", "nivel": "C", "municipio": "Ouro"},
                       {"id": "c", "url": "https://x.ac.gov.br/a", "nivel": "A", "municipio": "defesa_civil", "uf": "AC"}],
                      set())
    casos.append(("1.8: a fila descarta Reddit na porta, conta por domínio e põe o nível A primeiro",
                  [p["id"] for p in f["pistas"]] == ["c", "b"] and f["descartadas_por_dominio"] == {"www.reddit.com": 1}
                  and f["pistas"][0]["municipio"] is None and f["pistas"][0]["setor_18"] == "defesa_civil"))

    v18 = {"pista_id": "p", "url": "u", "municipio": "Taió", "uf": "SC", "municipio_da_pista": "Rio do Oeste",
           "uf_da_pista": "SC"}
    casos.append(("1.8: a chave salva é a da pista, não a do município do veredito (J5)",
                  chave_18(dict(v18, municipio=v18["municipio_da_pista"], uf=v18["uf_da_pista"]))
                  == chave_18({"pista_id": "p", "url": "u", "municipio": "Rio do Oeste", "uf": "SC"})))

    lido = {"promove": True, "categoria": "plano_antigo", "regras_18": [], "motivo": None,
            "com_propostas_J8_J9": {"promove": True, "categoria": "plano_recorrente"}}
    errata = {"promove": False, "motivo": "errata: comitê da dengue", "categoria": "plano_antigo", "errata": {"em": "x"}}
    h = herdar_18(dict(lido, regras_18=["J7"]), errata)
    casos.append(("1.8: a errata da linha manda, com ou sem regra 1.8 (Birigui/SP)",
                  h["promove"] is False and h["mantido_18"]["por"] == "errata"
                  and h["com_propostas_J8_J9"]["promove"] is False and herdar_18(h, errata) == h))
    casos.append(("1.8: sem regra 1.8 o veredito não muda; na fila, quem decide é o juiz de produção (Mogi Guaçu/SP)",
                  herdar_18(lido, None)["promove"] is False and herdar_18(lido, None)["mantido_18"]["por"] == "sem_regra"
                  and herdar_18(dict(lido, regras_18=["J1"]), None)["promove"] is True
                  and herdar_18(lido, {"promove": True, "categoria": "plano_antigo"}) == lido))

    lida, falhou = dict(lido, leu_documento=True), {"promove": False, "motivo": "documento_inacessivel"}
    casos.append(("1.8: releitura que não chega ao documento não apaga a leitura anterior; sem leitura anterior, vale",
                  vale_a_leitura_18(lida, falhou) is lida and vale_a_leitura_18(None, falhou) is falhou
                  and vale_a_leitura_18(lida, dict(lido, leu_documento=True, motivo="x"))["motivo"] == "x"))

    casos.append(("1.8: o que --refazer pede vem primeiro; depois o nunca tentado; a leitura que falhou, por último",
                  sorted([("falhou", False, falhou), ("refazer", True, lida), ("nova", False, None)],
                         key=lambda t: ordem_18(t[1], t[2]))[0][0] == "refazer"
                  and [n for n, *_ in sorted([("falhou", False, falhou), ("nova", False, None)],
                                             key=lambda t: ordem_18(t[1], t[2]))] == ["nova", "falhou"]))

    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos, sem rede e sem escrita.")
    return 0


# =============================================================================================
# Codebook 1.8 — RODADA PARALELA (handover da central de 26/10/2026)
# =============================================================================================
# `--codebook 1.8 --saida data/paralelo_juiz18.json`: rejulga cada decisão (uma vez por pista e URL, com
# a decisão vigente como "antes") e grava SÓ na saída. `--fila` tria as pistas em fila pelas regras B
# (B1, B3, B6) em `data/paralelo_fila18.json`. `--rede N` lê até N URLs novas por rodada (válvula
# `coleta-dia/*`): decisões e fila, por prioridade; sem `--rede`, só o que se decide sem documento.
# Retomável: chave já julgada com documento não volta. Nenhum arquivo de produção é escrito.
SAIDA_18 = RAIZ / "data" / "paralelo_juiz18.json"
FILA_18 = RAIZ / "data" / "paralelo_fila18.json"
STATUS_EM_FILA = "pista — na fila"


def chave_18(p: dict) -> str:
    return "|".join(str(p.get(c) or "") for c in ("pista_id", "url", "municipio", "uf"))


def vigentes(decisoes: list) -> dict:
    """A última decisão de cada chave (pista, URL, município, UF): é o "antes" do rejulgamento. PURA."""
    out = {}
    for v in decisoes:
        out[chave_18(v)] = v
    return out


def compacto_18(v: dict) -> dict:
    return {k: v.get(k) for k in ("promove", "motivo", "categoria", "data", "municipio", "uf", "ibge",
                                  "familia_de_risco", "sem_ato_de_aprovacao", "codebook", "regras_18") if k in v}


def herdar_18(novo: dict, antes) -> dict:
    """O veredito 1.8 só muda por regra 1.8, e a errata da linha manda (central, 28/10: Birigui e Mogi Guaçu/SP).
    PURA e idempotente: o que foi lido fica em `mantido_18`. `antes` é a decisão vigente (None na fila: lá o
    "antes" é não promover, e quem decide sem regra 1.8 é o juiz de produção)."""
    antes = antes or {"promove": False, "motivo": "sem_regra_18", "categoria": None, "data": None}
    por = "errata" if antes.get("errata") else (
        "sem_regra" if not novo.get("regras_18") and (novo.get("promove"), novo.get("categoria"))
        != (bool(antes.get("promove")), antes.get("categoria")) else None)
    if not por or novo.get("mantido_18"):
        return novo
    herdado = {k: antes.get(k) for k in ("promove", "motivo", "categoria", "data")}
    herdado["promove"] = bool(herdado["promove"]) and por != "errata"
    out = dict(novo, **herdado, mantido_18={"por": por, "lido": compacto_18(novo)})
    for variante in VARIANTES_18:   # regra da própria variante muda a variante; a errata manda em todas
        propria = set((novo.get(variante) or {}).get("regras_18") or []) - set(novo.get("regras_18") or [])
        if novo.get(variante) and (por == "errata" or not propria):
            out[variante] = dict(novo[variante], **herdado)
    return out


def vale_a_leitura_18(anterior, novo) -> dict:
    """Releitura que não chegou ao documento não apaga a leitura anterior (lote 12 de 29/10: 46 chaves lidas
    voltaram como "documento_inacessivel"). PURA."""
    return anterior if anterior and anterior.get("leu_documento") and not novo.get("leu_documento") else novo


def ordem_18(refeita: bool, anterior) -> tuple:
    """Ordem do trabalho. Lote 15 de 29/10: `--refazer J19 --rede 200` gastou as leituras em chaves nunca lidas e
    não releu nenhuma das 56 da J19, então o que `--refazer` pede vem primeiro. Depois o nunca tentado: em 29/10,
    19 h, 849 leituras que já tinham falhado iam antes de 3.233 pistas da fila nunca lidas. PURA."""
    return (not refeita, anterior is not None)


# Regras medidas à parte: J8/J9 (propostas). A segunda leva está no padrão desde 30/10; `com_segunda_leva` já gravado fica.
VARIANTES_18 = {"com_propostas_J8_J9": "PROPOSTAS_18"}


def julgar_18(p: dict, buscar, propostas=False) -> dict:
    import juiz
    from julgar_filas import julgar_uma
    novo = julgar_uma(p, buscar)
    if propostas and novo.get("leu_documento"):
        texto = buscar(p.get("url"))
        for variante, conjunto in VARIANTES_18.items():
            novo[variante] = compacto_18(juiz.julgar(
                texto, nome=p.get("municipio") or "", uf=p.get("uf") or "", ibge=p.get("ibge"), url=p.get("url"),
                trecho=p.get("trecho"), propostas=getattr(juiz, conjunto)))
    return novo


def triar_fila_18(pistas: list, veiculos) -> dict:
    """B1, B3 e B6 sobre as pistas em fila. PURA: devolve o documento da fila paralela."""
    from collections import Counter
    from pistas import REDIRECIONADORES, entrada_18, prioridade_18, sem_rotulo_de_setor
    aceitas, agregadores, fora = [], [], Counter()
    for bruta in pistas:
        p = sem_rotulo_de_setor(bruta)
        if any(r in str(p.get("url") or "") for r in REDIRECIONADORES) and not p.get("url_final"):
            agregadores.append({"id": p.get("id"), "url": p.get("url"), "titulo": p.get("titulo"),
                                "veiculo_dominio": p.get("veiculo_dominio"), "municipio": p.get("municipio"),
                                "uf": p.get("uf"), "ibge": p.get("ibge"), "nivel": p.get("nivel"),
                                "prioridade": prioridade_18(p), "tentativas_b2": 0})   # B2: resolver antes da porta
            continue
        ok, papel = entrada_18(p, veiculos)
        if not ok:
            fora[papel.split(": ", 1)[-1]] += 1
            continue
        aceitas.append({"id": p.get("id"), "url": p.get("url_final") or p.get("url"), "municipio": p.get("municipio"),
                        "uf": p.get("uf"), "ibge": p.get("ibge"), "nivel": p.get("nivel"),
                        "origem": p.get("origem"), "papel": papel, "prioridade": prioridade_18(p),
                        **({"setor_18": p["setor_18"]} if p.get("setor_18") else {})})
    aceitas.sort(key=lambda x: x["prioridade"])
    agregadores.sort(key=lambda x: x["prioridade"])
    return {"pistas": aceitas, "agregadores": agregadores, "descartadas_por_dominio": dict(fora.most_common()),
            "totais": {"em_fila": len(pistas), "aceitas": len(aceitas), "agregadores_a_resolver": len(agregadores),
                       "descartadas": sum(fora.values())}}


def candidata_18(c: dict, origem: dict, rota: str) -> dict:
    """Candidato de B2 ou B4 vira pista da fila paralela, ligada à de origem."""
    from pistas import prioridade_18
    import hashlib
    p = {"id": f"{origem.get('id') or origem.get('pista_id')}>{hashlib.sha1(c['url'].encode()).hexdigest()[:8]}",
         "url": c["url"],
         "trecho": c.get("trecho"), "municipio": origem.get("municipio"), "uf": origem.get("uf"),
         "ibge": origem.get("ibge"), "nivel": origem.get("nivel"), "origem": rota, "papel": "dominio_publico"}
    p["prioridade"] = prioridade_18(p)
    return p


def buscar_18():
    """O leitor com rede da rodada: B5 (espera crescente e registro) na pasta do RS; o resto, uma vez."""
    from julgar_e_aplicar_descobertas import (HOST_SHAREPOINT_RS, TETO_DA_LEITURA, _ler_sharepoint_rs,
                                              buscar_texto, extrair_texto_pdf)
    from seguir_pistas import ler_com_espera_18
    registros, cache = [], {}

    def ler_rs(url):
        # Lote 5 de 27/10: com `buscar_texto`, que engole o erro, 95 arquivos saíram "inacessível" sem causa e
        # cada um gastou 3 tentativas. Aqui o erro sobe (401/403/429 é recusa e encerra) e "" é PDF sem texto.
        raw = _ler_sharepoint_rs(url, 60)
        if raw[:5] == b"%PDF-":
            return (extrair_texto_pdf(raw) or "")[:TETO_DA_LEITURA]
        return raw.decode("utf-8", errors="ignore")[:TETO_DA_LEITURA]

    def ler(url):
        if url in cache:
            return cache[url]
        if HOST_SHAREPOINT_RS in str(url):
            texto, reg = ler_com_espera_18(url, ler_rs)
            registros.append(reg)
        else:
            texto = buscar_texto(url)
        cache[url] = texto
        return texto
    return ler, registros


def paralelo_18(argv) -> int:
    from coletores_base import gravar_em, hoje_editorial
    from juiz import CODEBOOK_VERSAO, fonte_oficial
    rede = int(argv[argv.index("--rede") + 1]) if "--rede" in argv else 0
    propostas = "--propostas" in argv
    # `--refazer J1,J7`: relê a chave já lida cujo veredito usou uma regra que mudou depois (lote 7 da J18);
    # a regra pedida vale também quando agiu só numa variante (`--refazer J8`).
    refazer = set(argv[argv.index("--refazer") + 1].split(",")) if "--refazer" in argv else set()
    saida = RAIZ / argv[argv.index("--saida") + 1] if "--saida" in argv else SAIDA_18
    doc = json.loads(saida.read_text(encoding="utf-8")) if saida.exists() else {
        "_governanca": ("Rodada paralela do juiz, codebook 1.8 (handover da central de 26/10/2026). Nenhuma página "
                        "lê este arquivo; a troca para o 1.8 é decisão da editoria. `rejulgada_de` é a decisão "
                        "vigente (1.7 ou anterior) da mesma pista e URL."),
        "codebook": CODEBOOK_VERSAO, "decisoes": []}
    # A chave é a da PISTA: o veredito pode ter mudado o município (J5/J6), e a chave pelo veredito fazia a
    # mesma pista ser relida a cada lote (113 repetidas até o lote 6).
    feitas = {}
    for v in doc["decisoes"]:
        feitas[chave_18(dict(v, municipio=v.get("municipio_da_pista"), uf=v.get("uf_da_pista")))] = v
    ler, registros = buscar_18() if rede else (lambda u: None, [])
    hoje = hoje_editorial().isoformat()
    lidas, pendentes = 0, [0]

    def refaz(anterior) -> bool:
        return bool(anterior and (refazer & set(anterior.get("regras_18") or []).union(
                                      *((anterior.get(x) or {}).get("regras_18") or [] for x in VARIANTES_18))
                                  or ("promove" in refazer and anterior.get("promove"))))

    def rejulgar(p, antes, origem):
        nonlocal lidas
        chave = chave_18(p)
        anterior = feitas.get(chave)
        precisa_ler = bool(p.get("url")) and fonte_oficial(p["url"])
        refeita = refaz(anterior)
        if anterior and (anterior.get("leu_documento") or not precisa_ler) and not refeita:
            return
        if precisa_ler and (not rede or lidas >= rede):
            pendentes[0] += 1
            return
        lidas += precisa_ler
        novo = julgar_18(p, ler if precisa_ler else (lambda u: None), propostas)
        novo.update(pista_id=p.get("pista_id") or p.get("id"), origem_18=origem, julgado_em=hoje,
                    rejulgada_de=compacto_18(antes) if antes else None)
        novo["url"], novo["municipio_da_pista"], novo["uf_da_pista"] = p.get("url"), p.get("municipio"), p.get("uf")
        if not novo.get("leu_documento"):
            novo.pop("criterios", None)   # sem documento lido, o motivo basta (o arquivo fica pequeno)
        feitas[chave] = vale_a_leitura_18(anterior, herdar_18(novo, antes))
        if rede and fila is not None and novo.get("motivo") in ("noticia_nao_e_documento",
                                                               "noticia_institucional_nao_e_o_plano"):
            from seguir_pistas import buscar_html, documentos_da_pagina_18   # B4: um nível, mesmo domínio
            vistos = {x["url"] for x in fila["pistas"]}
            fila["pistas"] += [candidata_18(c, p, "b4_pagina_oficial")
                               for c in documentos_da_pagina_18(p["url"], buscar_html(p["url"])) if c["url"] not in vistos]

    fila = json.loads(FILA_18.read_text(encoding="utf-8")) if FILA_18.exists() else None
    if "--fila" in argv:
        veiculos = {str(v.get("dominio") or "").lower() for v in json.loads(
            (RAIZ / "data" / "veiculos_imprensa.json").read_text(encoding="utf-8")).get("veiculos", [])}
        em_fila = [p for p in json.loads((RAIZ / "data" / "pistas_imprensa.json").read_text(encoding="utf-8"))
                   .get("pistas", []) if str(p.get("status") or "").startswith(STATUS_EM_FILA)]
        anterior = fila or {}
        fila = dict(triar_fila_18(em_fila, veiculos), _governanca=(
            "Fila paralela do codebook 1.8 (B1, B3, B6): as pistas em fila de data/pistas_imprensa.json que a "
            "entrada 1.8 aceita, por prioridade. Nenhuma página lê este arquivo."), triada_em=hoje)
        # retriar não apaga o que a rodada já fez: as pistas que B2/B4 acharam e as tentativas de B2
        novas_ids = {x["id"] for x in fila["pistas"]}
        fila["pistas"] += [x for x in anterior.get("pistas", [])
                           if str(x.get("origem")).startswith(("b2_", "b4_")) and x["id"] not in novas_ids]
        feitos = {a["id"]: a for a in anterior.get("agregadores", [])}
        fila["agregadores"] = [feitos.get(a["id"], a) for a in fila["agregadores"]]
        print(f"fila 1.8: {fila['totais']}")

    por_id = {p.get("id"): p for p in json.loads(
        (RAIZ / "data" / "pistas_imprensa.json").read_text(encoding="utf-8")).get("pistas", []) if p.get("id")}
    decididas = vigentes(json.loads(REGISTRO.read_text(encoding="utf-8")).get("decisoes") or [])
    # Decisão que saiu do registro (limpeza de 26/10, #1203) sai do rejulgamento: fica só a contagem.
    fora = [k for k, v in feitas.items() if v.get("origem_18") == "decisao" and k not in decididas]
    for k in fora:
        feitas.pop(k)
    doc["fora_do_registro"] = int(doc.get("fora_do_registro") or 0) + len(fora)
    if fila is not None and "--fila" in argv:   # B2: o link de agregador das decisões também se resolve
        from pistas import REDIRECIONADORES, prioridade_18
        ja, feitos = {a["id"] for a in fila["agregadores"]}, {a["id"]: a for a in anterior.get("agregadores", [])}
        for v in decididas.values():
            if any(r in str(v.get("url")) for r in REDIRECIONADORES) and v.get("pista_id") not in ja:
                ja.add(v.get("pista_id"))
                if v.get("pista_id") in feitos:
                    fila["agregadores"].append(feitos[v["pista_id"]])
                    continue
                origem = por_id.get(v.get("pista_id")) or {}
                fila["agregadores"].append({"id": v.get("pista_id"), "url": v.get("url"), "titulo": origem.get("titulo"),
                                            "veiculo_dominio": origem.get("veiculo_dominio"), "municipio": v.get("municipio"),
                                            "uf": v.get("uf"), "ibge": v.get("ibge"), "nivel": origem.get("nivel"),
                                            "prioridade": prioridade_18(origem), "tentativas_b2": 0})
        fila["agregadores"].sort(key=lambda x: x["prioridade"])
        fila["totais"]["agregadores_a_resolver"] = len(fila["agregadores"])
    # B2 depois de reunir os agregadores das decisões (lote 1 de 26/10: rodado antes, achou zero)
    if rede and fila and "--agregadores" in argv:
        from julgar_e_aplicar_descobertas import _resolver_da_rodada
        from seguir_pistas import seguir_agregador_18
        resolver, n = _resolver_da_rodada(), int(argv[argv.index("--agregadores") + 1])
        for a in [a for a in fila.get("agregadores", []) if a.get("tentativas_b2", 0) < 2 and not a.get("resolvido")][:n]:
            a["tentativas_b2"] = a.get("tentativas_b2", 0) + 1
            candidatos, como = seguir_agregador_18(a, resolver)
            a["resolvido"] = como if como != "nao_resolvido" else None
            fila["pistas"] += [candidata_18(c, a, "b2_agregador") for c in candidatos]
        fila["pistas"].sort(key=lambda x: x["prioridade"])

    # O prazo do elo interrompe com SIGINT e espera 60 s (`saude_pipeline.rodar`): o que foi lido até ali se
    # grava abaixo. Lote 4 de 27/10: sem isto, 5 h de leitura saíram sem nada no PR de dado.
    try:
        trabalho = [({"pista_id": v.get("pista_id"), "municipio": v.get("municipio"), "uf": v.get("uf"),
                      "ibge": v.get("ibge"), "url": v.get("url"), "origem": v.get("origem"),
                      "trecho": (por_id.get(v.get("pista_id")) or {}).get("trecho")}, v, "decisao")
                    for v in decididas.values()]
        trabalho += [({"pista_id": p["id"], "trecho": p.get("trecho") or (por_id.get(p["id"]) or {}).get("trecho"),
                       **{k: p.get(k) for k in ("municipio", "uf", "ibge", "url", "origem")}}, None, "fila")
                     for p in (fila or {}).get("pistas", [])]
        trabalho.sort(key=lambda t: ordem_18(refaz(feitas.get(chave_18(t[0]))), feitas.get(chave_18(t[0]))))
        for p, antes, origem in trabalho:
            rejulgar(p, antes, origem)
    except KeyboardInterrupt:
        print("interrompido pelo prazo: gravando o que foi lido", flush=True)

    if fila is not None:
        gravar_em(FILA_18, fila, compacto=True)
    doc["decisoes"] = [herdar_18(v, decididas.get(chave_18(dict(v, municipio=v.get("municipio_da_pista"),
                                                                 uf=v.get("uf_da_pista"))))
                                 if v.get("origem_18") == "decisao" else None) for v in feitas.values()]
    doc["leituras_da_pasta_rs"] = (doc.get("leituras_da_pasta_rs") or []) + registros
    gravar_em(saida, doc, compacto=True)
    faltam = pendentes[0]
    print(f"OK {saida.name}: {len(doc['decisoes'])} chave(s); {lidas} lida(s) nesta rodada; "
          f"{faltam} com documento oficial ainda sem leitura")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    if "--codebook" in sys.argv and sys.argv[sys.argv.index("--codebook") + 1].startswith("1.8"):
        return paralelo_18(sys.argv)

    from coletores_base import gravar_em, hoje_editorial
    from juiz import CODEBOOK_VERSAO
    from julgar_filas import julgar_uma

    doc = json.loads(REGISTRO.read_text(encoding="utf-8"))
    decisoes = doc.get("decisoes") or []
    fila = {p["id"]: p for p in json.loads(
        (RAIZ / "data" / "pistas_imprensa.json").read_text(encoding="utf-8")).get("pistas", [])
        if p.get("id")}

    novos, superadas, sem_prova = [], 0, 0
    viraram = {"promove_continua": 0, "promove_cai": 0, "recusa_continua": 0, "recusa_vira_promove": 0}
    hoje = hoje_editorial().isoformat()

    for v in decisoes:
        if not pendente_de_rejulgamento(v, CODEBOOK_VERSAO):
            continue
        arq = caminho_da_evidencia(v.get("hash_evidencia"))
        if arq is None:
            sem_prova += 1
            continue
        texto = arq.read_text(encoding="utf-8", errors="replace")
        pista = fila.get(v.get("pista_id"), {})
        # `buscar` devolve o texto do disco: rejulgar não toca a rede, e a decisão nova é sobre
        # exatamente a mesma prova que a antiga julgou.
        novo = julgar_uma({"id": v.get("pista_id"), "municipio": v.get("municipio"),
                           "uf": v.get("uf"), "ibge": v.get("ibge"), "url": v.get("url"),
                           "origem": v.get("origem"), "trecho": pista.get("trecho")},
                          lambda _u: texto)
        novo["hash_evidencia"] = v.get("hash_evidencia")
        novo["rejulgada_de"] = {"codebook": v.get("codebook"), "promovia": bool(v.get("promove"))}
        antes, agora = bool(v.get("promove")), bool(novo.get("promove"))
        virou = ("promove_continua" if antes and agora else
                   "promove_cai" if antes else
                   "recusa_vira_promove" if agora else "recusa_continua")
        viraram[virou] += 1
        marcar_superada(v, CODEBOOK_VERSAO, hoje)
        superadas += 1
        novos.append(novo)

    print(f"{superadas} decisão(ões) rejulgada(s) com a prova do disco; {sem_prova} sem evidência "
          f"(recusa de Etapa 0 — voltam à fila pela troca de versão do codebook)")
    for k, n in viraram.items():
        if n:
            print(f"  {k}: {n}")
    for novo in novos:
        if novo.get("rejulgada_de", {}).get("promovia") and not novo.get("promove"):
            print(f"  REVOGADA: {novo.get('municipio')}/{novo.get('uf')} — agora "
                  f"{novo.get('motivo')}")

    if "--escrever" not in sys.argv:
        print("relatório apenas; nada escrito (use --escrever)")
        return 0

    doc["decisoes"] = decisoes + novos
    gravar_em(REGISTRO, doc)   # §229
    print(f"OK data/{REGISTRO.name}: {len(decisoes)} decisão(ões) mantida(s) e {len(novos)} "
          f"acrescentada(s). Nada apagado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
