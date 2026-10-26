#!/usr/bin/env python3
"""
buscador2.py — as regras da busca de pistas (Buscador 2, 26/10/2026)
=====================================================================
Pedido da editoria (26/10/2026): reconstruir a busca de pistas com o que as amostras de 40, 100 e
500 julgamentos mediram em todas as 31.735 decisões. Handover: `robo-registro/notas/
HANDOVER_BUSCADOR2_26-10-2026.md`. O defeito maior não era o juiz: só 3.496 decisões chegaram a ler
um documento. A busca entregava redirecionador, página inicial, domínio de empresa e o município
errado.

Cada regra vive aqui uma vez, e os três lugares que buscam a usam em vez de copiá-la:
  · `scripts/pistas.py` (a porta da fila) — B1, B2, B3, B8 e B11 na entrada, para todo coletor;
  · `seguir_pistas.py` (o seguidor) — B4, B5, B6, B7, B9 e B10 sobre o que já está na fila;
  · `monitorar_busca_web.py` — as consultas do B1.

| regra | o que faz aqui |
|---|---|
| B1  | consulta por UF com termos em português e `site:<uf>.gov.br`; rótulo de setor nunca é município |
| B2  | redirecionador vira a URL final ou recusa "redirecionamento não resolvido" |
| B3  | entrada só de domínio do município, da UF, federal de lista fechada, diário oficial ou QD certo |
| B4  | página oficial que não é documento: um nível no mesmo domínio, só PDF/ato com termo de plano |
| B5  | pasta do SharePoint da Casa Militar/RS: nova tentativa noutra noite, até 3; falha vira lacuna datada |
| B6  | prioridade: nível A, depois domínio de prefeitura com termo de plano no caminho |
| B7  | notícia oficial que nomeia plano: `site:<domínio> "<plano citado>"` |
| B8  | par município–URL conferido: domínio de outro ente ou de outra UF cai, com motivo |
| B9  | página com menos de 200 caracteres: mapa do site e links de PDF; nada → lacuna datada |
| B10 | documento oficial com termo de plano no nome volta à fila noutra noite (até 3, intervalo crescente) |
| B11 | uma pista por URL normalizada; repetição soma contagem, não pista |

O que este módulo NÃO faz: julgar (é o juiz), pontuar, decidir categoria ou contornar recusa. Login,
captcha, 401/403/429/451 e muro de robô servido com 200 são recusa (`coletores_base.buscar` levanta).

USO   python3 buscador2.py --autoteste
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import unicodedata
import urllib.parse

RAIZ = pathlib.Path(__file__).resolve().parent

# ---------------------------------------------------------------------------------------- comum
def sem_acento(s) -> str:
    bruto = unicodedata.normalize("NFKD", str(s or "").lower())
    return "".join(c for c in bruto if not unicodedata.combining(c))


def slug(s) -> str:
    """Só letras e dígitos, sem acento: "São José do Rio Preto" → "saojosedoriopreto"."""
    return re.sub(r"[^a-z0-9]", "", sem_acento(s))


def host_de(url) -> str:
    h = (urllib.parse.urlsplit(str(url or "").strip()).hostname or "").lower().rstrip(".")
    return h[4:] if h.startswith("www.") else h


TERMOS_DE_PLANO = ("plano de contingencia", "plano municipal de contingencia", "plancon",
                   "plano de protecao e defesa civil", "plano municipal de protecao",
                   "plano de acao", "plano preventivo", "plano de enfrentamento",
                   "plano de resposta", "contingencia")
EXTENSOES_DE_DOCUMENTO = (".pdf", ".doc", ".docx", ".odt", ".rtf")
RE_CAMINHO_DE_ATO = re.compile(r"/(?:decreto|decretos|lei|leis|portaria|portarias|atos?|legislacao)"
                               r"(?:[/_-]|$)", re.I)


def tem_termo_de_plano(*textos) -> bool:
    t = " ".join(sem_acento(urllib.parse.unquote(str(x or ""))) for x in textos)
    t = re.sub(r"[-_+./]", " ", t)
    t = re.sub(r"\s+", " ", t)
    return any(termo in t for termo in TERMOS_DE_PLANO)


def e_documento(url) -> bool:
    caminho = urllib.parse.urlsplit(str(url or "")).path.lower()
    return caminho.endswith(EXTENSOES_DE_DOCUMENTO)


# ------------------------------------------------------------------------------------- B11 (URL)
PARAMETROS_DE_RASTREIO = ("utm_", "fbclid", "gclid", "mc_cid", "mc_eid", "ref", "source", "amp")


def url_normalizada(url) -> str:
    """A identidade da URL para deduplicar (B11). Função pura.

    Host em minúsculas e sem `www.`, sem fragmento, sem parâmetro de rastreio, parâmetros em
    ordem, barra final fora, `http`/`https` iguais. A anvisa ×5, o saude.portal.ap ×5 e o Taió ×10
    eram a mesma página com enfeite diferente no endereço."""
    bruto = str(url or "").strip()
    if not bruto:
        return ""
    p = urllib.parse.urlsplit(bruto)
    host = host_de(bruto)
    if p.port and p.port not in (80, 443):
        host = f"{host}:{p.port}"
    caminho = urllib.parse.unquote(p.path or "/")
    caminho = re.sub(r"/{2,}", "/", caminho)
    if len(caminho) > 1:
        caminho = caminho.rstrip("/")
    pares = [(k, v) for k, v in urllib.parse.parse_qsl(p.query, keep_blank_values=True)
             if not any(k.lower().startswith(r) for r in PARAMETROS_DE_RASTREIO)]
    consulta = urllib.parse.urlencode(sorted(pares))
    return f"{host}{caminho}" + (f"?{consulta}" if consulta else "")


# ------------------------------------------------------------------------------------------- B1
ROTULOS_DE_SETOR = {"defesa_civil", "saude", "defesacivil", "defesa civil", "saúde"}


def rotulo_no_lugar_do_municipio(nome) -> bool:
    """O campo `municipio` traz rótulo de setor ("defesa_civil", "saude") e não nome de município?

    3.209 pares de lixo (Amazon, Southwest, fandom) nasceram de consultas estaduais com o rótulo no
    lugar do município: "defesa_civil" AC buscava a web inteira."""
    n = str(nome or "").strip().lower()
    return bool(n) and (n in ROTULOS_DE_SETOR or "_" in n or "/" in n)


def consultas_da_uf(uf: str) -> list:
    """A consulta estadual do B1: termos em português + `site:<uf>.gov.br`. [(id, string)]."""
    s = f"site:{str(uf).lower()}.gov.br"
    return [("uf_plancon_defesa_civil", f'"plano de contingência" "defesa civil" {s}'),
            ("uf_plancon_saude", f'"plano de contingência" saúde {s}'),
            ("uf_estiagem_chuvas", f'plano "defesa civil" estiagem OR seca OR "período chuvoso" {s}')]


def consultas_do_municipio(nome: str, uf: str) -> list:
    """A cascata municipal do B1: o nome entre aspas, termos em português e `site:<uf>.gov.br`,
    que cobre o domínio da prefeitura (`<município>.<uf>.gov.br`) e os da UF. [(id, string)]."""
    s = f"site:{str(uf).lower()}.gov.br"
    return [("plancon", f'"{nome}" "plano de contingência" {s}'),
            ("periodo_ou_seca", f'"{nome}" plano "período chuvoso" OR estiagem OR seca {s}'),
            ("siglas_e_variantes", f'"{nome}" PLANCON OR "plano de ação" OR "plano de enfrentamento" {s}')]


# ------------------------------------------------------------------------------------- B3 + B8
# Lista FECHADA (usada para admitir; o que não está nela cai com motivo).
FEDERAIS = (("gov.br", "/mdr"), ("s2id.mi.gov.br", ""), ("s2id.mdr.gov.br", ""),
            ("in.gov.br", ""), ("pesquisa.in.gov.br", ""))
# Plataformas oficiais de diário municipal (as mesmas do juiz, etapa 0): publicação oficial do ente.
PLATAFORMAS_DE_DIARIO = ("diariomunicipal.com.br", "sigpub.com.br", "dosp.com.br")
QUERIDO_DIARIO = ("queridodiario.ok.org.br", "data.queridodiario.ok.org.br")
# Repositório estadual de planos municipais (J19): o arquivo é do município, a pasta é da UF.
REPOSITORIOS_ESTADUAIS = {
    "RS": ("rsgovbr-my.sharepoint.com/personal/casa-militar_casamilitar_rs_gov_br", "casamilitar-rs.com.br/pdfs/"),
}
PREFIXOS_DE_ENTE = ("prefeiturademunicipalde", "prefeituramunicipalde", "prefeiturade", "prefeitura",
                    "camaramunicipalde", "camarade", "camara", "pm", "cm")
# Rótulo de órgão estadual que coincide com nome de município ("saude.ba.gov.br" × Saúde/BA): nunca
# identifica o ente. Lista fechada; o que não está nela é lido como possível nome de município.
ROTULOS_DE_ORGAO = {"saude", "educacao", "defesacivil", "sedec", "cultura", "turismo", "fazenda",
                    "agricultura", "seguranca", "transparencia", "portal", "casacivil", "meioambiente",
                    "planejamento", "governo", "esporte", "trabalho", "justica", "agua", "agenersa"}
RE_DOMINIO_DE_UF = re.compile(r"^(?:(?P<sub>.+)\.)?(?P<uf>[a-z]{2})\.(?:gov|leg)\.br$")

_SLUGS = None


def slugs_por_uf() -> dict:
    """{UF: {slug: nome}} dos 5.571 municípios, de `data/municipios_ibge_referencia.json`. Só leitura."""
    global _SLUGS
    if _SLUGS is None:
        _SLUGS = {}
        try:
            ref = json.loads((RAIZ / "data" / "municipios_ibge_referencia.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            ref = []
        for m in ref:
            _SLUGS.setdefault(m["uf"], {})[slug(m["nome"])] = m["nome"]
        _SLUGS["_por_ibge"] = {str(m["codigo_ibge"]).zfill(7): (m["nome"], m["uf"]) for m in ref}
    return _SLUGS


def ente_do_rotulo(rotulo: str, uf: str, slugs: dict) -> str:
    """O município que o rótulo de host nomeia ("pmtaio" → "Taió"), ou "". Função pura."""
    s = slug(rotulo)
    if s in ROTULOS_DE_ORGAO:
        return ""
    for pre in PREFIXOS_DE_ENTE:
        if s.startswith(pre) and len(s) > len(pre) + 2:
            s = s[len(pre):]
            break
    if s.endswith(str(uf).lower()) and s[:-2] in slugs:
        s = s[:-2]
    return slugs.get(s, "")


def classe_de_entrada(url: str, ibge: str = "", uf: str = "", nome: str = "", slugs: dict = None) -> tuple:
    """(classe, motivo). Classe "" é recusa, e o motivo diz por quê (B3, B8). Função pura.

    Classes admitidas: municipio · uf · federal · diario_oficial · querido_diario. O par
    município–URL é conferido: domínio de outro município ou de outra UF cai antes de baixar."""
    slugs = slugs if slugs is not None else slugs_por_uf()
    bruto = str(url or "").strip()
    host = host_de(bruto)
    uf = str(uf or "").upper()
    if not host:
        return "", "sem endereço"
    if eh_redirecionador(bruto):
        return "", "redirecionamento não resolvido"
    caminho = urllib.parse.urlsplit(bruto).path
    if host in QUERIDO_DIARIO:
        cod = caminho.strip("/").split("/")[0]
        if ibge and cod.isdigit() and len(cod) == 7 and cod != str(ibge):
            return "", f"Querido Diário de outro município (código IBGE {cod})"
        return ("querido_diario", "") if cod.isdigit() else ("", "Querido Diário sem código IBGE no endereço")
    for h, pre in FEDERAIS:
        if host == h and caminho.startswith(pre):
            return "federal", ""
    if any(host == d or host.endswith("." + d) for d in PLATAFORMAS_DE_DIARIO):
        return "diario_oficial", ""
    alvo_bruto = (host + caminho).lower()
    for uf_rep, padroes in REPOSITORIOS_ESTADUAIS.items():
        if any(p.lower() in alvo_bruto for p in padroes):
            if uf and uf != uf_rep:
                return "", f"repositório estadual de outra UF ({uf_rep})"
            return "uf", ""
    m = RE_DOMINIO_DE_UF.match(host)
    if m:
        uf_host = m.group("uf").upper()
        if uf and uf_host != uf:
            return "", f"domínio de outra UF ({uf_host}: {host})"
        rotulos = [r for r in (m.group("sub") or "").split(".") if r]
        do_uf = slugs.get(uf_host, {})
        meu = slug(nome) if nome else ""
        for r in reversed(rotulos):
            ente = ente_do_rotulo(r, uf_host, do_uf)
            if not ente:
                continue
            if meu and slug(ente) == meu:
                return "municipio", ""
            return "", f"domínio de outro ente ({ente}/{uf_host}: {host})"
        return "uf", ""
    if host.endswith((".gov.br", ".leg.br")):
        return "", f"domínio público fora da lista fechada ({host})"
    return "", f"domínio não oficial ({host})"


def classe_da_pista(pista: dict, slugs: dict = None) -> tuple:
    """`classe_de_entrada` a partir da pista como a porta a vê (alvo IBGE ou UF)."""
    slugs = slugs if slugs is not None else slugs_por_uf()
    p = pista or {}
    alvo = str(p.get("alvo") or p.get("ibge") or "")
    nome, uf = p.get("municipio") or "", p.get("uf") or ""
    if alvo.isdigit() and len(alvo) == 7:
        nome, uf = slugs.get("_por_ibge", {}).get(alvo, (nome, uf))
    elif len(alvo) == 2 and alvo.isalpha():
        nome, uf = "", alvo
    return classe_de_entrada(p.get("url_final") or p.get("url"), alvo if len(alvo) == 7 else "",
                             uf, nome, slugs)


# ------------------------------------------------------------------------------------------- B2
REDIRECIONADORES = ("news.google.com", "news.url.google.com", "/rss/articles/", "feedproxy.google.com",
                    "google.com/url")


def eh_redirecionador(url) -> bool:
    return any(r in str(url or "") for r in REDIRECIONADORES)


def resolver(url: str, abrir=None, veiculo=None, titulo=None, buscar_web=None) -> tuple:
    """(url_final | None, como). Delega a `verificar_pista_imprensa.resolver_redirecionamento`, que
    já tem os três degraus (URL embutida, redirecionamento HTTP, busca no veículo) e o motivo."""
    from verificar_pista_imprensa import resolver_redirecionamento
    if not eh_redirecionador(url):
        return url, "nao_era_redirecionador"
    final, como = resolver_redirecionamento(url, abrir=abrir, tentativas=2, veiculo=veiculo,
                                            titulo=titulo, buscar_web=buscar_web)
    if final and eh_redirecionador(final):
        return None, "redirecionamento_nao_resolvido"
    return final, como


# ------------------------------------------------------------------------------------------- B4
RE_LINK = re.compile(r'<a\s[^>]*href=["\']([^"\'#]+)["\'][^>]*>(.*?)</a>', re.I | re.S)


def limpo(html) -> str:
    sem = re.sub(r"<script.*?</script>|<style.*?</style>", " ", str(html or ""), flags=re.S | re.I)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", sem)).strip()


def links_de_documento(html: str, url_base: str, limite: int = 8, mesmo_dominio: bool = True) -> list:
    """Os links de PDF ou ato com termo de plano no texto do link ou no nome (B4). [(url, âncora)].

    Um nível só, no mesmo domínio: a página inicial, a carta de serviços, a lista "planos
    municipais" e a notícia oficial não são o documento, mas costumam apontar para ele."""
    base_host = host_de(url_base)
    saida, vistos = [], set()
    for href, texto in RE_LINK.findall(str(html or "")):
        url = urllib.parse.urljoin(url_base, href.strip())
        if not url.startswith("http"):
            continue
        n = url_normalizada(url)
        if n in vistos or n == url_normalizada(url_base):
            continue
        if mesmo_dominio and host_de(url) != base_host:
            continue
        ancora = limpo(texto)[:200]
        nome_do_arquivo = urllib.parse.urlsplit(url).path.rsplit("/", 1)[-1]
        if not (e_documento(url) or RE_CAMINHO_DE_ATO.search(urllib.parse.urlsplit(url).path)):
            continue
        if not tem_termo_de_plano(ancora, nome_do_arquivo):
            continue
        vistos.add(n)
        saida.append((url, ancora))
        if len(saida) >= limite:
            break
    return saida


