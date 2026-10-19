#!/usr/bin/env python3
"""Regras de dado, num executor só (consolidação, item 6, 19/10/2026).

Sete portões pequenos tinham o mesmo esqueleto (docstring, `problemas()`, autoteste, `main()`) e
liam `data/`. Aqui cada regra é um bloco de duas funções — `problemas_*` (pura) e `real_*` (lê o
disco) — e uma lista de casos; o esqueleto existe uma vez. Cada regra e cada caso de teste dos
sete foram preservados.

AS REGRAS
  ausencia    `data/ausencia_declarada.json` (§201): órgão, data e canal nomeados; `efeito_no_indice`
              explícito; UF das 27; escopo único por UF; resumo curto. E a resposta sanitária só
              publica 0 com as duas buscas datadas (17/10/2026).
  rotulo      canal de DESCOBERTA (`imprensa`) nunca exibido como canal de registro: onde a página
              monta o rótulo, a palavra "descoberta" acompanha (§281, §5.2.1).
  camada      camada declarada (`data/percentual_uf.json`) nunca conta mais municípios do que o
              estado tem; contador declarado exige fonte (D2, 08/10/2026).
  esquema     `data/atos_resposta.json` dentro de `schemas/ato_resposta.json`: datas em dd/mm/aaaa,
              nenhuma posterior ao corte, ibge de sete dígitos (item 1.3, 08/10/2026).
  proveniencia todo documento pontuado aponta para o próprio endereço, ou declara a lacuna; o teto
              de defeitos de prova só desce (ajuste 2, 09/10/2026).
  redes       rede social é descoberta, nunca fonte de registro nem fonte no site (editoria,
              28/09/2026, item 2).
  imprensa    imprensa DESCOBRE, nunca REGISTRA: registro que pontua aponta para domínio oficial ou
              diário (C10, errata C29, 01/10/2026).

BARRA A PUBLICAÇÃO (editoria, 06/10/2026) só `camada` e `esquema`: são integridade do dado. As
outras cinco reprovam o PR e não seguram o publicador. Por isso a CI chama o executor duas vezes:
`--barra` (as duas que barram) e `--resto`.

USO
  python3 scripts/verificar_regras_de_dado.py [--barra | --resto]    # confere os dados reais
  python3 scripts/verificar_regras_de_dado.py --autoteste             # puro: não lê data/, não escreve
"""
import json
import pathlib
import re
import sys
from urllib.parse import urlparse

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))


def _json(rel: str):
    return json.loads((RAIZ / rel).read_text(encoding="utf-8"))


# ───────────────────────────── ausencia ─────────────────────────────
UFS = {"AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB",
       "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"}
LIMITE_RESUMO = 400   # o fato cabe; o texto da resposta, não


def problemas_ausencia(doc: dict) -> list:
    falhas = []
    obrig = doc.get("campos_obrigatorios") or []
    if not obrig:
        falhas.append("campos_obrigatorios ausente — o arquivo precisa declarar o que exige de si")
    vistos = set()
    for i, it in enumerate(doc.get("itens") or [], 1):
        rot = f"item {i} ({it.get('uf', '?')}/{str(it.get('escopo'))[:28]})"
        for campo in obrig:
            v = it.get(campo)
            if v is None or (isinstance(v, str) and not v.strip()):
                falhas.append(f"{rot}: campo obrigatório vazio — '{campo}'")
        if it.get("uf") not in UFS:
            falhas.append(f"{rot}: UF fora das 27")
        chave = (it.get("uf"), str(it.get("escopo", "")).strip().lower())
        if chave in vistos:
            falhas.append(f"{rot}: escopo repetido para a mesma UF — duas declarações do mesmo fato")
        vistos.add(chave)
        resumo = str(it.get("resumo_publico") or "")
        if len(resumo) > LIMITE_RESUMO:
            falhas.append(f"{rot}: resumo_publico com {len(resumo)} caracteres (teto {LIMITE_RESUMO}) — "
                          "este arquivo guarda o fato, não o texto da resposta")
    return falhas


