#!/usr/bin/env python3
"""Regras de dado, num executor só (consolidação, item 6, 19–20/10/2026).

Catorze portões pequenos tinham o mesmo esqueleto (docstring, `problemas()`, autoteste, `main()`) e
liam `data/`. Aqui cada regra é um bloco de duas funções — `problemas_*` (pura) e `real_*` (lê o
disco) — e uma lista de casos; o esqueleto existe uma vez. Cada regra e cada caso de teste dos
catorze foram preservados.

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
  financiamento  cartões do topo do Financiamento: lacuna declarada, nunca zero; o número da imprensa
              é o mesmo onde a janela é a mesma (02/10/2026).
  versao      a versão do índice é uma só (`meta.json`), repetida em datapackage e CITATION; o texto
              público não nomeia o que a definição do índice não tem (08 e 16/10/2026).
  pdf         análise de sensibilidade e PDF público usam a conta do motor (08/10/2026).
  semana      cartões "Esta semana em números" da Imprensa: paridade com `semana.json`, zero ≠ sem
              coleta, variação só com par, datas dos atos legíveis nos dois formatos (§253, §255).
  ancoras     âncora interna citada por página ou script existe no destino (01/10 e 16/10/2026).
  paridade_qd `cobertura_qd.json` e `verificacao_resumo.json` contam o mesmo acervo; indefinido nunca
              é `false`; partição de três parcelas (§256, §280).
  log         o log de buscas só cresce (marca d'água total e por mês), sem linha inválida, com
              data ISO e decisão do vocabulário (item 4, 28/09/2026; `--marcar-log` atualiza a marca).

BARRA A PUBLICAÇÃO (editoria, 06/10/2026) só `camada` e `esquema`: são integridade do dado. As
outras doze reprovam o PR e não seguram o publicador. Por isso a CI chama o executor duas vezes:
`--barra` (as duas que barram) e `--resto`.

USO
  python3 scripts/verificar_regras_de_dado.py [--barra | --resto]    # confere os dados reais
  python3 scripts/verificar_regras_de_dado.py --autoteste             # puro: não lê data/, não escreve
"""
import json
import pathlib
import re
import sys
from datetime import datetime
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
# O tenant `rsgovbr` é o do governo do RS: a pasta pública de PLANCONs da Casa Militar (REPOSITORIOS["RS"]).
HOSTS_OFICIAIS = {"www.diariomunicipal.com.br", "diariomunicipal.com.br", "prefeitura.poa.br",
                  "rsgovbr-my.sharepoint.com"}


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


# ─────────────────────────── financiamento ───────────────────────────
# Cartões do topo do Financiamento contra a edição da imprensa (item 4, 02/10/2026): os quatro
# existem; lacuna tem motivo e valor nulo (ausência não é número; a classe de ausência de 09/10/2026
# não exige período); recorte semanal igual ao da imprensa; corte não mais velho que o dela.
ESPERADOS_FIN = ["pago_periodo_mp", "transferido_municipios_periodo", "resposta_liberado_semana",
                 "atos_federais_semana"]
MESMO_NUMERO = {"atos_federais_semana": "atos_federais_no_periodo"}   # cartão → cartão da imprensa


def _data(s):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(s)[:10], fmt)
        except (ValueError, TypeError):
            continue
    return None


def problemas_financiamento(fin: dict, imp: dict) -> list:
    ruins = []
    cartoes = {c.get("id"): c for c in (fin or {}).get("cartoes") or []}
    for ident in ESPERADOS_FIN:
        if ident not in cartoes:
            ruins.append(f"cartão '{ident}' não existe em financiamento/semana.json")
    for ident, c in cartoes.items():
        if c.get("sem_coleta"):
            if c.get("valor") is not None:
                ruins.append(f"cartão '{ident}': declarado sem coleta e com valor — ausência não é número")
            if not c.get("detalhe"):
                ruins.append(f"cartão '{ident}': sem coleta e sem motivo escrito (lacuna tem de ser declarada)")
        elif c.get("classe"):
            if c.get("valor") is not None:
                ruins.append(f"cartão '{ident}': declarou classe de ausência e trouxe valor — "
                             f"ausência não é número")
            if not c.get("detalhe"):
                ruins.append(f"cartão '{ident}': classe de ausência sem motivo escrito")
        else:
            if c.get("valor") is None:
                ruins.append(f"cartão '{ident}': valor nulo sem declarar a lacuna")
            if not c.get("periodo"):
                ruins.append(f"cartão '{ident}': sem o período a que o número se refere")
            if not c.get("fonte"):
                ruins.append(f"cartão '{ident}': sem fonte")
    por_id_imp = {c.get("id"): c for c in (imp or {}).get("cartoes") or []}
    for aqui, la in MESMO_NUMERO.items():
        a, b = cartoes.get(aqui), por_id_imp.get(la)
        if not a or not b or a.get("sem_coleta") or b.get("sem_coleta"):
            continue
        if a.get("valor") != b.get("valor"):
            ruins.append(f"mesmo número com valores diferentes: '{aqui}' = {a.get('valor')} e "
                         f"imprensa '{la}' = {b.get('valor')}")
    d_fin, d_imp = _data((fin or {}).get("corte")), _data((imp or {}).get("corte"))
    if d_fin and d_imp and d_fin < d_imp:
        ruins.append(f"corte do Financiamento ({fin.get('corte')}) mais velho que o da imprensa "
                     f"({imp.get('corte')})")
    return ruins


def real_financiamento():
    def ler(rel):
        p = RAIZ / "data" / rel
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
    fin = ler("financiamento/semana.json")
    if fin is None:
        return (["data/financiamento/semana.json não existe — rode gerar_financiamento_semana.py"],
                "")
    return (problemas_financiamento(fin, ler("imprensa/semana.json") or {}),
            f"{len(fin.get('cartoes') or [])} cartões com período, fonte e lacuna declarada, e o "
            "mesmo número da imprensa onde a janela é a mesma")


_FB = {"corte": "02/10/2026", "cartoes": [
    {"id": i, "valor": 1, "periodo": "x", "fonte": "f", "sem_coleta": False} for i in ESPERADOS_FIN]}
_FI = {"corte": "02/10/2026", "cartoes": []}


def _fc(**campos):
    return {"corte": "02/10/2026", "cartoes": [dict(_FB["cartoes"][0], **campos)] + _FB["cartoes"][1:]}