# ------------------------------------------------------------------------------------- B5 + B10
TENTATIVAS_DO_BUSCADOR = 3
INTERVALO_DAS_TENTATIVAS = (1, 3)   # dias: a 2ª uma noite depois, a 3ª três noites depois


def proxima_tentativa(n_feitas: int, hoje):
    """A data da próxima tentativa de leitura, ou None quando as três se esgotaram. Função pura."""
    from datetime import timedelta
    if n_feitas >= TENTATIVAS_DO_BUSCADOR:
        return None
    return hoje + timedelta(days=INTERVALO_DAS_TENTATIVAS[min(max(n_feitas, 1), len(INTERVALO_DAS_TENTATIVAS)) - 1])


def e_sharepoint_rs(url) -> bool:
    return REPOSITORIOS_ESTADUAIS["RS"][0] in str(url or "").lower()


def volta_a_fila(pista: dict) -> bool:
    """O documento que não se leu volta noutra noite? (B5, B10) Função pura.

    Volta o documento oficial com termo de plano no nome e o arquivo da pasta do RS; a notícia e a
    página genérica não. "Documento não obtido nesta tentativa" deixa de ser final: Blumenau,
    Recife, Encantado e Laurentino tinham plano publicado e caíram numa noite ruim."""
    url = str(pista.get("url_final") or pista.get("url") or "")
    if e_sharepoint_rs(url):
        return True
    classe, _ = classe_da_pista(pista)
    nome_do_arquivo = urllib.parse.urlsplit(url).path.rsplit("/", 1)[-1]
    return bool(classe) and tem_termo_de_plano(nome_do_arquivo, pista.get("titulo"))


