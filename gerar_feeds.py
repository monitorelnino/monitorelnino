#!/usr/bin/env python3
"""
gerar_feeds.py — histórico de mudanças e feeds Atom do Monitor El Niño Brasil.

Sugestão aceita por Patricia em 31/08/2026: quem acompanha um estado (jornalista,
Defesa Civil, controle externo) assina `feeds/UF.xml` e recebe "SC: novo
instrumento localizado" sem precisar visitar o site.

Como funciona:
  1. Fotografa o estado atual do banco (status/doc por UF, categoria/documento por
     município, eventos de resposta, nota do índice) em data/snapshot_feed.json.
  2. Na rodada seguinte, compara com a fotografia anterior e grava as diferenças
     como EVENTOS em data/historico_mudancas.json (append-only, deduplicado).
  3. Renderiza feeds/brasil.xml (tudo) e feeds/UF.xml (por estado), Atom 1.0.
Primeira execução: cria a fotografia e um evento de abertura por UF.

Garantias: nunca escreve no banco (estados/municipios/indice); determinístico
para a mesma entrada e a mesma data; a data do evento é a da execução (--data
para testes). Linguagem probatória nos títulos: "localizado", nunca "criado".
Uso: python3 gerar_feeds.py [--data DD/MM/AAAA] [--self-test]
"""
import argparse
import datetime
import hashlib
import json
import sys
import xml.sax.saxutils as sx
from pathlib import Path

RAIZ = Path(__file__).parent
DATA = RAIZ / "data"
FEEDS = RAIZ / "feeds"
SITE = "https://monitorelnino.com.br"
SNAPSHOT = DATA / "snapshot_feed.json"
HISTORICO = DATA / "historico_mudancas.json"
CAT_HUMANO = {"plano": "plano preventivo", "plano_antigo": "plano de edição anterior", "plano_elaboracao": "plano em elaboração",
              "decreto": "decreto de emergência", "coberto_estadual": "cobertura pelo plano estadual",
              "nao_el_nino": "ato que não trata do El Niño", "nao_localizado": "verificação completa sem ato localizado",
              "nao_verificado": "ainda não verificado com a bateria completa de fontes"}
STATUS_HUMANO = {"NOVO": "plano estadual novo, específico para o El Niño", "READ": "plano recorrente readaptado para o ciclo",
                 "VIG": "instrumento recorrente, sem menção nominal ao El Niño", "ELAB": "plano estadual em elaboração",
                 "LAC": "sem plano estadual nominal localizado"}


def fotografar(estados, municipios, atos, indice, vresumo=None, saude_uf=None, evidencias=None):
    """Reduz o banco ao que o feed acompanha (apenas campos cujas mudanças viram evento)."""
    return {
        "estados": {u["uf"]: {"status": u.get("status"), "doc": u.get("doc", ""), "data": u.get("data", "")} for u in estados["ufs"]},
        "municipios": {f"{m['nome']}|{m['uf']}": {"categoria": m.get("categoria"), "documento": m.get("documento", ""), "data": m.get("data", "")} for m in municipios},
        "atos_resposta": sorted({f"{e['nome']}|{e['uf']}|{e.get('data', '')}" for e in atos.get("eventos", [])}),
        "indice": {uf: round(v["total"], 1) for uf, v in indice.items()},
        "nomes": {u["uf"]: u["nome"] for u in estados["ufs"]},
        # v2.3 (§7.2): tipos novos de evento
        "niveis": dict((vresumo or {}).get("niveis_acima_do_padrao", {})),
        "reconhecimentos": sorted({f"{e['nome']}|{e['uf']}|{e.get('data', '')}" for e in atos.get("eventos", []) if e.get("causa") == "reconhecimento federal"}),
        "saude": {uf: {"status": v.get("status"), "doc": v.get("doc") or ""} for uf, v in ((saude_uf or {}).get("uf") or {}).items()},
        "docs_alterados": sorted(f"{h}|{it.get('alterado_em')}|{it.get('municipio','')}" for h, it in ((evidencias or {}).get("itens") or {}).items() if it.get("alterado_em")),
    }


def _evento(data, uf, tipo, chave, titulo, resumo, nomes):
    """Monta um evento com id estável (hash do que mudou), para deduplicação."""
    h = hashlib.sha256(f"{data}|{tipo}|{chave}|{titulo}".encode()).hexdigest()[:16]
    return {"id": h, "data": data, "uf": uf, "estado": nomes.get(uf, uf), "tipo": tipo, "titulo": titulo, "resumo": resumo,
            "url": f"{SITE}/#{uf}"}


_REF = json.load(open(DATA / "municipios_ibge_referencia.json", encoding="utf-8")) if (DATA / "municipios_ibge_referencia.json").exists() else []
UF_POR_IBGE = {str(r["codigo_ibge"]).zfill(7): r["uf"] for r in _REF}