def _fim(valor, sem_coleta=False):
    return {"corte": "02/10/2026", "cartoes": [
        {"id": "atos_federais_no_periodo", "valor": valor, "sem_coleta": sem_coleta}]}


_CLASSE = dict(valor=None, periodo=None, sem_coleta=False, classe="sem_data_na_origem")
CASOS_FINANCIAMENTO = [
    ("arquivo completo passa", problemas_financiamento(_FB, _FI) == []),
    ("cartão faltando reprova",
     len(problemas_financiamento({"corte": "02/10/2026", "cartoes": _FB["cartoes"][:2]}, {})) == 2),
    ("sem coleta com valor reprova", any("ausência não é número" in p for p in problemas_financiamento(
        _fc(sem_coleta=True, valor=0, detalhe="x"), {}))),
    ("sem coleta sem motivo reprova", any("sem motivo escrito" in p for p in problemas_financiamento(
        _fc(sem_coleta=True, valor=None), {}))),
    ("classe de ausencia declarada passa, e sem exigir periodo", problemas_financiamento(
        _fc(detalhe="a origem nao datou o ato", **_CLASSE), _FI) == []),
    ("classe de ausencia com valor reprova", any("ausência não é número" in p for p in
        problemas_financiamento(_fc(detalhe="x", **dict(_CLASSE, valor=3)), {}))),
    ("classe de ausencia sem motivo reprova", any("sem motivo escrito" in p for p in
        problemas_financiamento(_fc(**_CLASSE), {}))),
    ("valor sem período reprova", any("sem o período" in p for p in
        problemas_financiamento(_fc(periodo=None), {}))),
    ("mesmo número divergente reprova", any("valores diferentes" in p for p in
        problemas_financiamento(_FB, _fim(9)))),
    ("mesmo número igual passa", problemas_financiamento(_FB, _fim(1)) == []),
    ("imprensa sem coleta não compara", problemas_financiamento(_FB, _fim(None, True)) == []),
    ("corte mais velho reprova", any("mais velho" in p for p in problemas_financiamento(
        dict(_FB, corte="29/09/2026"), _FI))),
    ("corte ilegível não levanta", problemas_financiamento(dict(_FB, corte="ontem"), {"corte": "x"}) == []),
]


# ───────────────────────────── versão do índice ─────────────────────────────
# A versão do índice é uma só, e tem dono (HANDOVER_CORRECAO_DEFINITIVA_08-10-2026, item 1.15):
# `meta.json` (escrito por `recalcular_mare.py --write`) manda; datapackage e CITATION a repetem; nenhuma
# régua extinta volta à tabela normativa; a v3.2 roda em paralelo e nenhuma página a lê; e (16/10/2026)
# o texto público não nomeia o que `definicao_indice` não tem. Dispensa só por `layout/excecoes.json`
# (regra `versao_do_indice.texto`); a página do MARÉ Saúde é outro índice e fica fora.
TEMPO_NA_NOTA = re.compile(r"quando o plano foi publicado em rela[çc][ãa]o ao primeiro boletim", re.I)
PESO_A_MAO = re.compile(r"pesam igual", re.I)


def problemas_versao(meta, datapackage, citation, metodologia, paralelo_existe, lido_por_pagina) -> list:
    fora = []
    versao = str(meta.get("versao_indice") or "")
    if not versao:
        fora.append("data/meta.json sem `versao_indice` — a versão do índice tem de ter dono, e o "
                    "dono é o motor (`recalcular_mare.py --write`)")
    else:
        curta = versao.split(" ")[0].lstrip("v")
        if str(datapackage.get("version") or "") != curta:
            fora.append(f"datapackage.json diz versão {datapackage.get('version')!r} e o índice "
                        f"está em {curta!r}")
        m = re.search(r'(?m)^version:\s*"?([^"\n]+)"?', citation)
        if not m or m.group(1).strip() != curta:
            fora.append(f"CITATION.cff diz versão {m.group(1) if m else None!r} e o índice está "
                        f"em {curta!r}")
    if re.search(r"(?m)^  Antecipação\s{2,}100 = instrumento", metodologia):
        fora.append("a tabela §5.2 da METODOLOGIA ainda nomeia 'Antecipação' como componente; ela "
                    "saiu do índice em 30/09/2026")
    if re.search(r"crédito: plano 1,0 · plano_antigo 0,6", metodologia):
        fora.append("o §5.3 da METODOLOGIA ainda grafa o crédito antigo do plano de ciclo anterior "
                    "(0,6), revogado pelo §196 em 24/09/2026")
    if not paralelo_existe:
        fora.append("data/paralelo_v32.json não existe — a v3.2 está decidida desde 05/10/2026 e o "
                    "cálculo paralelo é o que a sustenta (A3-12)")
    if lido_por_pagina:
        fora.append("alguma página ou script de página lê data/paralelo_v32.json; a v3.2 roda em "
                    "paralelo e não publica nada")
    return fora


def problemas_versao_texto(meta: dict, catalogos: dict, dispensadas: set) -> list:
    """`catalogos` é {pagina: {identificador: texto}}; `dispensadas`, as páginas com exceção."""
    definicao = (meta or {}).get("definicao_indice") or {}
    if not definicao:
        return ["data/meta.json sem `definicao_indice` — a definição do índice tem dono, e é o motor "
                "(`recalcular_mare.py --write`)"]
    fora = []
    for pagina, textos in sorted((catalogos or {}).items()):
        if pagina == "saude" or f"{pagina}.html" in dispensadas:
            continue
        for ident, texto in sorted((textos or {}).items()):
            t = str(texto or "")
            if definicao.get("antecipacao_fora_da_nota") and TEMPO_NA_NOTA.search(t):
                fora.append(f"{ident}: apresenta a antecedência como medida da nota; ela saiu da "
                            f"nota na v3.1 (meta.json › definicao_indice)")
            if PESO_A_MAO.search(t) and "{n_componentes}" not in t:
                fora.append(f"{ident}: \"pesam igual\" escrito à mão; o número de componentes vem de "
                            f"meta.json pelo molde {{n_componentes}}")
    return fora


