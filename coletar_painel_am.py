#!/usr/bin/env python3
"""Coletor do painel Power BI da Defesa Civil do Amazonas (§165, 23/09/2026).

MOTIVAÇÃO (caso real). Em 22/09/2026 a Ouvidoria da Defesa Civil do AM respondeu a um
pedido de LAI sem enviar a lista pedida: indicou um painel Power BI do próprio órgão. O
painel traz os 62 municípios do estado com calha de rio, ano do plano e um ícone de link
para o documento de cada município — exatamente os itens (1) e (2) do pedido. É público e
provavelmente antigo, e nenhuma rodada do robô o encontrou: a tabela é montada em
JavaScript depois do carregamento, então a busca textual recebe só o esqueleto da página.
A falha foi de CAMADA, não de cobertura (§164, sondar_paineis.py e a nota de diagnóstico).

O QUE ESTE SCRIPT FAZ
  1. Manda scripts/renderizar_painel_am.js abrir o sub-painel num navegador real e devolver
     a tabela em bruto (o Node só renderiza e extrai; não decide nada).
  2. Casa cada nome de município com o código IBGE de data/municipios_ibge_referencia.json.
  3. Para cada linha com link: baixa o documento, preserva a evidência e tenta ler do
     PRÓPRIO documento o número e a data do ato.
  4. Escreve o resultado em data/pistas_painel_am.json (fila própria) e registra tudo no
     log v2 e no livro de fontes consultadas.

DECLARADO ≠ DOCUMENTADO (a distinção que dá sentido ao coletor). A tabela do painel é
DECLARAÇÃO DO ESTADO: traz o ano, não traz número nem data do ato. Isso é camada
`declarado`, com o desconto já previsto na metodologia. Só vira `documentado` o município
cujo link ABRIU o documento e cujo ato teve número e data lidos do documento. Ano 2026 não
é prova de antecipação: a régua do ciclo separa antes e depois de 29/06/2026, e sem a data
do ato o município fica em `declarado` — nunca promovido "por ser de 2026".

===========================================================================
TRAVA ABSOLUTA (idêntica à de descobrir_planos.py e sondar_paineis.py):
  1. ESTRUTURAL: nunca escreve em estados.json, saude_uf.json, municipios.json,
     indice.json ou monitor_saude.json (garantido por autoteste que lê o próprio fonte).
  2. DE CAMPO: todo item nasce com "documento_oficial_confirmado": null e
     "promovivel": false.
  3. DE PROCESSO: sai em fila própria, nunca no banco. Promoção é humana (regra R7).
Link que não abre, PDF ilegível ou painel fora do ar = LACUNA DECLARADA (registrar_lacuna),
jamais valor estimado.
===========================================================================

Uso: python3 coletar_painel_am.py [--url URL] [--de-arquivo render.json] [--limite N]
     python3 coletar_painel_am.py --autoteste     (offline, sem rede e sem navegador)
"""
import json
import re
import subprocess
import sys
import time
import unicodedata
from datetime import date

from coletores_base import (RAIZ, buscar, hoje, ler, gravar, log_busca, preservar_evidencia,
                            referencia_ibge, registrar_lacuna, marcar_fonte_consultada,
                            rodar_autoteste, UA)

FILA = "pistas_painel_am.json"
RENDERIZADOR = RAIZ / "scripts" / "renderizar_painel_am.js"

# Sub-painel "Planos de Contingência Municipais" (registrado em data/pistas_paineis.json
# pela sonda de camada; repetido aqui para o coletor rodar sozinho).
URL_SUB_PAINEL = ("https://app.powerbi.com/view?r=eyJrIjoiZjg5MzkyM2QtMGJkZi00MGRiLWJhYmYt"
                  "MjcyZTBkMmNiZDc2IiwidCI6Ijg1NDczOTk4LTFmODEtNDAxMS1iYzk3LTg3YWUwNGU2MTIwNCJ9")

# Régua do ciclo (§ metodologia): o que separa antecipação de resposta é a data do ATO,
# não o ano impresso no painel.
CICLO_INICIO = date(2026, 6, 29)