def diferencas(antes, agora, data):
    """Compara duas fotografias e devolve a lista de eventos (vazia se nada mudou)."""
    ev = []
    nomes = agora["nomes"]
    if antes is None:
        for uf, e in sorted(agora["estados"].items()):
            n_mun = sum(1 for k in agora["municipios"] if k.endswith("|" + uf))
            ev.append(_evento(data, uf, "abertura", uf, f"{nomes[uf]}: feed iniciado",
                              f"Estado: {STATUS_HUMANO.get(e['status'], e['status'])}. {n_mun} registro(s) municipal(is) verificado(s). MARÉ {str(agora['indice'].get(uf, '')).replace('.', ',')}/100.", nomes))
        return ev
    for uf, e in sorted(agora["estados"].items()):
        a = antes["estados"].get(uf, {})
        if a.get("status") != e["status"] or a.get("doc") != e["doc"]:
            ev.append(_evento(data, uf, "estado", uf, f"{nomes[uf]}: instrumento estadual — {STATUS_HUMANO.get(e['status'], e['status'])}",
                              f"Antes: {STATUS_HUMANO.get(a.get('status'), a.get('status') or 'sem registro')}. Documento localizado: {e['doc'] or '—'}{(' (' + e['data'] + ')') if e['data'] else ''}.", nomes))
    for chave, m in sorted(agora["municipios"].items()):
        nome, uf = chave.split("|")
        a = antes["municipios"].get(chave)
        if a is None:
            ev.append(_evento(data, uf, "municipio", chave, f"{nome} ({uf}): {CAT_HUMANO.get(m['categoria'], m['categoria'])} localizado",
                              f"{m['documento'] or '—'}{(' (' + m['data'] + ')') if m['data'] else ''}.", nomes))
        elif a.get("categoria") != m["categoria"] or a.get("documento") != m["documento"]:
            ev.append(_evento(data, uf, "municipio", chave, f"{nome} ({uf}): registro atualizado — {CAT_HUMANO.get(m['categoria'], m['categoria'])}",
                              (f"Antes: registrado como 'nada localizado' sem bateria municipal completa logada. Agora: {CAT_HUMANO['nao_verificado']} — reclassificação por regra de prova (§2.1, 02/09/2026), com errata pública; efeito nulo na nota."
                               if (m['categoria'] == 'nao_verificado' and a.get('categoria') == 'nao_localizado') else
                               f"Antes: {CAT_HUMANO.get(a.get('categoria'), a.get('categoria'))}, apoiado apenas em imprensa. Agora: {CAT_HUMANO['nao_verificado']} — rebaixado a pista pela regra de prova (C10, 02/09/2026), com errata pública; volta a registro com documento primário (ato com número e data em fonte oficial)."
                               if m['categoria'] == 'nao_verificado' else
                               f"Antes: {CAT_HUMANO.get(a.get('categoria'), a.get('categoria'))}. Agora: {m['documento'] or '—'}{(' (' + m['data'] + ')') if m['data'] else ''}."), nomes))
    NIV_H = {"nacional": "verificado em fontes nacionais", "estadual": "verificado em fontes nacionais e estaduais", "municipal_completo": "verificação completa"}
    ORD = {"nao_verificado": 0, "nacional": 1, "estadual": 2, "municipal_completo": 3}
    # 03/09/2026: agregado por UF e nível (um evento por município inundava o feed: 5.571 de uma vez)
    subiram = {}
    for cod, niv in sorted(agora.get("niveis", {}).items()):
        if ORD.get(niv, 0) > ORD.get(antes.get("niveis", {}).get(cod, "nao_verificado"), 0):
            uf = UF_POR_IBGE.get(str(cod).zfill(7), "BR"); subiram.setdefault((uf, niv), 0); subiram[(uf, niv)] += 1
    for (uf, niv), n in sorted(subiram.items()):
        ev.append(_evento(data, uf, "verificacao_ampliada", f"{uf}|{niv}|{data}", f"{nomes.get(uf, uf)}: {n} município(s) passaram a '{NIV_H.get(niv, niv)}'",
                          "Fonte consultada e registrada no livro de fontes; nenhuma nota muda por verificação.", nomes))
    for chave in agora.get("reconhecimentos", []):
        if chave not in set(antes.get("reconhecimentos", [])):
            nome, uf, d = chave.split("|")
            ev.append(_evento(data, uf, "decreto_reconhecido", chave, f"{nome} ({uf}): reconhecimento federal de emergência ({d or 'data não localizada'})",
                              "Portaria SEDEC/MIDR no DOU. Ato de resposta: registro à parte, peso zero no índice.", nomes))
    for chave in agora.get("docs_alterados", []):
        if chave not in set(antes.get("docs_alterados", [])):
            h, dt, mun = chave.split("|"); uf = mun[-2:] if "/" in mun else "BR"
            ev.append(_evento(data, uf, "documento_alterado", chave, f"{mun or 'documento'}: documento-fonte alterado em {dt}",
                              f"O documento citado mudou de conteúdo (hash {h[:12]}…). Categoria mantida até julgamento humano (§3.8-bis).", nomes))
    for uf, v in sorted(agora.get("saude", {}).items()):
        a = antes.get("saude", {}).get(uf, {})
        if a and (a.get("status") != v["status"] or a.get("doc") != v["doc"]):
            ev.append(_evento(data, uf, "instrumento_saude", uf, f"{nomes.get(uf, uf)}: instrumento estadual de saúde — {v['status']}",
                              f"Antes: {a.get('status')}. Documento: {v['doc'] or '—'}. Camada de transparência, peso zero.", nomes))
    for chave in agora["atos_resposta"]:
        if chave not in set(antes.get("atos_resposta", [])):
            nome, uf, d = chave.split("|")
            ev.append(_evento(data, uf, "resposta", chave, f"{nome} ({uf}): decreto de emergência registrado ({d or 'data não localizada'})",
                              "Ato de resposta a dano já ocorrido — registro de transparência; não pontua no índice.", nomes))
    for uf, v in sorted(agora["indice"].items()):
        a = antes["indice"].get(uf)
        if a is not None and abs(a - v) >= 0.1:
            ev.append(_evento(data, uf, "indice", uf, f"{nomes[uf]}: MARÉ {str(a).replace('.', ',')} → {str(v).replace('.', ',')}",
                              "Mudança na nota do índice decorrente das atualizações acima.", nomes))
    return ev


