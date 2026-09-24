#!/usr/bin/env python3
"""
gerar_card_municipios.py — o card de cada município (§155, 22/09/2026)
======================================================================
Derivado compacto, data/municipios_card.json, lido pela consulta "seu município" em
prefeituras.html. Um objeto por código IBGE, SÓ para municípios com algo a dizer
(prioritário, ou registro no MARÉ, ou pista de imprensa) — os demais são "nada
localizado, não prioritário" por ausência, sem inflar o arquivo.

Campos: nome, uf, prioritario (aproximação populacional do Cadastro Nacional — mesmo
proxy de gerar_prioritarios.py), categoria no MARÉ (municipios.json; ausente = nao_localizado),
documento/url/data quando há registro, e `imprensa`: até 3 pistas pendentes de nível A/B
(título, url, data, veículo = host), mais novas primeiro.

Decisão editorial de 22/09/2026: pista de imprensa NÃO pontua — nem "em elaboração". Ela
entra no card como link, rotulada como pista sem verificação, para que o leitor peça o
documento ao gestor público (o card diz como). Quando o documento oficial aparece e o juiz
aplica, a categoria sobe e a pista fica como proveniência.
"""
import json, os, sys
from datetime import date, datetime, timezone


def data_de_geracao() -> str:
    """Data do carimbo do derivado, do RELÓGIO FIXADO — nunca do relógio da parede.

    DEFEITO REAL (§193, 24/09/2026). `scripts/verificar_derivados.sh` fixa SOURCE_DATE_EPOCH no
    corte da edição justamente para a cadeia ser reproduzível, e este arquivo escapava: usava
    `date.today()`. Enquanto a data local e a do runner coincidem, ninguém vê. Quando a data vira
    em UTC — o CI de 24/09/2026 rodou 01:21 UTC, com o Brasil ainda em 23/09 —, o runner regenera
    com o dia seguinte, o portão 12 acusa derivado obsoleto e a reprovação não tem nada a ver com
    o ramo que a recebeu. A `main` reprova sozinha pelo mesmo motivo, todo dia, na virada.
    """
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        return datetime.fromtimestamp(int(epoch), tz=timezone.utc).date().isoformat()
    return date.today().isoformat()
from urllib.parse import urlparse
from coletores_base import ler, gravar, rodar_autoteste
from monitorar_imprensa_regional import parece_fonte_oficial

NIVEIS_NO_CARD = ("A", "B")
MAX_IMPRENSA = 3


def _host(u):
    try:
        return (urlparse(u or "").hostname or "").lower().removeprefix("www.")
    except Exception:  # noqa: BLE001
        return ""


def _data_key(d):
    # "dd/mm/aaaa" → ordenável; ausente vai pro fim
    try:
        dd, mm, aa = (d or "").split("/"); return f"{aa}{mm}{dd}"
    except ValueError:
        return "0"


def montar(referencia, prioritarios, municipios, pistas):
    """Pura. Devolve dict codigo_ibge(str) → card."""
    por_nome = {(m["nome"], m["uf"]): int(m["codigo_ibge"]) for m in referencia}
    prior = {int(m["codigo_ibge"]) for m in prioritarios}
    cards = {}
    for m in referencia:
        cod = int(m["codigo_ibge"])
        if cod in prior:
            cards[cod] = {"nome": m["nome"], "uf": m["uf"], "prioritario": True}
    for r in municipios:
        cod = por_nome.get((r.get("nome"), r.get("uf")))
        if cod is None:
            continue
        c = cards.setdefault(cod, {"nome": r["nome"], "uf": r["uf"], "prioritario": cod in prior})
        c.update({"categoria": r.get("categoria"), "documento": (r.get("documento") or "")[:220],
                  "url": r.get("url"), "data": r.get("data"), "fonte": (r.get("fonte") or "")[:120]})
    for p in pistas:
        st = p.get("status") or ""
        if not st.startswith("pista") or p.get("nivel_confianca") not in NIVEIS_NO_CARD:
            continue
        # §159: documento oficial candidato (cascata ou host oficial) não é "publicação na imprensa" — não entra aqui
        if (p.get("origem") or "").startswith("seguimento") or parece_fonte_oficial(p.get("url") or ""):
            continue
        try:
            cod = int(p.get("ibge") or 0)
        except (TypeError, ValueError):
            continue
        if not cod:
            continue
        c = cards.setdefault(cod, {"nome": p.get("municipio"), "uf": p.get("uf"), "prioritario": cod in prior})
        c.setdefault("imprensa", []).append({"titulo": (p.get("titulo") or p.get("trecho") or "")[:140].strip(),
                                             "url": p.get("url"), "data": p.get("data"), "veiculo": _host(p.get("url")),
                                             "nivel": p.get("nivel_confianca")})
    for c in cards.values():
        if "imprensa" in c:
            c["imprensa"].sort(key=lambda x: _data_key(x.get("data")), reverse=True)
            c["imprensa"] = c["imprensa"][:MAX_IMPRENSA]
        c.setdefault("categoria", "nao_localizado")
    return {str(k): v for k, v in sorted(cards.items())}