MESES = {"janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4, "maio": 5,
         "junho": 6, "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10,
         "novembro": 11, "dezembro": 12}

# "Decreto nº 1.234, de 5 de março de 2026" / "Portaria 12/2026 de 05/03/2026" / "Lei ..."
RE_ATO = re.compile(
    r"(decreto|portaria|resolu[çc][ãa]o|lei|instru[çc][ãa]o normativa)"
    r"[^\n]{0,40}?n?[ºo°\.]?\s*([\d][\d\.\-/]{0,15})"
    r"[^\n]{0,60}?de\s+(\d{1,2})\s*(?:de\s+)?([a-zç]+|\d{1,2})\s*(?:de\s+)?(\d{4})",
    re.IGNORECASE)


def _norm(s: str) -> str:
    """Compara nome de município ignorando acento, caixa, pontuação e espaço duplo."""
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def ler_ato(texto: str):
    """Extrai {tipo, numero, data} do texto do PRÓPRIO documento. None se não achar —
    nunca chuta. A data volta em ISO; dia/mês inválidos devolvem None (não silenciam)."""
    m = RE_ATO.search(texto or "")
    if not m:
        return None
    tipo, numero, dia, mes_txt, ano = m.groups()
    mes = MESES.get(_norm(mes_txt)) if not mes_txt.isdigit() else int(mes_txt)
    if not mes:
        return None
    try:
        d = date(int(ano), int(mes), int(dia))
    except ValueError:
        return None
    return {"tipo": tipo.lower(), "numero": numero.strip(" ."), "data": d.isoformat()}


def eh_pdf(conteudo: bytes, url: str) -> bool:
    """O CONTEÚDO manda, não a extensão da URL: portal estadual que responde HTML numa URL
    terminada em .pdf (página de erro, visualizador, aviso de defeso) é comum, e tratá-lo
    como PDF só produziria uma lacuna falsa. A extensão só decide quando o corpo não é
    claramente HTML."""
    if conteudo[:5] == b"%PDF-":
        return True
    if re.match(rb"\s*(<!doctype html|<html|<\?xml)", conteudo[:64], re.IGNORECASE):
        return False
    return url.lower().split("?")[0].endswith(".pdf")


def texto_do_documento(conteudo: bytes, url: str) -> str:
    """Texto legível de PDF (pypdf) ou HTML. Devolve '' se ilegível — quem chama
    transforma isso em lacuna declarada, nunca em ausência de ato."""
    if eh_pdf(conteudo, url):
        try:
            import io
            import logging

            from pypdf import PdfReader
            # PDF corrompido é caminho ESPERADO aqui (vira lacuna declarada); o aviso do
            # pypdf em stderr só polui a saída do portão.
            logging.getLogger("pypdf").setLevel(logging.ERROR)
            r = PdfReader(io.BytesIO(conteudo), strict=False)
            return "\n".join((p.extract_text() or "") for p in r.pages[:20])
        except Exception:  # noqa: BLE001 — PDF corrompido/protegido vira lacuna
            return ""
    try:
        html = conteudo.decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return ""
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    return re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", html))


def linha_para_registro(linha: dict) -> dict:
    """Normaliza uma linha bruta do renderizador para os campos do projeto. Célula ausente
    vira None — o painel não tem coluna de número/data de ato, e isso é o ponto."""
    cel = {_norm(k): v for k, v in (linha.get("celulas") or {}).items()}

    def pega(*chaves):
        for c in chaves:
            for k, v in cel.items():
                if c in k and v not in (None, ""):
                    return v
        return None

    ano = pega("ano")
    try:
        ano = int(re.sub(r"\D", "", str(ano))) if ano else None
    except ValueError:
        ano = None
    return {"municipio_no_painel": pega("municipio", "município"),
            "calha": pega("calha"),
            "ano_do_plano": ano,
            "url_do_link": linha.get("url_do_link"),
            "como_obtido": linha.get("como_obtido"),
            "indice_no_painel": linha.get("indice")}