def zero_sem_busca(resposta: dict) -> list:
    zero = 0 in (resposta.get("emergencias"), resposta.get("indice"), resposta.get("pop_sob_emergencia"))
    return ["monitor_saude.resposta: 0 publicado sem as duas buscas (situacao "
            f"{resposta.get('situacao')!r})"] if zero and resposta.get("situacao") != "verificado" else []


def real_ausencia():
    if not (RAIZ / "data/ausencia_declarada.json").exists():
        return ["data/ausencia_declarada.json ausente"], ""
    doc = _json("data/ausencia_declarada.json")
    mon = RAIZ / "data/monitor_saude.json"
    falhas = problemas_ausencia(doc) + (zero_sem_busca(_json("data/monitor_saude.json").get("resposta") or {})
                                        if mon.exists() else ["data/monitor_saude.json ausente"])
    return falhas, (f"{len(doc.get('itens') or [])} declaração(ões) de órgão competente, cada uma com "
                    f"fonte nomeada, data e efeito no índice explícito")


_AUS = {"campos_obrigatorios": ["uf", "escopo", "orgao"],
        "itens": [{"uf": "MT", "escopo": "plano estadual", "orgao": "X", "resumo_publico": "curto"}]}


def _aus_n(**item):
    return len(problemas_ausencia({**_AUS, "itens": [item]}))


CASOS_AUSENCIA = [
    ("resposta sanitária: 0 sem as duas buscas reprova",
     bool(zero_sem_busca({"emergencias": 0, "indice": 0.0})) and not zero_sem_busca(
         {"emergencias": 0, "indice": 0.0, "situacao": "verificado"}) and not zero_sem_busca(
         {"situacao": "nao_coletado"})),
    ("arquivo íntegro passa", problemas_ausencia(_AUS) == []),
    ("campo obrigatório vazio reprova",
     _aus_n(uf="MT", escopo="plano estadual", orgao="  ", resumo_publico="x") >= 1),
    ("UF inválida reprova", _aus_n(uf="XX", escopo="plano", orgao="X", resumo_publico="x") >= 1),
    ("mesmo escopo duas vezes na mesma UF reprova",
     len(problemas_ausencia({**_AUS, "itens": [dict(_AUS["itens"][0]), dict(_AUS["itens"][0])]})) >= 1),
    ("resumo longo demais reprova (é o texto da resposta vazando)",
     _aus_n(**{**_AUS["itens"][0], "resumo_publico": "a" * (LIMITE_RESUMO + 1)}) >= 1),
    ("sem campos_obrigatorios reprova", len(problemas_ausencia({"itens": []})) >= 1),
]


# ───────────────────────────── rotulo ─────────────────────────────
# Canais de descoberta, e a palavra que precisa acompanhar cada um quando ele é exibido.
DESCOBERTA = {"imprensa": "descoberta"}
# Onde o rótulo é montado. Arquivo que deixar de existir reprova: o portão não pode virar verde
# por olhar para o vazio.
ARQUIVOS_DE_ROTULO = ["assets/js/index.js", "assets/js/proveniencia.js"]


def problemas_rotulo(nome: str, texto: str) -> list:
    p = []
    for canal, palavra in DESCOBERTA.items():
        # Formas em que um rótulo é escrito no projeto: `imprensa:'...'` e `imprensa: '...'`.
        for m in re.finditer(rf"""\b{canal}\s*:\s*(['"])(.*?)\1""", texto):
            rotulo = m.group(2)
            if palavra not in rotulo.lower():
                p.append(f"{nome}: o canal {canal!r} recebe o rótulo {rotulo!r}, sem a palavra "
                         f"{palavra!r} — canal de descoberta exibido como canal de registro faz o "
                         f"leitor tomar a matéria por prova do ato (§5.2.1)")
    return p


