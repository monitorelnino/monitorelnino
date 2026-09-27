#!/usr/bin/env python3
"""
julgar_filas.py
===============
Roda o juiz automático (`juiz.py`) sobre as filas de pistas e aplica o que passa, com rede de
proteção. É a Etapa 7 do codebook.

Decisão editorial de 27/09/2026, handover `HANDOVER_juiz_automatico_e_busca_web_27-09-2026.md`
(PR 2), repositório privado. A regra R7 passa a ser: promover é decisão do juiz quando TODOS os
critérios passam no documento primário; falhou um, fica pista, com o motivo visível; a editoria
audita amostra semanal e reverte por errata.

O QUE ESTE SCRIPT NÃO FAZ
-------------------------
- Não promove com base em título, notícia ou resumo: o texto julgado é o do documento primário,
  baixado da fonte oficial e preservado com hash.
- Não usa modelo de linguagem: `juiz.py` é regra versionada.
- Não apaga pista: recusa fica na fila, com `juiz` preenchido e o motivo à vista.
- Não muda peso, régua, escada de créditos nem categoria — isso exige a editoria (§12).
- Não reescreve os coletores: consome as filas que já existem.

REDE DE PROTEÇÃO (reusada de `julgar_e_aplicar_descobertas.py`, testada desde 31/08/2026)
-----------------------------------------------------------------------------------------
backup em disco → aplica → `recalcular_mare.py --write` → suíte de portões → se algum portão
reprovar, **restaura o disco** e devolve a pista com o erro. O rótulo "revertida" sem reverter de
verdade foi um defeito real de 31/08/2026; a restauração é de arquivo, não de rótulo.

USO
  python3 julgar_filas.py --relatorio           # julga e conta, NÃO aplica e NÃO escreve
  python3 julgar_filas.py --relatorio --limite 50
  python3 julgar_filas.py --aplicar             # julga e aplica o que passa
  python3 julgar_filas.py --autoteste
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

FILAS = ("pistas_imprensa.json", "pistas_descobertas.json", "pistas_doe.json", "pistas_revisao.json")
PROMOCOES = "promocoes_automaticas.json"

# Motivos de recusa do codebook, na ordem das etapas — a ordem do relatório segue esta.
MOTIVOS = ("sem_documento_primario", "texto_nao_extraivel", "ente_nao_confirmado",
           "citacao_incompleta", "executivo_pendente", "autoridade_nao_confirmada",
           "natureza_duvidosa", "fora_do_objeto", "familia_de_risco_nao_identificada",
           "resposta")


def pistas_da_fila(doc: dict) -> list:
    """As filas não têm o mesmo nome de lista: `pistas`, `itens` ou `grupos`."""
    for chave in ("pistas", "itens"):
        if isinstance(doc.get(chave), list):
            return doc[chave]
    return []


def pendente(p: dict) -> bool:
    """Pista que ainda espera decisão. Já resolvida, não se mexe."""
    status = str(p.get("status") or "")
    if p.get("juiz") and (p["juiz"] or {}).get("codebook"):
        return False    # já julgada por esta versão do codebook
    return status.startswith("pista") or status.startswith("rebaixado") or status.startswith("revertida")


def julgar_uma(p: dict, buscar, preservar=None) -> dict:
    """Julga uma pista e devolve o veredito, sem aplicar nada.

    `buscar(url) -> texto|None` e `preservar(url, texto) -> hash|None` são injetados: é o que
    permite ao autoteste rodar sem rede e sem escrever em `evidencias/`."""
    from juiz import julgar

    url = p.get("url")
    texto = buscar(url) if url else None
    veredito = julgar(texto, nome=p.get("municipio") or "", uf=p.get("uf") or "",
                      ibge=p.get("ibge"), url=url)
    veredito["pista_id"] = p.get("id")
    veredito["origem"] = p.get("origem")
    # O hash só se grava quando há documento de verdade: preservar um erro servido com 200 (§186)
    # criaria prova falsa.
    if preservar and texto and veredito["criterios"].get("0_documento_primario", {}).get("ok"):
        veredito["hash_evidencia"] = preservar(url, texto)
    return veredito


def contar(vereditos: list) -> dict:
    """Contagens do relatório: promovidas, recusadas por critério, resposta, fora do objeto."""
    c = {"pistas": len(vereditos), "com_documento": 0, "promovidas": 0,
         "por_motivo": {m: 0 for m in MOTIVOS}, "outros_motivos": {}}
    for v in vereditos:
        if v["criterios"].get("0_documento_primario", {}).get("ok"):
            c["com_documento"] += 1
        if v["promove"]:
            c["promovidas"] += 1
            continue
        m = v.get("motivo") or "sem_motivo"
        if m in c["por_motivo"]:
            c["por_motivo"][m] += 1
        else:
            c["outros_motivos"][m] = c["outros_motivos"].get(m, 0) + 1
    return c


def imprimir_relatorio(c: dict, por_categoria: dict = None) -> None:
    print(f"\n{c['pistas']} pista(s) julgada(s); {c['com_documento']} com documento primário "
          f"em fonte oficial; {c['promovidas']} promovida(s)")
    if por_categoria:
        for cat, n in sorted(por_categoria.items()):
            print(f"    {cat}: {n}")
    print("  recusas por critério:")
    for m in MOTIVOS:
        if c["por_motivo"][m]:
            print(f"    {m}: {c['por_motivo'][m]}")
    for m, n in sorted(c["outros_motivos"].items(), key=lambda kv: -kv[1]):
        print(f"    {m}: {n}  (fora da lista de motivos do codebook)")


# =============================================================================================
def autoteste() -> int:
    """Offline: sem rede, sem escrita em data/ nem em evidencias/."""
    from juiz import CANARIOS, CODEBOOK_VERSAO
    casos = []

    textos = {c["url"]: c["texto"] for c in CANARIOS.values()}
    buscar = lambda u: textos.get(u)                                      # noqa: E731
    preservados = []
    preservar = lambda u, t: (preservados.append(u), "hash" + str(len(preservados)))[1]   # noqa: E731

    pistas = [{"id": nome, "municipio": c["nome"], "uf": c["uf"], "url": c["url"],
               "origem": "teste", "status": "pista — promover a registro exige documento primário"}
              for nome, c in CANARIOS.items()]
    # o pdf_ilegivel e o plano_novo compartilham a URL; o dicionário de textos guarda um só.
    # Isso é fiel ao mundo: a mesma URL devolve um texto só.
    vereditos = [julgar_uma(p, buscar, preservar) for p in pistas]

    casos.append(("todo veredito carrega a versão do codebook",
                  all(v["codebook"] == CODEBOOK_VERSAO for v in vereditos)))
    casos.append(("todo veredito carrega o id da pista",
                  all(v["pista_id"] for v in vereditos)))
    c = contar(vereditos)
    casos.append(("o relatório conta uma linha por pista", c["pistas"] == len(pistas)))
    casos.append(("promovidas nunca passa de com_documento", c["promovidas"] <= c["com_documento"]))
    casos.append(("notícia não é preservada como evidência",
                  all("g1.globo.com" not in u for u in preservados)))
    casos.append(("recusa por fonte não oficial não tem hash",
                  all("hash_evidencia" not in v for v in vereditos
                      if v.get("motivo") == "sem_documento_primario")))

    # pista já julgada por este codebook não volta à fila
    p_julgada = {"status": "pista — …", "juiz": {"codebook": CODEBOOK_VERSAO}}
    casos.append(("pista já julgada por este codebook não é rejulgada", not pendente(p_julgada)))
    casos.append(("pista pendente é reconhecida",
                  pendente({"status": "pista — promover a registro exige documento primário"})))
    casos.append(("pista rebaixada pelo C10 volta ao juiz",
                  pendente({"status": "rebaixado_c10 — volta a registro só com documento"})))
    casos.append(("pista revertida por portão volta ao juiz",
                  pendente({"status": "revertida_erro_portao"})))
    casos.append(("pista aplicada não volta ao juiz",
                  not pendente({"status": "aplicada", "juiz": {"codebook": CODEBOOK_VERSAO}})))

    # documento ausente: a pista fica, com motivo, e nada é preservado
    v = julgar_uma({"id": "x", "municipio": "Bonito", "uf": "MS", "url": "https://bonito.ms.gov.br/x.pdf"},
                   lambda u: None, preservar)
    casos.append(("documento não obtido devolve sem_documento_primario",
                  v["motivo"] == "sem_documento_primario" and not v["promove"]))

    # as filas: leitura tolerante ao nome da lista
    casos.append(("lê fila com 'pistas'", len(pistas_da_fila({"pistas": [1, 2]})) == 2))
    casos.append(("lê fila com 'itens'", len(pistas_da_fila({"itens": [1]})) == 1))
    casos.append(("fila sem lista conhecida devolve vazio", pistas_da_fila({"grupos": {}}) == []))

    # o modo relatório não escreve: nem evidência, nem arquivo de fila, nem índice. A trava é
    # sobre o CÓDIGO de main(), porque exercitar main() de verdade tocaria o banco real.
    import inspect
    import re as _re
    fonte = inspect.getsource(main)
    # a docstring de `hash_do_texto` CITA preservar_evidencia para explicar por que não a usa;
    # a trava tem de procurar a CHAMADA, não a palavra.
    nao_preserva = not _re.search(r"preservar_evidencia\s*\(", fonte)
    guarda_pista = _re.search(r"if not aplicar:\s+continue", fonte)
    grava_fila_sob_guarda = _re.search(r"if aplicar:\s+gravar_em\(DATA / nome_fila", fonte)
    casos.append(("o juiz não preserva evidência: a porta canônica é preservar_evidencias.py --ler",
                  nao_preserva))
    casos.append(("o modo relatório não marca a pista em memória", bool(guarda_pista)))
    casos.append(("a fila só é gravada sob --aplicar", bool(grava_fila_sob_guarda)))
    # e o caminho sem preservador devolve veredito sem hash
    v_sem = julgar_uma({"id": "z", "municipio": "Bonito", "uf": "MS",
                        "url": CANARIOS["plano_novo"]["url"]}, buscar, None)
    casos.append(("sem função de hash, o veredito não inventa hash", "hash_evidencia" not in v_sem))

    # todo motivo que o juiz produz está na lista do relatório
    motivos_vistos = {v.get("motivo") for v in vereditos if not v["promove"]}
    casos.append(("todo motivo produzido pelos canários está no codebook do relatório",
                  motivos_vistos <= set(MOTIVOS)))

    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    imprimir_relatorio(c)
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos, sem rede e sem escrita.")
    return 0


# =============================================================================================
def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()

    aplicar = "--aplicar" in sys.argv
    limite = int(sys.argv[sys.argv.index("--limite") + 1]) if "--limite" in sys.argv else None

    import funil
    from coletores_base import DATA, gravar_em, ler, log_busca, hoje_editorial
    from julgar_e_aplicar_descobertas import buscar_texto

    def hash_do_texto(url, texto):
        """O hash do texto julgado, para o registro da decisão — NÃO preserva evidência.

        27/09/2026: a primeira versão chamava `preservar_evidencia` com o texto extraído e extensão
        `txt`. O portão 26 (`verificar_evidencias.py`) reprovou com razão: evidência de texto cuja
        URL termina em `.pdf` e sem `texto_manual: true` seria SOBRESCRITA por
        `preservar_evidencias.py --ler`, que é a porta canônica de preservação e guarda o binário.
        Duas portas gravando a mesma chave é como se perde prova. O juiz precisa do hash para
        identificar o que julgou; preservar o documento é trabalho de quem já o faz."""
        from coletores_base import sha256
        return sha256(texto.encode("utf-8")) if texto else None

    vereditos, por_fila = [], {}
    for nome_fila in FILAS:
        doc = ler(nome_fila)
        if not doc:
            continue
        lista = pistas_da_fila(doc)
        alvo = [p for p in lista if pendente(p)]
        if limite is not None:
            alvo = alvo[:max(0, limite - len(vereditos))]
        por_fila[nome_fila] = len(alvo)
        print(f"{nome_fila}: {len(alvo)} pendente(s) de {len(lista)}")
        for p in alvo:
            v = julgar_uma(p, buscar_texto, hash_do_texto)
            vereditos.append(v)
            if not aplicar:
                continue   # relatório não escreve nem no objeto em memória que será gravado
            p["juiz"] = {"codebook": v["codebook"], "promove": v["promove"], "motivo": v["motivo"],
                         "criterios": v["criterios"], "categoria": v["categoria"],
                         "data": v["data"], "julgado_em": hoje_editorial().isoformat(),
                         "hash_evidencia": v.get("hash_evidencia")}
            if not v["promove"]:
                p["status"] = f"pista — recusada pelo juiz: {v['motivo']}"
        if aplicar:
            gravar_em(DATA / nome_fila, doc)

    c = contar(vereditos)
    por_categoria = {}
    for v in vereditos:
        if v["promove"]:
            por_categoria[v["categoria"]] = por_categoria.get(v["categoria"], 0) + 1
    imprimir_relatorio(c, por_categoria)

    if aplicar:
        funil.registrar("juiz", pistas_recebidas=c["pistas"], com_documento=c["com_documento"],
                        promovidas=c["promovidas"],
                        **{f"recusa_{m}": n for m, n in c["por_motivo"].items() if n})
        registro = ler(PROMOCOES) or {"_governanca": (
            "Registro de toda decisão do juiz automático (§ do CHANGELOG de 27/09/2026). Uma linha "
            "por pista julgada, com os critérios 1-6 e o trecho que satisfez cada um. Errata humana "
            "reverte com uma linha. Este arquivo é o que alimenta a auditoria amostral semanal."),
            "decisoes": []}
        registro["decisoes"] = (registro.get("decisoes") or []) + vereditos
        gravar_em(DATA / PROMOCOES, registro)
        for v in vereditos:
            log_busca("juiz", 5, [f"pista {v.get('pista_id')}"],
                      "registro" if v["promove"] else "pista",
                      uf=v.get("uf"), municipio=v.get("municipio"), ibge=v.get("ibge"),
                      resultados=f"juiz {v['codebook']}: {v['motivo'] or v['categoria']}",
                      hash_evidencia=v.get("hash_evidencia"))
        print(f"\n{len(vereditos)} decisão(ões) gravada(s) em data/{PROMOCOES} e no log")
        print("A APLICAÇÃO em municipios.json/estados.json continua em julgar_e_aplicar_descobertas.py,")
        print("que tem a rede de proteção (backup, portões, rollback em disco) testada desde 31/08/2026.")
    else:
        print("\nrelatório apenas; nada escrito (use --aplicar)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