def casar_ibge(nome: str, por_nome: dict):
    """Nome do painel → código IBGE do AM. Sem casamento, devolve None: vira lacuna
    declarada, nunca palpite (um município errado contamina o índice de um terceiro)."""
    if not nome:
        return None
    alvo = _norm(nome)
    for (n, uf), cod in por_nome.items():
        if uf == "AM" and _norm(n) == alvo:
            return cod
    return None


class Efeitos:
    """Os quatro efeitos colaterais do coletor num só lugar: rede, evidência, log e livro
    de fontes. Existe para o autoteste poder rodar DE VERDADE offline e sem escrever em
    data/ — antes desta separação, `--autoteste` batia em app.powerbi.com e sujava
    log_buscas.json e fontes_consultadas.json a cada execução do portão."""

    def __init__(self, buscar_fn=buscar, preservar_fn=preservar_evidencia,
                 log_fn=log_busca, lacuna_fn=registrar_lacuna,
                 marcar_fn=marcar_fonte_consultada, pausa_s=2.0):
        self.buscar = buscar_fn
        self.preservar = preservar_fn
        self.log = log_fn
        self.lacuna = lacuna_fn
        self.marcar = marcar_fn
        self.pausa_s = pausa_s


class EfeitosInertes(Efeitos):
    """Dublê do autoteste: nenhuma requisição, nenhuma escrita. Guarda o que teria feito,
    para os testes afirmarem sobre isso (ex.: 'link que não abre vira lacuna declarada')."""

    def __init__(self, respostas=None):
        self.respostas = respostas or {}      # url → bytes (documento simulado)
        self.lacunas, self.logs, self.marcados, self.preservados = [], [], [], []
        super().__init__(buscar_fn=self._buscar, preservar_fn=self._preservar,
                         log_fn=self._log, lacuna_fn=self._lacuna,
                         marcar_fn=self._marcar, pausa_s=0.0)

    def _buscar(self, url, timeout=45):
        if url not in self.respostas:
            raise OSError(f"offline: sem resposta simulada para {url}")
        return self.respostas[url]

    def _preservar(self, conteudo, url, ext, origem):
        self.preservados.append(url)
        return "hash-simulado-" + str(len(conteudo))

    def _log(self, *a, **k):
        self.logs.append((a, k))

    def _lacuna(self, fonte, motivo, *a, **k):
        self.lacunas.append((fonte, motivo))

    def _marcar(self, ibges, fonte, nivel, resultado="consultada"):
        self.marcados.append((list(ibges), fonte, nivel))


def renderizar(url: str, de_arquivo: str | None) -> dict:
    """Chama o renderizador Node, ou relê um JSON já salvo (--de-arquivo), que é como se
    audita uma rodada antiga sem bater no sítio de novo."""
    if de_arquivo:
        with open(de_arquivo, encoding="utf-8") as f:
            return json.load(f)
    if not RENDERIZADOR.exists():
        return {"ok": False, "erro": f"renderizador ausente: {RENDERIZADOR}", "linhas": []}
    try:
        p = subprocess.run(["node", str(RENDERIZADOR), url],
                           capture_output=True, text=True, timeout=300,
                           env={**__import__("os").environ, "MONITOR_UA": UA})
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception as e:  # noqa: BLE001 — navegador indisponível vira lacuna declarada
        return {"ok": False, "erro": f"{type(e).__name__}: {e}", "linhas": []}