def real_rotulo():
    falhas, vistos = [], 0
    for nome in ARQUIVOS_DE_ROTULO:
        p = RAIZ / nome
        if not p.exists():
            falhas.append(f"{nome} não existe — este portão confere o rótulo do canal de descoberta "
                          f"ali e não pode ficar verde olhando para o vazio")
            continue
        texto = p.read_text(encoding="utf-8")
        falhas += problemas_rotulo(nome, texto)
        vistos += sum(1 for c, w in DESCOBERTA.items() if re.search(rf"\b{c}\b", texto) and w in texto.lower())
    return falhas, (f"{', '.join(sorted(DESCOBERTA))} exibido com a palavra que diz o que é, em "
                    f"{vistos} de {len(ARQUIVOS_DE_ROTULO)} arquivo(s) de rótulo")


CASOS_ROTULO = [
    ("rótulo com a palavra passa", problemas_rotulo("x", "imprensa:'imprensa (descoberta)'") == []),
    ("rótulo sem a palavra reprova", problemas_rotulo("x", "imprensa:'imprensa'") != []),
    ("aspas duplas e espaço também são vistos", problemas_rotulo("x", 'imprensa: "imprensa"') != []),
    ("maiúscula na palavra conta", problemas_rotulo("x", "imprensa:'Imprensa (Descoberta)'") == []),
    ("canal de registro não é assunto deste portão",
     problemas_rotulo("x", "site_municipal:'site oficial do município'") == []),
    ("rótulo vazio reprova", problemas_rotulo("x", "imprensa:''") != []),
]


# ───────────────────────────── camada ─────────────────────────────
def problemas_camada(por_uf: dict) -> list:
    fora = []
    for uf, x in sorted(por_uf.items()):
        dp = x.get("declarado_plano") or 0
        da = x.get("declarado_antigo") or 0
        total = x.get("total") or 0
        if dp < 0 or da < 0:
            fora.append(f"{uf}: contador declarado negativo (plano {dp}, antigo {da})")
        if total and dp > total:
            fora.append(f"{uf}: declarado_plano {dp} acima dos {total} municípios da UF")
        if total and da > total:
            fora.append(f"{uf}: declarado_antigo {da} acima dos {total} municípios da UF")
        if total and dp + da > total:
            fora.append(f"{uf}: declarado_plano + declarado_antigo = {dp + da} acima dos {total} "
                        f"municípios da UF — a mesma população contada duas vezes (D2)")
        if (dp or da) and not str(x.get("fonte_declarada") or "").strip():
            fora.append(f"{uf}: contador declarado sem `fonte_declarada` — número sem fonte não "
                        f"entra no índice")
    return fora


def real_camada():
    doc = _json("data/percentual_uf.json")
    bruto = doc.get("uf") if isinstance(doc, dict) and "uf" in doc else doc
    por_uf = bruto if isinstance(bruto, dict) else {x["uf"]: x for x in bruto}
    n = sum(1 for x in por_uf.values() if (x.get("declarado_plano") or 0) or (x.get("declarado_antigo") or 0))
    return problemas_camada(por_uf), f"{n} UF(s) com camada declarada, todas dentro do número de municípios do estado"


_RS = {"total": 497, "declarado_plano": 183, "declarado_antigo": 215, "fonte_declarada": "TCE-RS 2025"}
CASOS_CAMADA = [
    ("dentro do total passa", len(problemas_camada({"RS": _RS})) == 0),
    ("soma acima do total reprova", len(problemas_camada({"RS": {**_RS, "total": 300}})) == 1),
    ("um contador acima do total reprova",
     len(problemas_camada({"DF": {"total": 1, "declarado_plano": 80, "fonte_declarada": "MUNIC"}})) == 2),
    ("sem fonte reprova", len(problemas_camada({"PR": {"total": 399, "declarado_plano": 399}})) == 1),
    ("negativo reprova",
     len(problemas_camada({"PR": {"total": 399, "declarado_plano": -1, "fonte_declarada": "x"}})) == 1),
    ("UF sem contador declarado passa", len(problemas_camada({"SP": {"total": 645}})) == 0),
    ("soma igual ao total passa",
     len(problemas_camada({"PR": {"total": 399, "declarado_plano": 399, "declarado_antigo": 0,
                                  "fonte_declarada": "SISDC/CEPDEC-PR"}})) == 0),
]