def real_versao():
    meta = _json("data/meta.json")
    dp_path, cff_path = RAIZ / "dados-abertos" / "datapackage.json", RAIZ / "CITATION.cff"
    dp = json.loads(dp_path.read_text(encoding="utf-8")) if dp_path.exists() else {}
    cff = cff_path.read_text(encoding="utf-8") if cff_path.exists() else ""
    lido = any("paralelo_v32" in p.read_text(encoding="utf-8", errors="ignore")
               for p in sorted(RAIZ.glob("*.html")) + sorted((RAIZ / "assets").rglob("*.js")))
    fora = problemas_versao(meta, dp, cff, (RAIZ / "METODOLOGIA.md").read_text(encoding="utf-8"),
                            (RAIZ / "data" / "paralelo_v32.json").exists(), lido)
    catalogos = {a.stem: (json.loads(a.read_text(encoding="utf-8")).get("textos") or {})
                 for a in sorted((RAIZ / "conteudo").glob("*.json")) if not a.name.startswith("_")}
    from verificar_conformidade import excecoes_de  # noqa: PLC0415 — a mesma leitura de exceção
    exc_arq = RAIZ / "layout" / "excecoes.json"
    exc = json.loads(exc_arq.read_text(encoding="utf-8")) if exc_arq.exists() else {}
    dispensadas = {f"{p}.html" for p in catalogos
                   if "versao_do_indice.texto" in excecoes_de(f"{p}.html", exc)}
    return (fora + problemas_versao_texto(meta, catalogos, dispensadas),
            f"versão {meta.get('versao_indice')} em meta.json, datapackage e CITATION; v3.2 "
            f"calculada em paralelo e fora das páginas")


_VM = {"versao_indice": "v3.1 (30/09/2026)"}
_VDP, _VCFF, _VMET = {"version": "3.1"}, 'cff-version: 1.2.0\nversion: "3.1"\n', "tabela limpa"
_VD = {"definicao_indice": {"antecipacao_fora_da_nota": True, "componentes": [1, 2, 3]}}
CASOS_VERSAO = [
    ("tudo alinhado passa", len(problemas_versao(_VM, _VDP, _VCFF, _VMET, True, False)) == 0),
    ("meta sem versao_indice reprova", len(problemas_versao({}, _VDP, _VCFF, _VMET, True, False)) == 1),
    ("datapackage desalinhado reprova",
     len(problemas_versao(_VM, {"version": "2.3"}, _VCFF, _VMET, True, False)) == 1),
    ("CITATION desalinhado reprova",
     len(problemas_versao(_VM, _VDP, 'version: "2.3"\n', _VMET, True, False)) == 1),
    ("Antecipação na tabela 5.2 reprova", len(problemas_versao(
        _VM, _VDP, _VCFF, "  Antecipação                  100 = instrumento anterior ao Boletim",
        True, False)) == 1),
    ("crédito antigo no 5.3 reprova", len(problemas_versao(
        _VM, _VDP, _VCFF, "crédito: plano 1,0 · plano_antigo 0,6 · plano_elaboracao 0,45",
        True, False)) == 1),
    ("paralelo ausente reprova", len(problemas_versao(_VM, _VDP, _VCFF, _VMET, False, False)) == 1),
    ("paralelo lido por página reprova", len(problemas_versao(_VM, _VDP, _VCFF, _VMET, True, True)) == 1),
    ("texto limpo passa",
     len(problemas_versao_texto(_VD, {"index": {"i.a": "Três componentes."}}, set())) == 0),
    ("antecedência como medida da nota reprova", len(problemas_versao_texto(_VD, {"index": {
        "i.a": "e quando o plano foi publicado em relação ao primeiro boletim"}}, set())) == 1),
    ("'pesam igual' à mão reprova; por molde passa", len(problemas_versao_texto(_VD, {"index": {
        "i.a": "Os três pesam igual.", "i.b": "Os {n_componentes} pesam igual."}}, set())) == 1),
    ("a página do MARÉ Saúde é outro índice",
     len(problemas_versao_texto(_VD, {"saude": {"s.a": "Os três pesam igual."}}, set())) == 0),
    ("exceção registrada dispensa a página", len(problemas_versao_texto(
        _VD, {"index": {"i.a": "Os três pesam igual."}}, {"index.html"})) == 0),
    ("meta sem definição reprova", len(problemas_versao_texto({}, {}, set())) == 1),
]


# ───────────────────────────── camadas do PDF ─────────────────────────────
# A análise de sensibilidade e o PDF público usam a conta do MOTOR (HANDOVER_CORRECAO_DEFINITIVA_08-10-2026,
# item 1.14, A3-05): a cobertura da análise é igual, UF por UF, à que o índice publica; as três camadas
# somam a cobertura publicada; nem o gerador do PDF nem a análise trazem peso escrito à mão nem
# componente extinto. Comentários não contam: o que explica o defeito corrigido cita o defeito.
PROIBIDOS_NO_PDF = (
    (re.compile(r"plano_antigo 0,6"), "crédito de plano_antigo extinto em 24/09/2026 (hoje 1,0)"),
    (re.compile(r'"Antecipação"'), "antecipação como componente, extinta em 30/09/2026 (v3.1)"),
    (re.compile(r"Valores de antecipação em uso"), "régua de antecipação como componente"),
    (re.compile(r"explica 55% da variância"), "número de variância escrito à mão"),
    (re.compile(r"com 44% da variância"), "número de contribuição escrito à mão"),
    (re.compile(r"\+0,66"), "correlação escrita à mão"),
)
COLUNA_ERRADA = re.compile(r"Xv\[i,\s*1\]\s*=\s*round\(cobertura")


def problemas_pdf_texto(pdf_py: str, analise_py: str) -> list:
    sem_comentarios = lambda f: "\n".join(l for l in f.split("\n") if not l.strip().startswith("#"))  # noqa: E731
    fora = []
    pdf_py, analise_py = sem_comentarios(pdf_py), sem_comentarios(analise_py)
    for regex, por_que in PROIBIDOS_NO_PDF:
        if regex.search(pdf_py):
            fora.append(f"gerar_pdf_indice.py traz {por_que}")
    if COLUNA_ERRADA.search(analise_py):
        fora.append("analise_sensibilidade.py escreve a cobertura na coluna 1, que na v3.1 é a "
                    "estrutura (A3-05)")
    if "rm.cobertura_de_uf" not in analise_py:
        fora.append("analise_sensibilidade.py não usa `recalcular_mare.cobertura_de_uf` — a conta "
                    "da cobertura tem um dono só")
    return fora