def coletar(url: str, de_arquivo=None, limite=None, efeitos: "Efeitos | None" = None) -> dict:
    ef = efeitos or Efeitos()
    por_cod, por_nome = referencia_ibge()
    render = renderizar(url, de_arquivo)
    if not render.get("ok"):
        ef.lacuna("painel Power BI da Defesa Civil do AM",
                  render.get("erro") or "render sem linhas",
                  "painel AM", 1, strings=[url], uf="AM")
        return {"itens": [], "resumo": {"erro": render.get("erro")}}

    itens, ibges_lidos = [], []
    for bruta in (render.get("linhas") or [])[:limite]:
        r = linha_para_registro(bruta)
        cod = casar_ibge(r["municipio_no_painel"], por_nome)
        if not cod:
            ef.lacuna(f"município do painel: {r['municipio_no_painel']!r}",
                      "nome não casou com a referência IBGE do AM",
                      "painel AM", 1, uf="AM")
        else:
            ibges_lidos.append(cod)
        item = {**r, "uf": "AM", "ibge": cod,
                "nome_ibge": (por_cod.get(cod) or {}).get("nome") if cod else None,
                # A declaração do estado, isolada e rotulada como tal.
                "camada": "declarado", "ato": None, "hash_evidencia": None,
                "documento_oficial_confirmado": None, "promovivel": False,
                "lido_em": render.get("lido_em") or hoje()}

        if r["url_do_link"]:
            try:
                conteudo = ef.buscar(r["url_do_link"], timeout=45)
                ext = "pdf" if conteudo[:5] == b"%PDF-" else "html"
                item["hash_evidencia"] = ef.preservar(
                    conteudo, r["url_do_link"], ext, "painel Power BI Defesa Civil AM")
                ato = ler_ato(texto_do_documento(conteudo, r["url_do_link"]))
                if ato:
                    # Único caminho para `documentado`: documento aberto E ato com número e data.
                    item["ato"] = ato
                    item["camada"] = "documentado"
                    item["no_ciclo"] = date.fromisoformat(ato["data"]) >= CICLO_INICIO
                else:
                    item["observacao"] = ("documento preservado, mas sem número e data de ato "
                                          "legíveis — permanece declarado")
            except Exception as e:  # noqa: BLE001
                ef.lacuna(f"documento de {r['municipio_no_painel']}",
                          f"{type(e).__name__}: {e}", "painel AM", 1,
                          strings=[r["url_do_link"]], uf="AM")
                item["observacao"] = f"link não abriu ({type(e).__name__})"
            if ef.pausa_s:
                time.sleep(ef.pausa_s)     # §11: no máximo 1 requisição a cada 2s
        elif r["ano_do_plano"]:
            item["observacao"] = ("painel declara plano sem expor link do documento "
                                  f"({r['como_obtido']})")
        else:
            item["camada"] = "sem_plano_declarado"
        itens.append(item)

    if ibges_lidos:
        ef.marcar(ibges_lidos, "painel Power BI da Defesa Civil do AM",
                  "estadual", resultado="consultada")
    resumo = {
        "n_linhas_lidas": len(itens),
        "documentado": sum(1 for i in itens if i["camada"] == "documentado"),
        "declarado": sum(1 for i in itens if i["camada"] == "declarado"),
        "sem_plano_declarado": sum(1 for i in itens if i["camada"] == "sem_plano_declarado"),
        "sem_codigo_ibge": sum(1 for i in itens if not i["ibge"]),
        "no_ciclo": sum(1 for i in itens if i.get("no_ciclo")),
    }
    ef.log("painel AM", 1, [url], "pista", uf="AM", nivel="estadual",
           n_resultados=len(itens),
           resultados=(f"{resumo['documentado']} documentado(s), {resumo['declarado']} "
                       f"declarado(s), {resumo['sem_plano_declarado']} sem plano"))
    return {"itens": itens, "resumo": resumo}


def gravar_fila(saida: dict, url: str) -> dict:
    fila = ler(FILA, {"_governanca": (
        "Leitura do painel Power BI da Defesa Civil do AM (coletar_painel_am.py, §165). "
        "A tabela do painel é DECLARAÇÃO DO ESTADO: traz o ano, não o número e a data do "
        "ato. Camada 'declarado' entra com o desconto da metodologia; 'documentado' só "
        "para município cujo link abriu o documento e cujo ato teve número e data lidos do "
        "próprio documento. TRAVA ABSOLUTA: nada aqui entra no banco sem promoção humana "
        "(regra R7). Ano 2026 no painel NÃO prova antecipação."),
        "itens": []})
    fila["fonte"] = url
    fila["atualizado_em"] = hoje()
    fila["resumo"] = saida["resumo"]
    por_chave = {(i.get("ibge"), i.get("municipio_no_painel")): i for i in fila["itens"]}
    for i in saida["itens"]:
        por_chave[(i.get("ibge"), i.get("municipio_no_painel"))] = i
    fila["itens"] = sorted(por_chave.values(),
                           key=lambda x: (x.get("indice_no_painel") or 1e9,
                                          x.get("municipio_no_painel") or ""))
    gravar(FILA, fila)
    return fila