# ───────────────────────────── esquema ─────────────────────────────
RE_BR = re.compile(r"^\d{2}/\d{2}/\d{4}$")
RE_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def problemas_esquema(eventos, esq, corte=None) -> list:
    obrig = list(esq["obrigatorios"])
    campos_de_data = list(esq["datas"]["campos"])
    fora = []
    for i, e in enumerate(eventos):
        etiqueta = f"evento {i} ({e.get('nome')}/{e.get('uf')} {e.get('decreto')})"
        for c in obrig:
            if str(e.get(c) or "").strip():
                continue
            # `url` vazia é legítima quando o ato é conhecido por fonte oficial e o documento ainda
            # não foi lido (`documento_nao_localizado`). Fora disso, ato sem endereço não é conferível.
            if c == "url" and e.get("documento_nao_localizado"):
                continue
            fora.append(f"{etiqueta}: campo obrigatório ausente: {c}")
        for c in campos_de_data:
            v = e.get(c)
            if v is None or v == "":
                continue
            v = str(v)
            if RE_ISO.match(v):
                fora.append(f"{etiqueta}: {c} em ISO ({v}); o esquema exige dd/mm/aaaa")
            elif not RE_BR.match(v):
                fora.append(f"{etiqueta}: {c} fora de dd/mm/aaaa ({v})")
            elif corte:
                d, m, a = (int(x) for x in v.split("/"))
                if (a, m, d) > corte:
                    fora.append(f"{etiqueta}: {c} posterior ao corte ({v})")
        ibge = str(e.get("ibge") or "")
        if ibge and not re.fullmatch(r"\d{7}", ibge):
            fora.append(f"{etiqueta}: ibge fora de sete dígitos ({ibge})")
    return fora


def real_esquema():
    from coletores_base import data_do_corte
    c = data_do_corte()
    eventos = _json("data/atos_resposta.json").get("eventos") or []
    return (problemas_esquema(eventos, _json("schemas/ato_resposta.json"), corte=(c.year, c.month, c.day)),
            f"{len(eventos)} eventos dentro de schemas/ato_resposta.json")


_ESQ = {"obrigatorios": {k: "" for k in ("nome", "uf", "data", "causa", "decreto", "fonte", "url", "canal")},
        "datas": {"campos": ["data", "data_ato", "data_publicacao"]}}
_ATO = {"nome": "Piranhas", "uf": "AL", "data": "22/09/2026", "causa": "situação de emergência",
        "decreto": "Decreto nº 31", "fonte": "Diário consorciado", "url": "https://x/e.pdf",
        "canal": "DOM-consorciado", "ibge": "2707602", "data_publicacao": "23/09/2026"}


def _esq_n(**campos):
    return len(problemas_esquema([{**_ATO, **campos}], _ESQ, corte=(2026, 10, 8)))


CASOS_ESQUEMA = [
    ("evento completo passa", _esq_n() == 0),
    ("data em ISO reprova", _esq_n(data="2026-09-22") == 1),
    ("data_publicacao em ISO reprova", _esq_n(data_publicacao="2026-09-23") == 1),
    ("data em texto reprova", _esq_n(data="22 de setembro") == 1),
    ("campo obrigatório vazio reprova", _esq_n(canal="") == 1),
    ("ibge curto reprova", _esq_n(ibge="27076") == 1),
    ("ibge ausente passa",
     len(problemas_esquema([{k: v for k, v in _ATO.items() if k != "ibge"}], _ESQ, corte=(2026, 10, 8))) == 0),
    ("data futura reprova", _esq_n(data="31/12/2027") == 1),
    ("url vazia reprova", _esq_n(url="") == 1),
    ("url vazia passa com documento_nao_localizado", _esq_n(url="", documento_nao_localizado=True) == 0),
]