def problemas_pdf_numero(cobertura_da_analise: dict, cobertura_publicada: dict, camadas: dict) -> list:
    fora = []
    for uf, valor in sorted(cobertura_da_analise.items()):
        publicado = cobertura_publicada.get(uf)
        if publicado is None:
            fora.append(f"{uf}: a análise calcula cobertura para uma UF que o índice não tem")
        elif abs(valor - publicado) > 0.05:
            fora.append(f"{uf}: a análise calcula cobertura {valor:.1f} e o índice publica "
                        f"{publicado:.1f}")
    for uf, (doc, agr, dec) in sorted(camadas.items()):
        soma, publicado = doc + agr + dec, cobertura_publicada.get(uf)
        if publicado is not None and abs(soma - publicado) > 0.15:
            fora.append(f"{uf}: as três camadas somam {soma:.1f} e a cobertura publicada é "
                        f"{publicado:.1f}")
    return fora


def real_pdf():
    import analise_sensibilidade as asens  # noqa: PLC0415
    fora = problemas_pdf_texto((RAIZ / "gerar_pdf_indice.py").read_text(encoding="utf-8"),
                               (RAIZ / "analise_sensibilidade.py").read_text(encoding="utf-8"))
    R = asens.rodar() if hasattr(asens, "rodar") else asens.analisar()
    publicada = {uf: v["cobertura_pop"] for uf, v in _json("data/indice.json").items()}
    coberturas, camadas = R.get("cobertura_por_uf") or {}, R.get("camadas_absolutas") or {}
    return (fora + problemas_pdf_numero(coberturas, publicada, camadas),
            f"a análise e o PDF usam a conta do motor; {len(coberturas)} UFs conferidas e "
            f"{len(camadas)} decomposições somam a cobertura publicada")


CASOS_PDF = [
    ("texto limpo passa", len(problemas_pdf_texto("CREDITO_EM_USO", "rm.cobertura_de_uf(uf, c, w)")) == 0),
    ("crédito à mão reprova",
     len(problemas_pdf_texto("plano 1,0 · plano_antigo 0,6 ·", "rm.cobertura_de_uf()")) == 1),
    ("antecipação como componente reprova",
     len(problemas_pdf_texto('["Antecipação", "Tempestividade"]', "rm.cobertura_de_uf()")) == 1),
    ("coluna 1 reprova", len(problemas_pdf_texto(
        "CREDITO_EM_USO", "Xv[i, 1] = round(cobertura(u))\nrm.cobertura_de_uf()")) == 1),
    ("análise sem a porta do motor reprova",
     len(problemas_pdf_texto("CREDITO_EM_USO", "def cobertura(uf): ...")) == 1),
    ("cobertura igual à publicada passa",
     len(problemas_pdf_numero({"SE": 14.5}, {"SE": 14.5}, {"SE": (10.0, 0.0, 4.5)})) == 0),
    ("cobertura divergente reprova", len(problemas_pdf_numero({"DF": 80.0}, {"DF": 30.0}, {})) == 1),
    ("camadas que não somam a cobertura reprovam",
     len(problemas_pdf_numero({}, {"PR": 29.4}, {"PR": (13.0, 0.0, 3.0)})) == 1),
]


# ───────────────────── semana da imprensa (27/09/2026, §253; §255) ─────────────────────
# Cartões "Esta semana em números": paridade com `data/imprensa/semana.json`, período nos de janela,
# zero ≠ sem coleta, variação só com par (calculada deslocando a janela em sete dias), grupo, fonte,
# modelo declarado, frase sem cláusula de valor zero, peso zero nos índices e data dos atos legível
# nos dois formatos (`dd/mm/aaaa` e ISO; a mistura é nota, normalizá-la é decisão da editoria).
GRUPOS_SEMANA = ("preparacao", "emergencias", "risco_agora", "dinheiro", "saude")
DE_MODELO = ("temperatura_maxima", "qualidade_ar_indice")   # valor de modelo, não de medição


def formatar(valor) -> str:
    """O valor como a página o mostra (vírgula decimal, ponto de milhar): uma função para os dois lados."""
    if valor is None:
        return "sem coleta"
    if isinstance(valor, float):
        return f"{valor:.1f}".replace(".", ",")
    return f"{valor:,}".replace(",", ".") if isinstance(valor, int) else str(valor)


def problemas_semana(r: dict, html: str, leitores: dict) -> list:
    """`r` é o semana.json; `html` a página; `leitores` {arquivo: texto} dos que não podem ler imprensa/."""
    p, cartoes = [], r.get("cartoes") or []
    if not cartoes:
        p.append("semana.json sem nenhum cartão")
    for c in cartoes:
        i, v = c.get("id") or "(sem id)", c.get("valor")
        par, var = c.get("valor_semana_anterior"), c.get("variacao")
        if c.get("sem_coleta") and v is not None:
            p.append(f"{i}: marcado sem_coleta mas com valor {v!r}")
        if not c.get("sem_coleta") and v is None:
            p.append(f"{i}: valor nulo sem declarar sem_coleta — ausência não é zero")
        per = c.get("periodo") or {}
        if ("periodo" in i or i.endswith("_no_periodo")) and not (per.get("ini") and per.get("fim")):
            p.append(f"{i}: cartão de janela sem período declarado")
        if var is not None and par is None:
            p.append(f"{i}: tem variacao sem valor_semana_anterior — variação inventada")
        if par is not None and var is None:
            p.append(f"{i}: tem valor_semana_anterior e não diz a variação")
        if bool(c.get("primeira_medicao")) == (par is not None):
            p.append(f"{i}: primeira_medicao não espelha a existência do par comparável")
        if None not in (var, v, par) and var != v - par:
            p.append(f"{i}: a variação não fecha com os dois valores do cartão")
        if c.get("grupo") not in GRUPOS_SEMANA:
            p.append(f"{i}: grupo ausente ou fora dos cinco aprovados")
        if i in DE_MODELO and not c.get("sem_coleta"):
            texto = f"{c.get('nota') or ''} {c.get('fonte') or ''}".lower()
            if not any(t in texto for t in ("previsão", "estimativ", "modelo", "cams", "escala")):
                p.append(f"{i}: cartão de modelo sem dizer que é previsão ou estimativa")
        if not c.get("fonte"):
            p.append(f"{i}: sem fonte")
        # Paridade, não ausência: o fallback estático escreve o número no HTML; ele tem de ser o do dado.
        achado = re.search(rf'data-imprensa="{re.escape(str(c.get("id")))}"[^>]*>([^<]*)<', html)
        na_pagina = achado.group(1).strip() if achado else ""
        esperado = "sem coleta" if c.get("sem_coleta") else formatar(v)
        if na_pagina not in ("", "—", esperado):
            p.append(f"{i}: a página mostra {na_pagina!r} e o dado diz {esperado!r} — paridade rompida")
    if re.search(r"\b0 [a-zà-ú]", r.get("texto_pronto") or ""):
        p.append("texto_pronto traz cláusula de valor zero — o cartão mostra o zero, a frase não")
    p += [f"{f} lê algo de imprensa/ — os cartões têm peso zero nos índices"
          for f, texto in leitores.items() if "imprensa/" in texto]
    return p