# ── autoteste (offline: sem rede, sem navegador) ─────────────────────────────

FIXTURE = {
    "ok": True, "url": URL_SUB_PAINEL, "lido_em": "2026-09-22",
    "colunas": ["Índice", "Calha", "Município", "Plano", "Ano do Plano"],
    "linhas": [
        {"indice": 1, "celulas": {"Índice": "1", "Calha": "Alto Solimões",
                                  "Município": "Atalaia do Norte", "Plano": "",
                                  "Ano do Plano": "2026"},
         "url_do_link": "https://defesacivil.am.gov.br/planos/atalaia-do-norte.pdf",
         "como_obtido": "href na própria célula"},
        {"indice": 2, "celulas": {"Índice": "2", "Calha": "Alto Solimões",
                                  "Município": "Benjamin Constant", "Plano": "",
                                  "Ano do Plano": "2026"},
         "url_do_link": None, "como_obtido": "ícone sem href — URL não obtida sem clique"},
        {"indice": 3, "celulas": {"Índice": "3", "Calha": "Madeira",
                                  "Município": "Humaitá", "Plano": "", "Ano do Plano": ""},
         "url_do_link": None, "como_obtido": "sem link na linha"},
    ],
}


DOC_COM_ATO = (b"<html><body><h1>Plano de Contingencia Municipal</h1>"
               b"<p>Aprovado pelo DECRETO N\xc2\xba 1.234, de 5 de mar\xc3\xa7o de 2026.</p>"
               b"</body></html>")
DOC_SEM_ATO = b"<html><body><p>Plano de Contingencia Municipal - versao 2026.</p></body></html>"


def _inertes(respostas=None) -> "EfeitosInertes":
    return EfeitosInertes(respostas or {})