def lacuna_datada(o_que: str, data_iso: str) -> str:
    """O texto da lacuna, com data e nunca "não existe" (teto: não localizamos até a data)."""
    return f"{o_que} até {data_iso}"


# ------------------------------------------------------------------------------------------- B6
def prioridade(pista: dict) -> tuple:
    """Chave de ordenação (menor primeiro): nível A; depois domínio de prefeitura com termo de plano
    no caminho; depois o resto pelo nível. Função pura."""
    p = pista or {}
    nivel = str(p.get("nivel") or p.get("nivel_confianca") or "C").upper()
    url = str(p.get("url_final") or p.get("url") or "")
    if nivel == "A":
        return (0, url)
    classe, _ = classe_da_pista(p)
    if classe == "municipio" and tem_termo_de_plano(urllib.parse.urlsplit(url).path):
        return (1, url)
    return (2 + ("ABC".index(nivel) if nivel in "ABC" else 2), url)


# ------------------------------------------------------------------------------------------- B7
RE_PLANO_CITADO = re.compile(r"(plano\s+(?:municipal\s+)?de\s+conting[êe]ncia[^.;:<>\n]{0,60}|plancon[^.;:<>\n]{0,40})",
                             re.I)


def plano_citado(texto: str) -> str:
    """O nome do plano que a notícia oficial cita ("Plano de Contingência para Estiagem 2026"), ou "". """
    m = RE_PLANO_CITADO.search(str(texto or ""))
    return " ".join(m.group(1).split())[:80].strip(" ,-") if m else ""