def problemas_atos(datas: list, legivel) -> tuple:
    """(problemas, formatos) das datas de atos_resposta.csv; `legivel(texto)` é o parser tolerante."""
    ruins = [d for d in datas if not legivel(d)]
    formatos = {}
    for d in datas:
        k = "dd/mm/aaaa" if "/" in d else ("ISO" if "-" in d else "outro")
        formatos[k] = formatos.get(k, 0) + 1
    p = [f"dados-abertos/atos_resposta.csv: {len(ruins)} ato(s) com data ilegível pelo parser "
         f"tolerante; exemplo {ruins[0]!r}"] if ruins else []
    return p, formatos


def real_semana():
    import csv
    from gerar_imprensa_semana import data_do_ato
    sem, pagina = RAIZ / "data/imprensa/semana.json", RAIZ / "imprensa.html"
    if not sem.exists():
        return [f"{sem.relative_to(RAIZ)} não existe — rode gerar_imprensa_semana.py"], ""
    leitores = {f: (RAIZ / f).read_text(encoding="utf-8", errors="replace")
                for f in ("recalcular_mare.py", "gerar_monitor_saude.py") if (RAIZ / f).exists()}
    html = pagina.read_text(encoding="utf-8", errors="replace") if pagina.exists() else ""
    falhas, formatos = problemas_semana(_json("data/imprensa/semana.json"), html, leitores), {}
    csv_atos = RAIZ / "dados-abertos/atos_resposta.csv"
    if csv_atos.exists():
        with open(csv_atos, encoding="utf-8") as f:
            p, formatos = problemas_atos([(l.get("data") or "").strip() for l in csv.DictReader(f)],
                                         data_do_ato)
        falhas += p
    return falhas, ("paridade, período, zero ≠ sem coleta, sem variação inventada, frase sem cláusula "
                    f"zero, peso zero nos índices, datas dos atos legíveis (formatos: {formatos})")


def _casos_semana() -> list:
    from datetime import date
    from gerar_imprensa_semana import data_do_ato
    bom = {"id": "x", "valor": 5, "fonte": "f", "grupo": "saude", "primeira_medicao": True}
    com_par = dict(bom, valor_semana_anterior=2, variacao=3, primeira_medicao=False)

    def acusa(texto, *cs, html="", leitores=None, **kw):
        return any(texto in x for x in problemas_semana(dict({"cartoes": list(cs)}, **kw), html,
                                                        leitores or {}))
    return [
        ("cartões sãos não acusam nada",
         problemas_semana({"cartoes": [bom, com_par]}, "", {}) == []),
        ("sem cartão nenhum reprova", acusa("sem nenhum cartão")),
        ("sem_coleta com valor reprova", acusa("sem_coleta mas com valor", dict(bom, sem_coleta=True))),
        ("valor nulo sem sem_coleta reprova", acusa("ausência não é zero", dict(bom, valor=None))),
        ("zero declarado é número, não ausência", not acusa("ausência", dict(bom, valor=0))),
        ("cartão de janela sem período reprova", acusa("sem período", dict(bom, id="dengue_periodo"))),
        ("variação sem par reprova", acusa("variação inventada", dict(bom, variacao=3))),
        ("par sem variação reprova", acusa("não diz a variação", dict(bom, valor_semana_anterior=2))),
        ("primeira_medicao fora do espelho reprova",
         acusa("não espelha", dict(com_par, primeira_medicao=True))),
        ("variação que não fecha reprova", acusa("não fecha", dict(com_par, variacao=9))),
        ("grupo fora dos cinco reprova", acusa("grupo ausente", dict(bom, grupo="outro"))),
        ("cartão de modelo sem dizer que é estimativa reprova",
         acusa("sem dizer", dict(bom, id="temperatura_maxima"))),
        ("cartão de modelo que diz 'previsão' passa",
         not acusa("sem dizer", dict(bom, id="temperatura_maxima", nota="previsão"))),
        ("cartão sem fonte reprova", acusa("sem fonte", dict(bom, fonte=""))),
        ("frase com cláusula de valor zero reprova",
         acusa("cláusula de valor zero", bom, texto_pronto="e 0 planos foram publicados")),
        ("página com número que não é o do dado reprova (paridade)",
         acusa("paridade rompida", bom, html='<b data-imprensa="x">81</b>')),
        ("página com o número do dado passa; placeholder passa",
         not acusa("paridade", bom, html='<b data-imprensa="x">5</b>')
         and not acusa("paridade", bom, html='<b data-imprensa="x">—</b>')),
        ("formatação em português: milhar com ponto, decimal com vírgula",
         formatar(12345) == "12.345" and formatar(3.14) == "3,1" and formatar(None) == "sem coleta"),
        ("peso zero: leitor dos índices que lê imprensa/ reprova",
         acusa("peso zero", bom, leitores={"recalcular_mare.py": "open('data/imprensa/x')"})),
        ("o parser tolerante lê os dois formatos de data",
         data_do_ato("2026-09-15") == date(2026, 9, 15) == data_do_ato("15/09/2026")),
        ("data de ato ilegível reprova e a mistura de formatos é contada",
         (lambda p, f: len(p) == 1 and f == {"ISO": 1, "dd/mm/aaaa": 1, "outro": 1})(
             *problemas_atos(["2026-09-15", "15/09/2026", "x"], data_do_ato))),
    ]