def _rfc3339(d):
    """DD/MM/AAAA → 2026-08-31T09:00:00-03:00 (horário de Brasília)."""
    dd, mm, aa = d.split("/")
    return f"{aa}-{mm}-{dd}T09:00:00-03:00"


def atom(titulo, arquivo, eventos, atualizado):
    """Documento Atom 1.0 com os eventos (mais recentes primeiro)."""
    e = sx.escape
    itens = "\n".join(f"""  <entry>
    <id>tag:monitorelnino.com.br,2026:evento:{ev['id']}</id>
    <title>{e(ev['titulo'])}</title>
    <link href="{e(ev['url'])}"/>
    <updated>{_rfc3339(ev['data'])}</updated>
    <category term="{e(ev['tipo'])}"/>
    <summary>{e(ev['resumo'])}</summary>
  </entry>""" for ev in eventos)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>{e(titulo)}</title>
  <subtitle>Preparação demonstrável publicamente para o El Niño 2026/2027 — o que foi localizado em fontes oficiais, quando.</subtitle>
  <link href="{SITE}/"/>
  <link rel="self" href="{SITE}/feeds/{arquivo}"/>
  <id>tag:monitorelnino.com.br,2026:feed:{arquivo}</id>
  <updated>{_rfc3339(atualizado)}</updated>
  <author><name>Monitor El Niño Brasil · Futura Evidence Lab</name></author>
{itens}
</feed>
"""


def renderizar(historico, nomes, data):
    """Escreve feeds/brasil.xml, feeds/UF.xml (27) e feeds/index.json."""
    FEEDS.mkdir(exist_ok=True)
    eventos = sorted(historico["eventos"], key=lambda x: (x["data"].split("/")[::-1], x["titulo"]), reverse=True)
    (FEEDS / "brasil.xml").write_text(atom("Monitor El Niño Brasil — atualizações", "brasil.xml", eventos[:100], eventos[0]["data"] if eventos else data), encoding="utf-8")
    for uf, nome in sorted(nomes.items()):
        ev = [x for x in eventos if x["uf"] == uf][:50]
        (FEEDS / f"{uf}.xml").write_text(atom(f"Monitor El Niño Brasil — {nome}", f"{uf}.xml", ev, ev[0]["data"] if ev else data), encoding="utf-8")
    # v2.2.4 (§7.7): feed próprio de saúde — eventos dos tipos novos (instrumento_saude,
    # verificacao_ampliada, decreto_reconhecido). Nasce válido mesmo sem eventos.
    ev_saude = [x for x in eventos if x.get("tipo") in ("instrumento_saude", "verificacao_ampliada", "decreto_reconhecido")][:100]
    (FEEDS / "saude.xml").write_text(atom("Monitor El Niño Brasil — saúde e El Niño (registro de transparência, peso zero)", "saude.xml",
                                          ev_saude, ev_saude[0]["data"] if ev_saude else data), encoding="utf-8")
    (FEEDS / "index.json").write_text(json.dumps({"brasil": f"{SITE}/feeds/brasil.xml", "saude": f"{SITE}/feeds/saude.xml",
                                                  "ufs": {uf: f"{SITE}/feeds/{uf}.xml" for uf in sorted(nomes)}}, ensure_ascii=False, indent=1), encoding="utf-8")


def executar(data, dados=None, gravar=True):
    """Ciclo completo. `dados` injetável para o self-test; devolve os eventos novos."""
    if dados is None:
        dados = {k: json.load(open(DATA / f"{k}.json", encoding="utf-8")) for k in ("estados", "municipios", "atos_resposta", "indice")}
        for k in ("verificacao_resumo", "saude_uf", "evidencias"):
            if (DATA / f"{k}.json").exists(): dados[k] = json.load(open(DATA / f"{k}.json", encoding="utf-8"))
    agora = fotografar(dados["estados"], dados["municipios"], dados["atos_resposta"], dados["indice"], dados.get("verificacao_resumo"), dados.get("saude_uf"), dados.get("evidencias"))
    antes = json.load(open(SNAPSHOT, encoding="utf-8")) if (gravar and SNAPSHOT.exists()) else dados.get("_antes")
    historico = json.load(open(HISTORICO, encoding="utf-8")) if (gravar and HISTORICO.exists()) else dados.get("_historico") or {"_governanca": "Histórico append-only de mudanças detectadas pelo pipeline (feeds Atom). Nunca é lido pelo cálculo do índice.", "eventos": []}
    novos = diferencas(antes, agora, data)
    vistos = {x["id"] for x in historico["eventos"]}
    ineditos = [x for x in novos if x["id"] not in vistos]
    historico["eventos"].extend(ineditos)
    if gravar:
        json.dump(agora, open(SNAPSHOT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        json.dump(historico, open(HISTORICO, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        renderizar(historico, agora["nomes"], data)
    return ineditos, historico, agora


FIX = {
    "estados": {"ufs": [{"uf": "SC", "nome": "Santa Catarina", "status": "NOVO", "doc": "Plano X", "data": "01/06/2026"},
                        {"uf": "PB", "nome": "Paraíba", "status": "LAC", "doc": "", "data": ""}]},
    "municipios": [{"nome": "Blumenau", "uf": "SC", "categoria": "plano", "documento": "PLANCON 2026", "data": "10/06/2026"}],
    "atos_resposta": {"eventos": []},
    "indice": {"SC": {"total": 78.6}, "PB": {"total": 11.9}},
}


def self_test():
    """Abertura, diff (estado, município novo, resposta, índice), dedup, Atom válido, banco intocado."""
    import copy, xml.etree.ElementTree as ET
    ev1, hist, foto = executar("24/08/2026", dados=dict(FIX, _antes=None), gravar=False)
    assert len(ev1) == 2 and all(e["tipo"] == "abertura" for e in ev1), ev1
    d2 = copy.deepcopy(FIX)
    d2["estados"]["ufs"][1].update(status="NOVO", doc="Decreto PB 1/2026", data="28/08/2026")
    d2["municipios"].append({"nome": "João Pessoa", "uf": "PB", "categoria": "decreto", "documento": "Decreto 9/2026", "data": "20/08/2026"})
    d2["atos_resposta"]["eventos"].append({"nome": "Biguaçu", "uf": "SC", "data": "30/08/2026"})
    d2["indice"]["PB"] = {"total": 74.3}
    ev2, hist2, _ = executar("31/08/2026", dados=dict(d2, _antes=foto, _historico=hist), gravar=False)
    tipos = sorted(e["tipo"] for e in ev2)
    assert tipos == ["estado", "indice", "municipio", "resposta"], tipos
    assert any("Paraíba: instrumento estadual" in e["titulo"] for e in ev2) and any("11,9 → 74,3" in e["titulo"] for e in ev2)
    ev3, _, _ = executar("31/08/2026", dados=dict(d2, _antes=foto, _historico=hist2), gravar=False)
    assert ev3 == [], "mesma mudança não pode virar evento duas vezes"
    x = atom("t", "SC.xml", [e for e in hist2["eventos"] if e["uf"] == "SC"], "31/08/2026")
    ET.fromstring(x.encode("utf-8"))
    assert "não pontua" in x and "criad" not in x.lower()
    print("✓ self-test OK — abertura, diff (estado/município/resposta/índice), dedup, Atom válido")
    return 0


def main():
    """Interface de linha de comando."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default=datetime.date.today().strftime("%d/%m/%Y"))
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    novos, hist, _ = executar(a.data)
    print(f"✓ feeds: {len(novos)} evento(s) novo(s) em {a.data}; histórico com {len(hist['eventos'])}; 28 feeds em feeds/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