def autoteste() -> int:
    def t_le_ato_por_extenso():
        a = ler_ato("DECRETO Nº 1.234, de 5 de março de 2026, aprova o Plano de Contingência")
        return a and a["numero"] == "1.234" and a["data"] == "2026-03-05" and a["tipo"] == "decreto"

    def t_le_ato_numerico():
        a = ler_ato("Portaria nº 12/2026, de 30 de 06 de 2026")
        return a and a["data"] == "2026-06-30"

    def t_texto_sem_ato_nao_inventa():
        return ler_ato("Plano de Contingência Municipal — versão 2026, sem ato publicado") is None

    def t_data_impossivel_vira_none():
        return ler_ato("Decreto nº 9, de 31 de fevereiro de 2026") is None

    def t_pdf_ilegivel_nao_vira_ausencia_de_ato():
        """PDF corrompido devolve texto vazio — e texto vazio nunca pode ser lido como
        'não há ato'. Quem chama tem de tratar como lacuna."""
        return texto_do_documento(b"%PDF-1.4 lixo binario", "x.pdf") == ""

    def t_html_servido_em_url_pdf():
        """Portal estadual que responde HTML numa URL .pdf: o conteúdo manda. Tratar pela
        extensão produziria lacuna falsa num documento perfeitamente legível."""
        return (eh_pdf(DOC_COM_ATO, "https://x/plano.pdf") is False
                and eh_pdf(b"%PDF-1.7 ...", "https://x/sem-extensao") is True
                and ler_ato(texto_do_documento(DOC_COM_ATO, "https://x/plano.pdf")) is not None)

    def t_casa_ibge_com_acento_e_caixa():
        _, por_nome = referencia_ibge()
        return (casar_ibge("SAO GABRIEL DA CACHOEIRA", por_nome)
                == casar_ibge("São Gabriel da Cachoeira", por_nome) is not None)

    def t_nome_desconhecido_nao_casa():
        _, por_nome = referencia_ibge()
        return casar_ibge("Município Que Não Existe", por_nome) is None

    def t_linha_para_registro():
        r = linha_para_registro(FIXTURE["linhas"][0])
        return (r["municipio_no_painel"] == "Atalaia do Norte" and r["ano_do_plano"] == 2026
                and r["calha"] == "Alto Solimões")

    def t_link_abre_com_ato_vira_documentado():
        """Único caminho para `documentado`: o link abriu E o ato tem número e data lidos
        do próprio documento. Aqui a data é 05/03/2026, ANTES do ciclo — logo no_ciclo=False,
        provando que a régua olha a data do ato, não o ano do painel."""
        ef = _inertes({FIXTURE["linhas"][0]["url_do_link"]: DOC_COM_ATO})
        s = coletar(URL_SUB_PAINEL, de_arquivo=_fixture_em_disco(), limite=3, efeitos=ef)
        a = {i["municipio_no_painel"]: i for i in s["itens"]}["Atalaia do Norte"]
        return (a["camada"] == "documentado" and a["ato"]["numero"] == "1.234"
                and a["no_ciclo"] is False and a["hash_evidencia"]
                and a["promovivel"] is False)

    def t_link_abre_sem_ato_continua_declarado():
        ef = _inertes({FIXTURE["linhas"][0]["url_do_link"]: DOC_SEM_ATO})
        s = coletar(URL_SUB_PAINEL, de_arquivo=_fixture_em_disco(), limite=3, efeitos=ef)
        a = {i["municipio_no_painel"]: i for i in s["itens"]}["Atalaia do Norte"]
        return a["camada"] == "declarado" and a["ato"] is None and a["hash_evidencia"]

    def t_link_que_nao_abre_vira_lacuna():
        ef = _inertes()                       # nenhuma resposta simulada → buscar levanta
        s = coletar(URL_SUB_PAINEL, de_arquivo=_fixture_em_disco(), limite=3, efeitos=ef)
        a = {i["municipio_no_painel"]: i for i in s["itens"]}["Atalaia do Norte"]
        return (a["camada"] == "declarado" and a["hash_evidencia"] is None
                and any("Atalaia" in f for f, _ in ef.lacunas))

    def t_ano_sem_link_fica_declarado():
        """O coração da regra: painel diz 2026, não há link → declarado, nunca documentado,
        e nunca 'antecipado por ser de 2026'."""
        s = coletar(URL_SUB_PAINEL, de_arquivo=_fixture_em_disco(), limite=3, efeitos=_inertes())
        bc = {i["municipio_no_painel"]: i for i in s["itens"]}["Benjamin Constant"]
        return (bc["camada"] == "declarado" and bc["ato"] is None
                and bc["promovivel"] is False and "no_ciclo" not in bc)

    def t_sem_ano_e_sem_link_e_sem_plano():
        s = coletar(URL_SUB_PAINEL, de_arquivo=_fixture_em_disco(), limite=3, efeitos=_inertes())
        h = {i["municipio_no_painel"]: i for i in s["itens"]}["Humaitá"]
        return h["camada"] == "sem_plano_declarado" and h["ibge"] is not None

    def t_render_falho_vira_lacuna():
        ef = _inertes()
        s = coletar(URL_SUB_PAINEL, de_arquivo=_fixture_falha_em_disco(), efeitos=ef)
        return s["itens"] == [] and s["resumo"].get("erro") and len(ef.lacunas) == 1

    def t_trava_de_campo():
        s = coletar(URL_SUB_PAINEL, de_arquivo=_fixture_em_disco(), limite=3, efeitos=_inertes())
        return all(i["promovivel"] is False and i["documento_oficial_confirmado"] is None
                   for i in s["itens"])

    def t_autoteste_nao_toca_em_data():
        """Regressão da falha encontrada ao construir este coletor: a primeira versão do
        autoteste batia na rede e escrevia em log_buscas.json e fontes_consultadas.json a
        cada execução do portão, deixando a árvore suja."""
        antes = {n: (RAIZ / "data" / n).read_bytes()
                 for n in ("log_buscas.json", "fontes_consultadas.json")}
        coletar(URL_SUB_PAINEL, de_arquivo=_fixture_em_disco(), limite=3, efeitos=_inertes())
        return all((RAIZ / "data" / n).read_bytes() == b for n, b in antes.items())

    def t_trava_estrutural():
        fonte = (RAIZ / "coletar_painel_am.py").read_text(encoding="utf-8")
        for proibido in ["estados.json", "saude_uf.json", "municipios.json",
                         "indice.json", "monitor_saude.json"]:
            if re.search(r'gravar\(\s*["\']' + re.escape(proibido), fonte):
                return False
            if re.search(r'open\([^)]*' + re.escape(proibido) + r'[^)]*,\s*["\']([wa])', fonte):
                return False
        return True

    return rodar_autoteste({
        "lê nº e data de ato por extenso": t_le_ato_por_extenso,
        "lê nº e data de ato em formato numérico": t_le_ato_numerico,
        "texto sem ato não inventa ato": t_texto_sem_ato_nao_inventa,
        "data impossível vira None (não silencia)": t_data_impossivel_vira_none,
        "PDF ilegível devolve vazio (vira lacuna, não ausência)": t_pdf_ilegivel_nao_vira_ausencia_de_ato,
        "HTML servido em URL .pdf é lido como HTML": t_html_servido_em_url_pdf,
        "casa nome do painel com IBGE (acento/caixa)": t_casa_ibge_com_acento_e_caixa,
        "nome desconhecido não casa (vira lacuna)": t_nome_desconhecido_nao_casa,
        "normaliza linha bruta do renderizador": t_linha_para_registro,
        "link abre + ato com nº e data → documentado": t_link_abre_com_ato_vira_documentado,
        "link abre sem ato legível → continua declarado": t_link_abre_sem_ato_continua_declarado,
        "link que não abre → lacuna declarada": t_link_que_nao_abre_vira_lacuna,
        "ano 2026 sem link → declarado, nunca documentado": t_ano_sem_link_fica_declarado,
        "linha sem ano e sem link → sem plano declarado": t_sem_ano_e_sem_link_e_sem_plano,
        "render falho vira lacuna declarada, não ausência": t_render_falho_vira_lacuna,
        "trava de campo: nasce não promovível": t_trava_de_campo,
        "autoteste é offline e não escreve em data/": t_autoteste_nao_toca_em_data,
        "trava estrutural: não escreve no banco": t_trava_estrutural,
    })