# ─────────────────────── âncoras internas (01/10/2026; JS desde 16/10) ───────────────────────
# `href="pagina.html#ancora"` (e `href="#ancora"`) em página ou script de assets/js/ tem de achar um
# `id` no destino: o navegador acusa arquivo morto, mas abre no topo quando o `id` não existe. A
# (até #1132, a seção "Como os recursos chegam" de "Para gestores" era só ponteiro para o Financiamento.)
PADRAO = ["prefeituras.html", "financiamento.html"]   # o par cuja sincronia dá razão à regra (CODEMAP)
RE_LINK = re.compile(r'href="([^"#]*)#([^"]+)"')
RE_ID = re.compile(r'\sid="([^"]+)"')


def problemas_ancoras(paginas: dict, scripts: dict, ler) -> list:
    """`paginas` {nome.html: texto}, `scripts` {nome.js: texto}, `ler(arquivo)` → texto ou None."""
    ids, falhas = {}, []

    def ids_de(arq):
        if arq not in ids:
            texto = paginas[arq] if arq in paginas else ler(arq)
            ids[arq] = None if texto is None else set(RE_ID.findall(texto))
        return ids[arq]

    def conferir(onde, texto, donos, js):
        for arquivo, ancora in RE_LINK.findall(texto):
            if ancora.startswith(("/", "http")) or ":" in arquivo + ancora or (
                    js and ("${" in arquivo + ancora or "'" in arquivo + ancora)):
                continue          # externo, ou destino montado por variável: não é literal
            destinos = [arquivo] if arquivo else donos
            if arquivo and ids_de(arquivo) is None:
                falhas.append(f"{onde}: aponta para '{arquivo}#{ancora}' e o arquivo não existe")
            elif ancora not in set().union(*(ids_de(d) for d in destinos)):
                falhas.append(f"{onde}: aponta para '{arquivo}#{ancora}' e não existe id='{ancora}' "
                              f"em {', '.join(destinos) or 'página nenhuma que o carregue'}")

    for nome, texto in paginas.items():
        conferir(nome, texto, [nome], False)
    for nome, texto in scripts.items():
        conferir(f"assets/js/{nome}", texto,
                 [p for p, t in paginas.items() if f"assets/js/{nome}" in t], True)
    return falhas


def real_ancoras():
    paginas = {p.name: p.read_text(encoding="utf-8") for p in sorted(RAIZ.glob("*.html"))}
    scripts = {j.name: j.read_text(encoding="utf-8") for j in sorted((RAIZ / "assets/js").glob("*.js"))}
    ler = lambda a: (RAIZ / a).read_text(encoding="utf-8") if (RAIZ / a).is_file() else None
    return (problemas_ancoras(paginas, scripts, ler),
            f"toda âncora citada nas {len(paginas)} páginas e nos scripts existe no destino")


def _casos_ancoras() -> list:
    pg = {"a.html": '<a href="b.html#x">1</a><a href="#y">2</a><i id="y"></i>',
          "b.html": '<p id="x"></p><script src="assets/js/s.js">'}
    nao = lambda a: None
    em_pagina = lambda html: problemas_ancoras(dict(pg, **{"c.html": html}), {}, nao)
    em_js = lambda js: problemas_ancoras(pg, {"s.js": js}, nao)
    citadas = {a for arq, a in RE_LINK.findall((RAIZ / "prefeituras.html").read_text(encoding="utf-8"))
               if arq == "financiamento.html"}
    return [
        ("âncoras que existem passam", problemas_ancoras(pg, {}, nao) == []),
        ("âncora para id inexistente reprova", len(em_pagina('<a href="b.html#nao">x</a>')) == 1),
        ("âncora da própria página sem id reprova", len(em_pagina('<a href="#nao">x</a>')) == 1),
        ("arquivo inexistente reprova", len(em_pagina('<a href="z.html#x">x</a>')) == 1),
        ("link externo com fragmento não é cobrado",
         em_pagina('<a href="https://e.com/p#q">x</a><a href="mailto:a@b#c">y</a>') == []),
        ("link montado em JS reprova se o id não existe na página que o carrega",
         len(em_js('h=`<a href="#nao-existe">x</a>`')) == 1),
        ("link do JS com id que existe na página que o carrega passa", em_js('<a href="#x">') == []),
        ("destino montado por variável não é literal", em_js('<a href="#${id}">') == []),
        ("toda âncora que o Para gestores cita no Financiamento existe no Financiamento (#1132 tirou a seção ponteiro)",
         citadas <= set(RE_ID.findall((RAIZ / "financiamento.html").read_text(encoding="utf-8")))),
        ("o link do cartão da cidade é lido no JS",
         ("", "formulario") in RE_LINK.findall((RAIZ / "assets/js/index.js").read_text(encoding="utf-8"))),
    ]


# ───────────── paridade da cobertura do Querido Diário (27/09/2026, §256; 01/10 e 28/09) ─────────────
# `data/cobertura_qd.json` e `data/verificacao_resumo.json` contam a mesma coisa — quantos municípios
# têm diário indexado — e o número entra no preprint como limitação quantificada: divergência seria
# duas afirmações incompatíveis. Compara acervo com acervo: indexados = lidos + indexados sem leitura
# (`cobertura_indefinida`); indefinido (`None`) nunca é `false`; a partição dos indexados no resumo
# tem TRÊS parcelas desde o §280 (com_mencao + coberto_sem_mencao + sem_edicao_no_periodo).
def contar_qd(cobertura: dict) -> dict:
    municipios = (cobertura or {}).get("municipios") or {}
    valores = [r.get("cobertura_qd") if isinstance(r, dict) else r for r in municipios.values()]
    return {"indexados": sum(v is True for v in valores), "nao_indexados": sum(v is False for v in valores),
            "indefinidos": sum(v is not True and v is not False for v in valores), "total": len(municipios)}