def consulta_do_citado(url: str, texto: str) -> str:
    """`site:<domínio> "<plano citado>"` para achar o PDF ou o decreto que a notícia cita (B7)."""
    citado = plano_citado(texto)
    host = host_de(url)
    return f'site:{host} "{citado}"' if citado and host else ""


# ------------------------------------------------------------------------------------------- B9
TEXTO_MINIMO_LEGIVEL = 200


def pagina_legivel(texto: str) -> bool:
    return len(str(texto or "").strip()) >= TEXTO_MINIMO_LEGIVEL


def url_do_mapa_do_site(url: str) -> str:
    p = urllib.parse.urlsplit(str(url or ""))
    return f"{p.scheme or 'https'}://{p.netloc}/sitemap.xml" if p.netloc else ""


def links_do_mapa(xml: str, url_base: str, limite: int = 8) -> list:
    """Documentos com termo de plano no endereço, do `sitemap.xml` do mesmo domínio. [(url, "")]."""
    base = host_de(url_base)
    saida = []
    for loc in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", str(xml or ""), re.I):
        if host_de(loc) == base and tem_termo_de_plano(urllib.parse.urlsplit(loc).path):
            saida.append((loc, ""))
            if len(saida) >= limite:
                break
    return saida


# ---------------------------------------------------------------------------------- o seguimento
def candidatos_da_pagina(pista: dict, corpo: bytes, abrir=None, buscar_web=None, hoje_iso: str = "") -> dict:
    """O que o Buscador 2 tira de UMA página já baixada: {candidatos, via, lacuna}. Rede só por
    `abrir` (mapa do site, B9) e `buscar_web` (B7), ambos injetados.

    Documento (PDF) não se segue: quem o lê é o juiz. Página HTML oficial: B4 (um nível no mesmo
    domínio); ilegível: B9; sem link e citando plano: B7. Notícia de veículo não oficial (rota):
    os links para domínio oficial da pista, em qualquer host — é de onde a matéria tira o ato."""
    url = str(pista.get("url_final") or pista.get("url") or "")
    if not corpo or corpo[:5] == b"%PDF-":
        return {"candidatos": [], "via": "documento", "lacuna": ""}
    html = corpo.decode("utf-8", "replace") if isinstance(corpo, bytes) else str(corpo)
    texto = limpo(html)
    rota = not classe_da_pista(pista)[0]
    if rota:
        links = [(u, a) for u, a in links_de_documento(html, url, mesmo_dominio=False)
                 if classe_da_pista(dict(pista, url_final=u, url=u))[0]]
        return {"candidatos": links, "via": "B2_noticia", "lacuna": ""}
    if not pagina_legivel(texto):
        achados = []
        if abrir is not None:
            try:
                achados = links_do_mapa(abrir(url_do_mapa_do_site(url)).decode("utf-8", "replace"), url)
            except Exception:  # noqa: BLE001 — sem mapa do site, segue para a lacuna
                achados = []
        achados = achados or links_de_documento(html, url)
        if achados:
            return {"candidatos": achados, "via": "B9", "lacuna": ""}
        return {"candidatos": [], "via": "B9", "lacuna": lacuna_datada("página não legível", hoje_iso)}
    links = links_de_documento(html, url)
    if links:
        return {"candidatos": links, "via": "B4", "lacuna": ""}
    q = consulta_do_citado(url, texto)
    if q and buscar_web is not None:
        try:
            res = (buscar_web(q) or {}).get("results") or []
        except Exception:  # noqa: BLE001
            res = []
        achados = [(r.get("url"), (r.get("title") or "")[:200]) for r in res
                   if r.get("url") and host_de(r.get("url")) == host_de(url)
                   and url_normalizada(r.get("url")) != url_normalizada(url)][:4]
        return {"candidatos": achados, "via": "B7", "lacuna": ""}
    return {"candidatos": [], "via": "B4", "lacuna": ""}