# ───────────────────────────── proveniencia ─────────────────────────────
PONTUADAS = ("plano", "plano_antigo", "estrutura")
PONTUADOS_UF = ("NOVO", "READ", "VIG")
TETO_DE_DEFEITOS = 10   # 10/10/2026: 31 de 41 pontuados com endereço; 10 defeitos de prova


def problemas_proveniencia(estados: dict, municipios: list, js: str) -> list:
    out = []
    for u in (estados or {}).get("ufs") or []:
        for i in u.get("instrumentos") or []:
            if i.get("status") == "LAC":
                continue
            if not (i.get("url") or i.get("urls") or i.get("endereco_lacuna")):
                out.append(f"{u.get('uf')} · {i.get('tipo')}: sem endereço e sem lacuna declarada")
            # 10/10/2026 (item 2b): "se encontrou o plano, sabe onde encontrar o link". Pontuado sem
            # endereço nem cópia preservada só passa como DEFEITO DE PROVA declarado — e o número só desce.
            if i.get("status") in PONTUADOS_UF and not (i.get("url") or i.get("urls") or i.get("copia_preservada")):
                if not i.get("defeito_de_prova"):
                    out.append(f"{u.get('uf')} · {i.get('tipo')}: pontuado ({i.get('status')}) sem "
                               f"endereço, sem cópia preservada e sem defeito de prova declarado")
            if (i.get("url") or i.get("urls")) and not i.get("consultado_em"):
                out.append(f"{u.get('uf')} · {i.get('tipo')}: endereço sem data de consulta")
    defeitos = sum(1 for u in (estados or {}).get("ufs") or [] for i in u.get("instrumentos") or []
                   if i.get("defeito_de_prova"))
    if defeitos > TETO_DE_DEFEITOS:
        out.append(f"{defeitos} defeitos de prova estaduais, acima do teto de {TETO_DE_DEFEITOS} "
                   f"(o teto só desce: endereço achado sai do teto, defeito novo não entra)")
    for m in municipios or []:
        if m.get("categoria") in PONTUADAS and not m.get("url"):
            out.append(f"{m.get('nome')}/{m.get('uf')} · {m.get('categoria')}: pontuado sem endereço")
    if "docComEndereco(d)" not in js or "docComEndereco(d.estrutura)" not in js:
        out.append("assets/js/index.js: o cartão do estado não liga o documento ao endereço")
    if "endereço do documento não localizado até o corte" not in js:
        out.append("assets/js/index.js: o cartão do estado não declara a lacuna de endereço")
    return out


def real_proveniencia():
    estados = _json("data/estados.json")
    mun = _json("data/municipios.json")
    mun = mun if isinstance(mun, list) else mun.get("municipios") or []
    js = (RAIZ / "assets/js/index.js").read_text(encoding="utf-8")
    inst = [i for u in estados["ufs"] for i in u.get("instrumentos") or []]
    com = sum(1 for i in inst if i.get("url") or i.get("urls"))
    lac = sum(1 for i in inst if i.get("endereco_lacuna"))
    return problemas_proveniencia(estados, mun, js), (
        f"instrumentos estaduais: {com} com endereço, {lac} com lacuna declarada; todo registro "
        f"municipal pontuado tem endereço; o cartão liga o documento")


_JS = "docComEndereco(d) docComEndereco(d.estrutura) endereço do documento não localizado até o corte"
_UF_BOM = {"ufs": [{"uf": "SC", "instrumentos": [
    {"tipo": "x", "status": "NOVO", "url": "https://a.sc.gov.br/p.pdf", "consultado_em": "2026-10-10"},
    {"tipo": "y", "status": "ELAB", "endereco_lacuna": {"motivo": "m"}},
    {"tipo": "z", "status": "LAC"}]}]}


def _go(**inst):
    return problemas_proveniencia({"ufs": [{"uf": "GO", "instrumentos": [{"tipo": "x", **inst}]}]}, [], _JS)