def problemas_paridade(cobertura: dict, resumo: dict) -> list:
    c, v = contar_qd(cobertura), (resumo or {}).get("varredura_diarios") or {}
    if not c["total"]:
        return ["data/cobertura_qd.json sem municípios"]
    if not v:
        return ["data/verificacao_resumo.json sem o bloco varredura_diarios"]
    p, lidos, sem_leitura = [], v.get("indexados"), v.get("cobertura_indefinida") or 0
    if lidos is not None and c["indexados"] != lidos + sem_leitura:
        p.append(f"indexados divergem: cobertura_qd.json conta {c['indexados']} e o resumo declara "
                 f"{lidos} lido(s) mais {sem_leitura} indexado(s) sem leitura, que somam {lidos + sem_leitura}")
    soma = c["indexados"] + c["nao_indexados"] + c["indefinidos"]
    if soma != c["total"]:
        p.append(f"as três classes somam {soma} e o arquivo tem {c['total']} municípios")
    if v.get("total") is not None and c["total"] != v["total"]:
        p.append(f"total de municípios diverge: cobertura_qd.json {c['total']} × "
                 f"verificacao_resumo.json {v['total']}")
    if v.get("sem_cobertura_qd") is not None and c["nao_indexados"] != v["sem_cobertura_qd"]:
        p.append(f"não indexados divergem: cobertura_qd.json conta {c['nao_indexados']} e "
                 f"verificacao_resumo.json declara {v['sem_cobertura_qd']}")
    com, sem, vazio = v.get("com_mencao"), v.get("coberto_sem_mencao"), v.get("sem_edicao_no_periodo")
    if None not in (com, sem, vazio):
        if com + sem + vazio != v.get("indexados"):
            p.append(f"no resumo, com_mencao {com} + coberto_sem_mencao {sem} + sem_edicao_no_periodo "
                     f"{vazio} = {com + sem + vazio}, que não é indexados {v.get('indexados')}")
    elif com is not None and sem is not None:
        p.append("o resumo traz com_mencao e coberto_sem_mencao sem sem_edicao_no_periodo — a partição "
                 "dos indexados tem três parcelas desde o §280; sem a terceira, os municípios com diário "
                 "indexado e nenhuma edição na janela voltam a ser contados como tendo menção")
    if c["indexados"] == 0:
        p.append("nenhum município indexado — 5.571 em false é falha de coleta, não um fato; confira "
                 "se a rotina que preenche cobertura_qd.json rodou")
    return p


def real_paridade():
    arqs = [RAIZ / "data/cobertura_qd.json", RAIZ / "data/verificacao_resumo.json"]
    if falta := [str(a.relative_to(RAIZ)) for a in arqs if not a.exists()]:
        return [f"arquivo ausente: {', '.join(falta)}"], ""
    cobertura, resumo = (json.loads(a.read_text(encoding="utf-8")) for a in arqs)
    c = contar_qd(cobertura)
    return (problemas_paridade(cobertura, resumo),
            f"{c['indexados']} município(s) com diário indexado nos dois arquivos ({c['nao_indexados']} "
            f"não indexados, {c['indefinidos']} indefinidos, total {c['total']})")


def _cob(t, f, n):
    ms = [True] * t + [False] * f + [None] * n
    return {"municipios": {str(i): {"cobertura_qd": x} for i, x in enumerate(ms)}}


CASOS_PARIDADE = [
    ("o estado real de 28/09 passa: 527 / 5041 / 3 contra indexados 527",
     problemas_paridade(_cob(527, 5041, 3), {"varredura_diarios": dict(
         indexados=527, total=5571, sem_cobertura_qd=5041, com_mencao=260, coberto_sem_mencao=211,
         sem_edicao_no_periodo=56)}) == []),
    ("indexados divergentes reprovam",
     any("indexados divergem" in x for x in problemas_paridade(
         _cob(500, 5068, 3), {"varredura_diarios": dict(indexados=527, total=5571)}))),
    ("zero indexado reprova, mesmo com os dois arquivos de acordo",
     any("nenhum município indexado" in x for x in problemas_paridade(
         _cob(0, 5571, 0), {"varredura_diarios": dict(indexados=0, total=5571, sem_cobertura_qd=5571)}))),
    ("não indexados divergentes reprovam",
     any("não indexados divergem" in x for x in problemas_paridade(
         _cob(527, 5041, 3), {"varredura_diarios": dict(indexados=527, total=5571, sem_cobertura_qd=5000)}))),
    ("partição interna do resumo que não fecha reprova",
     any("não é indexados" in x for x in problemas_paridade(
         _cob(527, 5041, 3), {"varredura_diarios": dict(indexados=527, total=5571, com_mencao=300,
                                                        coberto_sem_mencao=180, sem_edicao_no_periodo=56)}))),
    ("partição de DUAS parcelas reprova, mesmo fechando a soma (o defeito do §280)",
     any("três parcelas" in x for x in problemas_paridade(
         _cob(527, 5041, 3), {"varredura_diarios": dict(indexados=527, total=5571, sem_cobertura_qd=5041,
                                                        com_mencao=347, coberto_sem_mencao=180)}))),
    ("total divergente reprova",
     any("total de municípios diverge" in x for x in problemas_paridade(
         _cob(527, 5041, 3), {"varredura_diarios": dict(indexados=527, total=9999)}))),
    ("indefinido é contado à parte, nunca como não indexado",
     (lambda c: c["indefinidos"] == 5 and c["nao_indexados"] == 20)(contar_qd(_cob(10, 20, 5)))),
]


# ─────────────── log de buscas só cresce (28/09/2026, item 4; esquema A6-27) ───────────────
# Marca d'água em `data/log_buscas_marca.json`: o total e cada mês nunca encolhem (a união por
# conteúdo de 23/09 apagou quase 3.000 execuções sem aviso); linha de JSONL inválida é dado perdido;
# toda execução tem `data` ISO e a primeira palavra de `decisao` no vocabulário (houve escrita por
# fora de `coletores_base.log_busca`: decisão em prosa e data dd/mm/aaaa). Atualizar a marca depois
# de crescer: `python3 scripts/verificar_regras_de_dado.py --marcar-log`.
MARCA_LOG = RAIZ / "data" / "log_buscas_marca.json"


def contar_log(doc: dict) -> tuple:
    execucoes = doc.get("execucoes") or []
    por_mes = {}
    for e in execucoes:
        mes = str(e.get("data") or "")[:7] or "sem-data"
        por_mes[mes] = por_mes.get(mes, 0) + 1
    return len(execucoes), por_mes, int(doc.get("linhas_invalidas") or 0)


def problemas_log(total: int, por_mes: dict, invalidas: int, marca: dict) -> list:
    marca_total = int((marca or {}).get("total") or 0)
    falhas = [f"o log ENCOLHEU: {total} execuções contra {marca_total} da marca d'água "
              f"({marca_total - total} a menos). Log é append-only."] if total < marca_total else []
    falhas += [f"o mês {mes} encolheu: {por_mes.get(mes, 0)} contra {n} da marca d'água"
               for mes, n in sorted(((marca or {}).get("por_mes") or {}).items())
               if int(por_mes.get(mes, 0)) < int(n)]
    if invalidas:
        falhas.append(f"{invalidas} linha(s) inválida(s) no JSONL — linha perdida é dado perdido")
    return falhas