# ------------------------------------------------------------------------------------- autoteste
def autoteste() -> int:
    sys.path.insert(0, str(RAIZ / "scripts"))
    from _casos import ok_de
    falhas, contados = [], []
    ok = ok_de(falhas, contados)
    S = {"SC": {"taio": "Taió", "celsoramos": "Celso Ramos", "blumenau": "Blumenau", "itajai": "Itajaí"},
         "ES": {"vitoria": "Vitória", "viana": "Viana"},
         "RS": {"pelotas": "Pelotas", "riodosul": "Rio do Sul"},
         "_por_ibge": {"4217808": ("Taió", "SC"), "4205902": ("Celso Ramos", "SC")}}

    # B1 — consulta por UF, rótulo nunca é município (3.209 pares de lixo)
    ok("B1: rótulo de setor no campo município é reconhecido",
       rotulo_no_lugar_do_municipio("defesa_civil") and rotulo_no_lugar_do_municipio("saude")
       and not rotulo_no_lugar_do_municipio("Taió"))
    ok("B1: consulta por UF em português e restrita a site:<uf>.gov.br",
       all("site:ac.gov.br" in q and ("plano" in q) for _, q in consultas_da_uf("AC")))
    ok("B1: consulta municipal leva o nome entre aspas e site:<uf>.gov.br",
       all('"Taió"' in q and "site:sc.gov.br" in q for _, q in consultas_do_municipio("Taió", "SC")))

    # B2 — Google News aberto ou recusado (21.464 links nunca abertos)
    gn = "https://news.google.com/rss/articles/CBMiAU_yqLopaco?oc=5"
    ok("B2: link do Google News que não resolve é recusa nomeada",
       resolver(gn, abrir=lambda u: gn) == (None, "redirecionamento_nao_resolvido")
       and classe_de_entrada(gn, slugs=S) == ("", "redirecionamento não resolvido"))
    ok("B2: o redirecionamento seguido guarda a URL final",
       resolver(gn, abrir=lambda u: "https://taio.sc.gov.br/plano.pdf")[0] == "https://taio.sc.gov.br/plano.pdf")

    ok("B3: rótulo de órgão estadual não vira município (saude.ba.gov.br × Saúde/BA)",
       classe_de_entrada("https://www5.saude.ba.gov.br/x.pdf", "", "BA", "", {"BA": {"saude": "Saúde"}})[0] == "uf")
    # B3 — só domínio do município, da UF, federal fechado, diário oficial, QD certo (2.031 não oficiais)
    ok("B3: empresa (cristalconsult) cai com motivo",
       classe_de_entrada("https://www.cristalconsult.com.br/plano.pdf", "4217808", "SC", "Taió", S)[1]
       == "domínio não oficial (cristalconsult.com.br)")
    ok("B3: rede social cai (canal de descoberta, nunca documento)",
       classe_de_entrada("https://www.instagram.com/p/x", "4217808", "SC", "Taió", S)[0] == "")
    ok("B3: domínio federal fora da lista (anvisa) cai; MIDR e DOU entram",
       classe_de_entrada("https://pesquisa.anvisa.gov.br/x", "", "SC", "", S)[0] == ""
       and classe_de_entrada("https://www.gov.br/mdr/pt-br/x.pdf", "", "SC", "", S)[0] == "federal"
       and classe_de_entrada("https://www.in.gov.br/web/dou/-/x", "", "SC", "", S)[0] == "federal")
    ok("B3: domínio do município, da UF e diário oficial entram",
       classe_de_entrada("https://taio.sc.gov.br/plano.pdf", "4217808", "SC", "Taió", S)[0] == "municipio"
       and classe_de_entrada("https://www.pmtaio.sc.gov.br/a", "4217808", "SC", "Taió", S)[0] == "municipio"
       and classe_de_entrada("https://defesacivil.sc.gov.br/a.pdf", "4217808", "SC", "Taió", S)[0] == "uf"
       and classe_de_entrada("https://www.diariomunicipal.com.br/fecam/x", "4217808", "SC", "Taió", S)[0]
       == "diario_oficial")
    ok("B3: Querido Diário só do código IBGE certo",
       classe_de_entrada("https://data.queridodiario.ok.org.br/4217808/2026/x.pdf", "4217808", "SC", "Taió", S)[0]
       == "querido_diario"
       and "4205902" in classe_de_entrada("https://data.queridodiario.ok.org.br/4205902/x.pdf",
                                           "4217808", "SC", "Taió", S)[1])

    # B4 — um nível no mesmo domínio, só PDF/ato com termo de plano (3.119 listas)
    html = ('<a href="/arquivos/plano-de-contingencia-2026.pdf">Baixar</a>'
            '<a href="/arquivos/edital-merenda.pdf">Edital</a>'
            '<a href="https://outro.com.br/plancon.pdf">PLANCON</a>'
            '<a href="/decretos/512">Decreto 512 — Plano de Contingência</a>'
            '<a href="/noticias/plano">Plano de contingência</a>')
    achados = [u for u, _ in links_de_documento(html, "https://pelotas.rs.gov.br/defesa-civil")]
    ok("B4: segue só PDF/ato do mesmo domínio com termo de plano",
       achados == ["https://pelotas.rs.gov.br/arquivos/plano-de-contingencia-2026.pdf",
                   "https://pelotas.rs.gov.br/decretos/512"])

    # B5 — SharePoint do RS: três noites, depois lacuna datada (203 não lidos)
    import datetime as _dt
    d0 = _dt.date(2026, 10, 26)
    sp = {"url": "https://rsgovbr-my.sharepoint.com/personal/casa-militar_casamilitar_rs_gov_br/Documents/x.pdf",
          "alvo": "RS", "uf": "RS"}
    ok("B5: arquivo da pasta do RS volta noutra noite, no máximo 3",
       volta_a_fila(sp) and proxima_tentativa(1, d0) == _dt.date(2026, 10, 27)
       and proxima_tentativa(2, d0) == _dt.date(2026, 10, 29) and proxima_tentativa(3, d0) is None
       and lacuna_datada("documento não lido", "2026-10-29") == "documento não lido até 2026-10-29")

    # B6 — nível A primeiro, depois prefeitura com termo de plano no caminho
    fila = [{"url": "https://g1.globo.com/x", "nivel": "C", "alvo": "SC"},
            {"url": "https://taio.sc.gov.br/plano-de-contingencia.pdf", "nivel": "C", "alvo": "4217808"},
            {"url": "https://x.sc.gov.br/a", "nivel": "A", "alvo": "SC"}]
    global _SLUGS
    guardado, _SLUGS = _SLUGS, S
    try:
        ordem = [p["url"] for p in sorted(fila, key=prioridade)]
        ok("B6: nível A, depois domínio de prefeitura com termo de plano, depois o resto",
           ordem == ["https://x.sc.gov.br/a", "https://taio.sc.gov.br/plano-de-contingencia.pdf",
                     "https://g1.globo.com/x"])
        # B7 — notícia oficial que nomeia plano: site:<domínio> + título
        corpo = ("<html><body><h1>Cubatão</h1><p>A prefeitura aprovou o Plano de Contingência para o El Niño "
                 "2026, com comissão própria. " + "texto " * 60 + "</p></body></html>").encode()
        pista = {"url": "https://cubatao.sp.gov.br/noticia/el-nino", "alvo": "SP", "uf": "SP"}
        visto = []
        r = candidatos_da_pagina(pista, corpo, buscar_web=lambda q: (visto.append(q), {"results": [
            {"url": "https://cubatao.sp.gov.br/arquivos/plancon.pdf", "title": "PLANCON"},
            {"url": "https://outro.com/x.pdf"}]})[1])
        ok("B7: notícia oficial que cita plano busca o documento no mesmo domínio",
           r["via"] == "B7" and visto and visto[0].startswith('site:cubatao.sp.gov.br "Plano de Contingência')
           and [u for u, _ in r["candidatos"]] == ["https://cubatao.sp.gov.br/arquivos/plancon.pdf"])
        # B9 — página curta: mapa do site; sem nada, lacuna datada
        curta = b"<html><body>Carregando...</body></html>"
        mapa = (b"<urlset><url><loc>https://riodosul.sc.gov.br/docs/plano-de-contingencia.pdf</loc></url>"
                b"<url><loc>https://riodosul.sc.gov.br/turismo</loc></url></urlset>")
        p9 = {"url": "https://riodosul.sc.gov.br/defesa", "alvo": "SC", "uf": "SC"}
        r9 = candidatos_da_pagina(p9, curta, abrir=lambda u: mapa)
        r9b = candidatos_da_pagina(p9, curta, abrir=lambda u: b"", hoje_iso="2026-10-26")
        ok("B9: página ilegível tenta o mapa do site; sem nada, lacuna datada",
           [u for u, _ in r9["candidatos"]] == ["https://riodosul.sc.gov.br/docs/plano-de-contingencia.pdf"]
           and r9b["lacuna"] == "página não legível até 2026-10-26")
        # B10 — documento oficial com termo de plano volta; página genérica não
        ok("B10: documento oficial com termo de plano no nome volta à fila; notícia não",
           volta_a_fila({"url": "https://blumenau.sc.gov.br/plancon-2026.pdf", "alvo": "4202404", "uf": "SC",
                         "municipio": "Blumenau"})
           and not volta_a_fila({"url": "https://g1.globo.com/plano-de-contingencia", "alvo": "SC"}))
        ok("documento (PDF) não se segue: quem lê é o juiz",
           candidatos_da_pagina(pista, b"%PDF-1.4 ...")["via"] == "documento")
        ok("notícia de veículo (rota): só links para domínio oficial do ente",
           [u for u, _ in candidatos_da_pagina(
               {"url": "https://jornal.com.br/x", "alvo": "4208203", "uf": "SC", "municipio": "Itajaí"},
               b'<a href="https://itajai.sc.gov.br/plano-de-contingencia.pdf">PDF</a>'
               b'<a href="https://jornal.com.br/plancon.pdf">PLANCON</a>')["candidatos"]]
           == ["https://itajai.sc.gov.br/plano-de-contingencia.pdf"])
    finally:
        _SLUGS = guardado

    # B8 — par município–URL conferido (964 de outro ente ou UF)
    ok("B8: domínio de outro município da mesma UF cai, nomeando o ente",
       classe_de_entrada("https://celsoramos.sc.gov.br/plano.pdf", "4217808", "SC", "Taió", S)[1]
       == "domínio de outro ente (Celso Ramos/SC: celsoramos.sc.gov.br)")
    ok("B8: domínio de outra UF cai (Porto Velho para Palmas/TO)",
       classe_de_entrada("https://www.portovelho.ro.gov.br/x.pdf", "1721000", "TO", "Palmas", S)[1]
       .startswith("domínio de outra UF (RO"))
    ok("B8: repositório estadual de outra UF cai",
       classe_de_entrada(sp["url"], "", "SC", "", S)[0] == "")

    # B11 — uma pista por URL normalizada (anvisa ×5, Taió ×10)
    ok("B11: www, http/https, barra final, fragmento e utm não fazem outra URL",
       url_normalizada("http://www.Taio.sc.gov.br/plano/?utm_source=x#topo")
       == url_normalizada("https://taio.sc.gov.br/plano") == "taio.sc.gov.br/plano")
    ok("B11: parâmetro de conteúdo continua distinguindo",
       url_normalizada("https://x.gov.br/a?id=1") != url_normalizada("https://x.gov.br/a?id=2"))

    import dis
    nomes = set()
    for f in (url_normalizada, classe_de_entrada, links_de_documento, prioridade, volta_a_fila,
              consulta_do_citado, links_do_mapa, rotulo_no_lugar_do_municipio):
        nomes |= {i.argval for i in dis.get_instructions(f) if isinstance(i.argval, str)}
    ok("trava: as regras puras não escrevem nem vão à rede",
       not ({"gravar", "gravar_em", "write_text", "urlopen", "buscar", "rejeitar"} & nomes))
    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        sys.exit(autoteste())
    print(__doc__.strip().splitlines()[0])