CASOS_PROVENIENCIA = [
    ("endereço ou lacuna declarada passa", problemas_proveniencia(_UF_BOM, [], _JS) == []),
    ("instrumento sem endereço e sem lacuna reprova",
     len(problemas_proveniencia({"ufs": [{"uf": "SC", "instrumentos": [{"tipo": "x", "status": "NOVO"}]}]}, [], _JS)) >= 1),
    ("plano municipal sem endereço reprova",
     len(problemas_proveniencia(_UF_BOM, [{"nome": "X", "uf": "SC", "categoria": "plano"}], _JS)) == 1),
    ("decreto sem endereço não é pontuado e passa",
     problemas_proveniencia(_UF_BOM, [{"nome": "X", "uf": "SC", "categoria": "decreto"}], _JS) == []),
    ("cartão sem link reprova", len(problemas_proveniencia(_UF_BOM, [], "nada")) == 2),
    ("pontuado só com lacuna, sem defeito declarado, reprova",
     len(_go(status="NOVO", endereco_lacuna={"motivo": "m"})) == 1),
    ("pontuado com defeito de prova declarado passa",
     _go(status="NOVO", endereco_lacuna={"motivo": "m"}, defeito_de_prova={"motivo": "d"}) == []),
    ("pontuado com cópia preservada passa",
     _go(status="VIG", endereco_lacuna={"motivo": "m"}, copia_preservada="evidencias/h.pdf") == []),
    ("endereço sem data de consulta reprova", len(_go(status="NOVO", url="https://a.go.gov.br/p")) == 1),
    ("defeitos acima do teto reprovam",
     any("teto" in x for x in problemas_proveniencia({"ufs": [{"uf": "GO", "instrumentos": [
         {"tipo": str(k), "status": "LAC", "defeito_de_prova": {"motivo": "d"}}
         for k in range(TETO_DE_DEFEITOS + 1)]}]}, [], _JS))),
]


# ───────────────────────────── redes ─────────────────────────────
REDES = ("facebook.com", "instagram.com", "twitter.com", "x.com", "youtube.com", "threads.net",
         "bsky.app", "tiktok.com")
# Fonte escrita à mão não traz domínio ("Instagram da Prefeitura", "post no Facebook"): o portão que
# olhava só o domínio deixava passar a forma mais provável. `x` sozinho fica FORA: casaria em qualquer texto.
NOMES_DE_REDE = ("facebook", "instagram", "twitter", "youtube", "tiktok", "threads", "bluesky", "bsky")
RE_NOME_DE_REDE = re.compile(r"\b(" + "|".join(NOMES_DE_REDE) + r")\b", re.I)
BANCOS = ("municipios.json", "estados.json", "atos_resposta.json")
CAMPOS = ("url", "fonte", "canal", "documento")
# Onde o leitor lê "de onde veio o dado": crédito de figura e link de fonte.
RE_FONTE_NA_PAGINA = re.compile(r'(?:class="fonte-figura"[^>]*>|Fonte:)([^<]{0,400})', re.I)


def rede_em(texto) -> str:
    t = str(texto or "").lower()
    for rede in REDES:
        if rede in t:
            return rede
    m = RE_NOME_DE_REDE.search(t)
    return m.group(1) if m else ""


def problemas_banco_de_rede(nome: str, registros: list) -> list:
    falhas = []
    for r in registros or []:
        for campo in CAMPOS:
            rede = rede_em(r.get(campo))
            if rede:
                falhas.append(f"{nome}: {r.get('nome') or r.get('uf') or '?'} tem `{campo}` em "
                              f"{rede} — rede social é descoberta, nunca fonte de registro")
    return falhas


def problemas_pagina_de_rede(nome: str, html: str) -> list:
    falhas = []
    for m in RE_FONTE_NA_PAGINA.finditer(html or ""):
        rede = rede_em(m.group(1))
        if rede:
            falhas.append(f"{nome}: crédito de figura cita {rede} — \"{' '.join(m.group(1).split())[:80]}\"")
    return falhas