def problemas_log_esquema(log: dict, vocabulario) -> list:
    fora = []
    for i, e in enumerate((log or {}).get("execucoes") or []):
        data, dec = str(e.get("data") or ""), str(e.get("decisao") or "")
        if not RE_ISO.fullmatch(data):
            fora.append(f"execução {i} ({e.get('canal')}): data fora de AAAA-MM-DD: {data!r}")
        if dec.split(" ")[0] not in vocabulario:
            fora.append(f"execução {i} ({e.get('canal')}): decisão fora do vocabulário: {dec[:60]!r}")
    return fora


def real_log():
    from coletores_base import DECISOES_LOG, ler_log
    log = ler_log()
    total, por_mes, invalidas = contar_log(log)
    marca = json.loads(MARCA_LOG.read_text(encoding="utf-8")) if MARCA_LOG.exists() else {}
    return (problemas_log(total, por_mes, invalidas, marca) + problemas_log_esquema(log, DECISOES_LOG)[:20],
            f"{total} execução(ões) em {len(por_mes)} mês(es), nenhuma perdida (marca d'água: "
            f"{int(marca.get('total') or 0)}), data ISO e decisão do vocabulário")


def marcar_log() -> int:
    from coletores_base import gravar_em, ler_log
    total, por_mes, _ = contar_log(ler_log())
    antes = json.loads(MARCA_LOG.read_text(encoding="utf-8")) if MARCA_LOG.exists() else {}
    meses = set(por_mes) | set(antes.get("por_mes") or {})
    nova = {"_governanca": ("Marca d'água do log append-only (item 4, 28/09/2026): o maior total já "
                            "visto, e por mês. O portão reprova se a contagem encolher."),
            "total": max(total, int(antes.get("total") or 0)),
            "por_mes": {m: max(por_mes.get(m, 0), int((antes.get("por_mes") or {}).get(m, 0))) for m in meses}}
    gravar_em(MARCA_LOG, nova)
    print(f"✓ marca d'água em {nova['total']} execução(ões), {len(nova['por_mes'])} mês(es)")
    return 0


_MARCA = {"total": 100, "por_mes": {"2026-08": 40, "2026-09": 60}}
_VOCAB = ("registro", "pista", "consultado", "nada")
CASOS_LOG = [
    ("crescer passa", problemas_log(120, {"2026-08": 40, "2026-09": 80}, 0, _MARCA) == []),
    ("ficar igual passa", problemas_log(100, {"2026-08": 40, "2026-09": 60}, 0, _MARCA) == []),
    ("encolher o total reprova e diz quantas a menos",
     (lambda f: any("ENCOLHEU" in x and "10 a menos" in x for x in f))(
         problemas_log(90, {"2026-08": 40, "2026-09": 50}, 0, _MARCA))),
    ("mês que encolhe reprova mesmo com o total crescendo",
     any("2026-08 encolheu" in x for x in problemas_log(120, {"2026-08": 30, "2026-09": 90}, 0, _MARCA))),
    ("linha inválida reprova",
     any("inválida" in x for x in problemas_log(100, {"2026-08": 40, "2026-09": 60}, 1, _MARCA))),
    ("sem marca d'água nada reprova (primeira execução)", problemas_log(10, {"2026-09": 10}, 0, {}) == []),
    ("mês novo não reprova",
     problemas_log(101, {"2026-08": 40, "2026-09": 60, "2026-10": 1}, 0, _MARCA) == []),
    ("conta total, meses e inválidas; data ausente vira sem-data",
     contar_log({"execucoes": [{"data": "2026-09-01"}, {"data": "2026-08-31"}, {"data": None}],
                 "linhas_invalidas": 2}) == (3, {"2026-09": 1, "2026-08": 1, "sem-data": 1}, 2)),
    ("esquema: log no esquema passa",
     problemas_log_esquema({"execucoes": [{"data": "2026-10-12", "decisao": "pista"},
                                          {"data": "2026-10-12", "decisao": "nada localizado"}]}, _VOCAB) == []),
    ("esquema: data dd/mm/aaaa reprova",
     len(problemas_log_esquema({"execucoes": [{"data": "28/09/2026", "decisao": "pista"}]}, _VOCAB)) == 1),
    ("esquema: decisão em prosa reprova",
     len(problemas_log_esquema({"execucoes": [{"data": "2026-08-27", "decisao": "+6 registros"}]}, _VOCAB)) == 1),
    ("esquema: log vazio passa", problemas_log_esquema({}, _VOCAB) == []),
]


# ───────────────────────────── executor ─────────────────────────────
# (nome, barra a publicação, confere o disco)
REGRAS = [("ausencia", False, real_ausencia), ("rotulo", False, real_rotulo),
          ("camada", True, real_camada), ("esquema", True, real_esquema),
          ("proveniencia", False, real_proveniencia), ("redes", False, real_redes),
          ("imprensa", False, real_imprensa), ("financiamento", False, real_financiamento),
          ("versao", False, real_versao), ("pdf", False, real_pdf),
          ("semana", False, real_semana), ("ancoras", False, real_ancoras),
          ("paridade_qd", False, real_paridade), ("log", False, real_log)]


def autoteste() -> int:
    casos = [(f"{n}: {r}", ok) for n, cs in (("ausencia", CASOS_AUSENCIA), ("rotulo", CASOS_ROTULO),
                                             ("camada", CASOS_CAMADA), ("esquema", CASOS_ESQUEMA),
                                             ("proveniencia", CASOS_PROVENIENCIA),
                                             ("redes", _casos_redes()), ("imprensa", CASOS_IMPRENSA),
                                             ("financiamento", CASOS_FINANCIAMENTO),
                                             ("versao", CASOS_VERSAO), ("pdf", CASOS_PDF),
                                             ("semana", _casos_semana()),
                                             ("ancoras", _casos_ancoras()),
                                             ("paridade_qd", CASOS_PARIDADE), ("log", CASOS_LOG))
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
    if "--marcar-log" in sys.argv:
        return marcar_log()
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