def _escrever_tmp(obj) -> str:
    import tempfile
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(obj, f, ensure_ascii=False)
    f.close()
    return f.name


def _fixture_em_disco() -> str:
    return _escrever_tmp(FIXTURE)


def _fixture_falha_em_disco() -> str:
    return _escrever_tmp({"ok": False, "erro": "grade não encontrada no DOM renderizado",
                          "linhas": []})


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    a = sys.argv
    url = a[a.index("--url") + 1] if "--url" in a else URL_SUB_PAINEL
    de_arquivo = a[a.index("--de-arquivo") + 1] if "--de-arquivo" in a else None
    limite = int(a[a.index("--limite") + 1]) if "--limite" in a else None

    saida = coletar(url, de_arquivo=de_arquivo, limite=limite)
    if not saida["itens"]:
        print("Nenhuma linha lida — lacuna declarada no log. Nada foi escrito na fila.")
        print(f"  motivo: {saida['resumo'].get('erro')}")
        return 1
    fila = gravar_fila(saida, url)
    r = saida["resumo"]
    print(f"\nPainel da Defesa Civil do AM — {r['n_linhas_lidas']} linha(s) lida(s):")
    print(f"  documentado (link abriu + ato com nº e data): {r['documentado']}")
    print(f"  declarado (painel afirma, sem ato legível):    {r['declarado']}")
    print(f"  sem plano declarado no painel:                 {r['sem_plano_declarado']}")
    print(f"  sem código IBGE (lacuna declarada):            {r['sem_codigo_ibge']}")
    print(f"  com ato dentro do ciclo (>= 29/06/2026):       {r['no_ciclo']}")
    print(f"\nFila: data/{FILA} ({len(fila['itens'])} item(ns)).")
    print("Nada entra no banco sem promoção humana (R7). Ano no painel não prova antecipação.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