def real_redes():
    falhas = []
    for nome in BANCOS:
        if not (RAIZ / "data" / nome).exists():
            continue
        doc = _json(f"data/{nome}")
        for chave in ("municipios", "ufs", "atos", "itens"):
            if isinstance(doc, dict) and isinstance(doc.get(chave), list):
                falhas += problemas_banco_de_rede(nome, doc[chave])
        if isinstance(doc, list):
            falhas += problemas_banco_de_rede(nome, doc)
        if isinstance(doc, dict) and isinstance(doc.get("ufs"), dict):
            falhas += problemas_banco_de_rede(nome, list(doc["ufs"].values()))
    for p in sorted(RAIZ.glob("*.html")):
        falhas += problemas_pagina_de_rede(p.name, p.read_text(encoding="utf-8", errors="replace"))
    return falhas, ("nenhum registro e nenhuma página cita rede social como fonte; nenhum domínio de "
                    "rede está nos padrões de fonte oficial do juiz")


def _casos_redes() -> list:
    from juiz import PADROES_FONTE_PROVAVEL_OFICIAL as oficiais
    limpo = [{"nome": "Bonito", "url": "https://bonito.ms.gov.br/d", "fonte": "Diário Oficial", "canal": "DOM"}]
    casos = [("banco limpo passa", problemas_banco_de_rede("x.json", limpo) == [])]
    for campo, valor in (("url", "https://facebook.com/prefbonito/posts/1"), ("fonte", "Instagram da Prefeitura"),
                         ("canal", "x.com"), ("documento", "post no Facebook")):
        f = problemas_banco_de_rede("x.json", [{"nome": "Bonito", campo: valor}])
        casos.append((f"rede social em `{campo}` reprova", len(f) == 1 and campo in f[0]))
    casos += [
        ("banco vazio não reprova", problemas_banco_de_rede("x.json", []) == []),
        ("registro sem os campos não estoura", problemas_banco_de_rede("x.json", [{"nome": "X"}]) == []),
        ("página limpa passa", problemas_pagina_de_rede(
            "p.html", '<p class="fonte-figura">Fonte: Diário Oficial · Atualização: 28/09/2026</p>') == []),
        ("rede social no crédito de figura reprova", len(problemas_pagina_de_rede(
            "p.html", '<p class="fonte-figura">Fonte: Instagram da Defesa Civil</p>')) == 1),
        ("`Fonte:` em prosa com rede social também reprova",
         len(problemas_pagina_de_rede("p.html", "<p>Fonte: facebook.com/prefeitura</p>")) == 1),
        ("prosa que MENCIONA rede social sem ser fonte não reprova",
         problemas_pagina_de_rede("p.html", "<p>A prefeitura anunciou no Instagram.</p>") == []),
        ("nenhuma rede social está nos padrões de fonte oficial do juiz",
         not any(rede in p or p in rede for rede in REDES for p in oficiais)),
    ]
    return casos


# ───────────────────────────── imprensa ─────────────────────────────
# Categorias que CREDITAM no índice. Decreto não pontua e `nao_verificado`/`nao_localizado` valem zero:
# nenhuma delas move ponto, e por isso nenhuma entra na conferência.
PONTUAM = {"plano", "plano_novo", "plano_readaptado", "plano_recorrente",
           "plano_antigo", "plano_elaboracao", "plano_saude", "estrutura"}
SUFIXOS_OFICIAIS = (".gov.br", ".leg.br", ".jus.br")
# Entes que publicam ato oficial fora do `gov.br`. Lista curta de propósito: crescer por conveniência
# é como a notícia entraria de volta.
HOSTS_OFICIAIS = {"www.diariomunicipal.com.br", "diariomunicipal.com.br", "prefeitura.poa.br"}


def host_oficial(host: str) -> bool:
    host = host.lower()
    return (host in HOSTS_OFICIAIS or "queridodiario.ok.org.br" in host or "data.queridodiario" in host
            or host.endswith(SUFIXOS_OFICIAIS))