def gerar():
    ref = ler("municipios_ibge_referencia.json") or []
    prior = (ler("municipios_prioritarios.json") or {}).get("municipios", [])
    mun = ler("municipios.json") or []
    pis = (ler("pistas_imprensa.json") or {}).get("pistas", [])
    cards = montar(ref, prior, mun, pis)
    out = {"_governanca": ("Card por município (§155). DERIVADO — regenerado a cada rodada por gerar_card_municipios.py. "
                           "`prioritario` = aproximação populacional do Cadastro Nacional (não a lista oficial). "
                           "`imprensa` = pistas pendentes de nível A/B: NÃO pontuam no MARÉ; entram como link para que o "
                           "leitor peça o documento ao gestor. Só municípios com algo a dizer; ausência = nada localizado."),
           "gerado_em": data_de_geracao(), "total": len(cards),
           "com_registro": sum(1 for c in cards.values() if c.get("categoria") != "nao_localizado"),
           "com_imprensa": sum(1 for c in cards.values() if c.get("imprensa")),
           "prioritarios": sum(1 for c in cards.values() if c.get("prioritario")),
           "municipios": cards}
    gravar("municipios_card.json", out)
    return out


def autoteste():
    ref = [{"nome": "Bagé", "uf": "RS", "codigo_ibge": 4301602}, {"nome": "Ipixuna", "uf": "AM", "codigo_ibge": 1301803},
           {"nome": "Marília", "uf": "SP", "codigo_ibge": 3529005}, {"nome": "Sem Nada", "uf": "SP", "codigo_ibge": 3500001}]
    prior = [{"codigo_ibge": 1301803}]
    mun = [{"nome": "Bagé", "uf": "RS", "categoria": "plano", "documento": "Decreto x", "url": "https://bage.rs.gov.br/d", "data": "10/07/2026"}]
    pis = [{"ibge": "3529005", "municipio": "Marília", "uf": "SP", "status": "pista — promover…", "nivel_confianca": "B", "titulo": "Marília prepara plano", "url": "https://www.marilianoticia.com.br/a", "data": "15/09/2026"},
           {"ibge": "3529005", "municipio": "Marília", "uf": "SP", "status": "pista — promover…", "nivel_confianca": "C", "titulo": "ruído", "url": "https://x", "data": "16/09/2026"},
           {"ibge": "3529005", "municipio": "Marília", "uf": "SP", "status": "rejeitada_humana", "nivel_confianca": "A", "titulo": "rejeitada", "url": "https://y", "data": "17/09/2026"},
           {"ibge": "4301602", "municipio": "Bagé", "uf": "RS", "status": "pista — promover…", "nivel_confianca": "A", "titulo": "Bagé lança plano", "url": "https://g1.globo.com/b", "data": "01/09/2026"}]
    c = montar(ref, prior, mun, pis)

    def t_prioritario_sozinho_entra(): return c["1301803"]["prioritario"] is True and c["1301803"]["categoria"] == "nao_localizado"
    def t_sem_nada_nao_entra(): return "3500001" not in c
    def t_registro_e_tag(): return c["4301602"]["categoria"] == "plano" and c["4301602"]["prioritario"] is False and c["4301602"]["url"]
    def t_imprensa_so_A_B_pendentes(): return [x["titulo"] for x in c["3529005"]["imprensa"]] == ["Marília prepara plano"] and c["3529005"]["categoria"] == "nao_localizado"
    def t_imprensa_nao_vira_categoria(): return c["3529005"].get("categoria") == "nao_localizado"   # peso zero, por construção
    def t_veiculo_sem_www(): return c["3529005"]["imprensa"][0]["veiculo"] == "marilianoticia.com.br"
    def t_registro_mantem_imprensa_como_proveniencia(): return c["4301602"]["imprensa"][0]["veiculo"] == "g1.globo.com"
    def t_carimbo_segue_o_relogio_fixado():
        """§193: o carimbo do derivado não pode depender do relógio da parede. Com SOURCE_DATE_EPOCH
        posto, a data sai dele; sem ele, cai no dia de hoje. Foi a falta disso que fez o CI reprovar
        na virada da data em UTC, num ramo que não tinha nada a ver com o assunto."""
        anterior = os.environ.get("SOURCE_DATE_EPOCH")
        try:
            ep = lambda a, m, d: str(int(datetime(a, m, d, tzinfo=timezone.utc).timestamp()))
            os.environ["SOURCE_DATE_EPOCH"] = ep(2026, 9, 10)   # o corte desta edição
            fixo = data_de_geracao()
            os.environ["SOURCE_DATE_EPOCH"] = ep(2026, 9, 21)
            outro = data_de_geracao()
            os.environ.pop("SOURCE_DATE_EPOCH")
            livre = data_de_geracao()
        finally:
            if anterior is None: os.environ.pop("SOURCE_DATE_EPOCH", None)
            else: os.environ["SOURCE_DATE_EPOCH"] = anterior
        return fixo == "2026-09-10" and outro == "2026-09-21" and livre == date.today().isoformat()

    return rodar_autoteste({
        "§193 carimbo do derivado segue o relógio fixado, não o da parede": t_carimbo_segue_o_relogio_fixado,
        "prioritário sem registro entra, categoria nao_localizado": t_prioritario_sozinho_entra,
        "município sem nada não entra (ausência = nada localizado)": t_sem_nada_nao_entra,
        "registro no MARÉ + tag prioritário false": t_registro_e_tag,
        "imprensa: só pistas pendentes de nível A/B (C e rejeitadas ficam fora)": t_imprensa_so_A_B_pendentes,
        "imprensa nunca vira categoria (peso zero por construção)": t_imprensa_nao_vira_categoria,
        "veículo = host sem www": t_veiculo_sem_www,
        "município com registro mantém a pista como proveniência": t_registro_mantem_imprensa_como_proveniencia,
    })


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        sys.exit(autoteste())
    o = gerar()
    print(f"✓ data/municipios_card.json: {o['total']} municípios · {o['com_registro']} com registro · {o['com_imprensa']} com pista de imprensa · {o['prioritarios']} prioritários")