def problemas_imprensa(nome: str, registros) -> list:
    falhas = []
    if isinstance(registros, dict):
        registros = list(registros.values())
    for r in registros:
        if not isinstance(r, dict) or r.get("categoria") not in PONTUAM:
            continue
        url = (r.get("url") or "").strip()
        if not url:
            continue   # URL ausente é outro defeito, de outra regra (`proveniencia`)
        host = urlparse(url).netloc
        if host and not host_oficial(host):
            quem = f"{r.get('nome') or r.get('uf') or '?'} ({r.get('uf', '?')})"
            falhas.append(f"{nome}: {quem} pontua como '{r['categoria']}' com URL em '{host}' — não é "
                          f"domínio oficial nem diário. Troque pela fonte primária ou rebaixe a pista (C10).")
    return falhas


def real_imprensa():
    falhas = []
    for nome in ("municipios.json", "estados.json"):
        if (RAIZ / "data" / nome).exists():
            falhas += problemas_imprensa(nome, _json(f"data/{nome}"))
    return falhas, "nenhum registro pontuável apoiado em domínio que não seja oficial ou diário"


CASOS_IMPRENSA = [
    ("plano pontuado em jornal reprova",
     len(problemas_imprensa("m", [{"nome": "Curitiba", "uf": "PR", "categoria": "plano",
                                   "url": "https://agoraparana.com.br/x"}])) == 1),
    ("plano pontuado em domínio gov.br passa",
     problemas_imprensa("m", [{"categoria": "plano", "url": "https://x.pr.gov.br/p.pdf"}]) == []),
    ("diário agregado e Querido Diário passam",
     problemas_imprensa("m", [{"categoria": "estrutura", "url": "https://www.diariomunicipal.com.br/a"},
                              {"categoria": "plano", "url": "https://queridodiario.ok.org.br/b"}]) == []),
    ("decreto não pontua e não é conferido",
     problemas_imprensa("m", [{"categoria": "decreto", "url": "https://jornal.com/x"}]) == []),
    ("URL ausente não é deste portão", problemas_imprensa("m", [{"categoria": "plano"}]) == []),
]


# ───────────────────────────── executor ─────────────────────────────
# (nome, barra a publicação, confere o disco)
REGRAS = [("ausencia", False, real_ausencia), ("rotulo", False, real_rotulo),
          ("camada", True, real_camada), ("esquema", True, real_esquema),
          ("proveniencia", False, real_proveniencia), ("redes", False, real_redes),
          ("imprensa", False, real_imprensa)]


def autoteste() -> int:
    casos = [(f"{n}: {r}", ok) for n, cs in (("ausencia", CASOS_AUSENCIA), ("rotulo", CASOS_ROTULO),
                                             ("camada", CASOS_CAMADA), ("esquema", CASOS_ESQUEMA),
                                             ("proveniencia", CASOS_PROVENIENCIA),
                                             ("redes", _casos_redes()), ("imprensa", CASOS_IMPRENSA))
             for r, ok in cs]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    ruins = [n for n, ok in casos if not ok]
    print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s)." if ruins
          else f"OK AUTOTESTE — {len(casos)} casos, sem rede e sem escrita.")
    return 1 if ruins else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    so_barra, so_resto = "--barra" in sys.argv, "--resto" in sys.argv
    ruim = False
    for nome, barra, real in REGRAS:
        if (so_barra and not barra) or (so_resto and barra):
            continue
        falhas, resumo = real()
        if falhas:
            ruim = True
            print(f"✗ {nome.upper()}: {len(falhas)} problema(s)")
            for f in falhas[:40]:
                print(f"   · {f}")
            if len(falhas) > 40:
                print(f"   … e outros {len(falhas) - 40}")
        else:
            print(f"✓ {nome.upper()} OK — {resumo}.")
    return 1 if ruim else 0


if __name__ == "__main__":
    sys.exit(main())
