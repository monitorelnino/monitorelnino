#!/usr/bin/env python3
"""Sonda de CAMADA: procura, no HTML dos sítios oficiais, evidência publicada atrás de
painel ou de hospedagem de terceiros — a classe de canal que escapou de toda a varredura
textual até 22/09/2026.

MOTIVAÇÃO (caso real, 22/09/2026). Em resposta a pedido de LAI, a Ouvidoria da Defesa
Civil do Amazonas não enviou a lista pedida: indicou um painel Power BI. Aberto num
navegador real, o painel traz os 62 municípios do estado com ano do plano e link do
documento por município — exatamente os itens (1) e (2) do pedido. O painel é público e
provavelmente antigo; nenhuma rodada do robô o encontrou, porque `web_fetch`/busca textual
recebe de app.powerbi.com apenas o esqueleto da página: a tabela é montada em JavaScript
depois do carregamento.

A falha, portanto, não foi de COBERTURA (quantas fontes) e sim de CAMADA (em que forma a
evidência está publicada). O erro que isso produz no MARÉ não é aleatório: pune
sistematicamente a UF que publica em painel moderno, que aparece como se nada tivesse
publicado. Daí esta sonda ser sobre o índice, não só sobre recall.

O QUE ESTE SCRIPT FAZ: baixa páginas institucionais candidatas de cada UF/setor e procura
no HTML BRUTO referências a hospedeiros conhecidos de painel/arquivo (lista HOSPEDEIROS
abaixo). Um <iframe src="https://app.powerbi.com/view?r=..."> aparece no código-fonte
mesmo quando o conteúdo não aparece — é justamente isso que torna a sonda viável sem
navegador. Cada referência vira PISTA para triagem humana.

O QUE ESTE SCRIPT NÃO FAZ: não abre o painel, não lê a tabela, não decide que há plano.
Extrair conteúdo de painel exige renderização (navegador real) e é passo humano/assistido,
fora desta sonda. Aqui a pergunta é só: "existe uma camada que não estamos olhando?".

===========================================================================
TRAVA ABSOLUTA (idêntica à de descobrir_planos.py) — três camadas independentes:
  1. ESTRUTURAL: nunca escreve em estados.json, saude_uf.json, municipios.json,
     indice.json ou monitor_saude.json (garantido por autoteste que lê o próprio fonte).
  2. DE CAMPO: todo achado nasce com "documento_oficial_confirmado": null e
     "promovivel": false.
  3. DE PROCESSO: achados vão para data/pistas_paineis.json (fila própria) — nunca
     direto no banco. Promoção é humana (regra R7).
===========================================================================

REGRAS herdadas do §11: cliente identificado (coletores_base.UA); no máximo 1 requisição
por domínio a cada 2s; sítio fora do ar ou que recusa = acesso_recusado, jamais "nada
localizado"; toda execução entra no log v2 via coletores_base.log_busca.

Uso: python3 sondar_paineis.py [--limite N] [--setor saude|defesa_civil]
     python3 sondar_paineis.py --autoteste    (offline)
"""
import re
import sys
import time

from coletores_base import (RAIZ, buscar, hoje, ler, gravar, log_busca,
                            rodar_autoteste)

FILA = "pistas_paineis.json"

# Hospedeiros cuja presença no HTML indica evidência publicada fora da camada textual.
# Declarado, não escondido: a lista é curada e certamente incompleta — um hospedeiro
# ausente só reduz recall, nunca inventa achado.
HOSPEDEIROS = {
    "app.powerbi.com": "painel Power BI",
    "powerbi.com": "painel Power BI",
    "lookerstudio.google.com": "painel Looker Studio",
    "datastudio.google.com": "painel Looker Studio (Data Studio)",
    "public.tableau.com": "painel Tableau",
    "tableau.com": "painel Tableau",
    "qlikcloud.com": "painel Qlik",
    "arcgis.com": "mapa/StoryMap ArcGIS",
    "experience.arcgis.com": "ArcGIS Experience",
    "drive.google.com": "pasta/arquivo no Google Drive",
    "docs.google.com": "documento/planilha Google",
    "1drv.ms": "arquivo no OneDrive",
    "sharepoint.com": "arquivo no SharePoint",
}

UFS = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
       "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]

# Reaproveita a curadoria de domínios de descobrir_planos.py (mesma lista, mesma lacuna
# de curadoria) para não criar uma segunda fonte de verdade sobre "onde mora cada órgão".
try:
    from descobrir_planos import dominio_para   # noqa: E402
except Exception:  # noqa: BLE001 — sonda tem de rodar mesmo se o outro script mudar
    def dominio_para(uf: str, setor: str) -> str:
        prefixo = "saude" if setor == "saude" else "defesacivil"
        return f"{prefixo}.{uf.lower()}.gov.br"

CAMINHOS = ["/", "/planos", "/defesa-civil", "/acesso-a-informacao", "/transparencia"]


def achar_hospedeiros(html: str) -> list:
    """Devolve [{'hospedeiro','tipo','url'}] para cada referência encontrada no HTML bruto.
    Casa tanto `src="https://app.powerbi.com/view?r=..."` quanto menção em texto/link."""
    achados, urls_vistas = [], set()
    # Do hospedeiro mais específico para o mais genérico: `app.powerbi.com` antes de
    # `powerbi.com`, para a mesma URL não virar duas pistas.
    for host in sorted(HOSPEDEIROS, key=len, reverse=True):
        tipo = HOSPEDEIROS[host]
        if host not in html.lower():
            continue
        padrao = re.compile(r"https?://[^\s\"'<>\\]*" + re.escape(host) + r"[^\s\"'<>\\]*",
                            re.IGNORECASE)
        urls = padrao.findall(html) or [f"https://{host} (referência sem URL completa)"]
        for u in urls[:5]:          # teto por hospedeiro: pista é amostra, não espelho
            if u in urls_vistas:
                continue
            urls_vistas.add(u)
            achados.append({"hospedeiro": host, "tipo": tipo, "url": u})
    return achados


def carregar_fila():
    return ler(FILA, {"_governanca": (
        "Fila de pistas de CAMADA (sondar_paineis.py, 22/09/2026): referências a painéis "
        "e hospedagens de terceiros achadas no HTML de sítios oficiais. Motivada pelo "
        "painel Power BI da Defesa Civil do AM, público e nunca alcançado pela varredura "
        "textual. TRAVA ABSOLUTA: nada aqui entra no banco sem confirmação humana do "
        "documento primário (promoção = regra R7). Um item nesta fila NÃO é plano: é um "
        "lugar onde ainda não olhamos."),
        "itens": []})


def _hash_pista(p: dict) -> str:
    import hashlib
    return hashlib.sha256(f"{p['uf']}|{p['setor']}|{p['url']}".encode()).hexdigest()[:16]


def registrar(fila: dict, achados: list) -> list:
    vistos = {i["hash"] for i in fila["itens"]}
    ineditos = []
    for a in achados:
        a["hash"] = _hash_pista(a)
        if a["hash"] in vistos:
            continue
        a["documento_oficial_confirmado"] = None
        a["promovivel"] = False
        a["status"] = "pendente_abertura_em_navegador"
        a["descoberto_em"] = hoje()
        fila["itens"].append(a)
        vistos.add(a["hash"])
        ineditos.append(a)
    return ineditos


def classificar_falha(e) -> tuple:
    """(decisao, motivo) de uma falha de busca. §181 (23/09/2026): a versão anterior chamava TODA
    falha de "acesso recusado", e isso mentia em duas direções. Dos 235 registros de falha da
    rodada de 23/09, **80 eram HTTP 404** nos caminhos adivinhados (`/planos`, `/defesa-civil`) —
    caminho que não existe não é fonte que recusa —, 140 eram falha de conexão (DNS, TLS, reset) e
    só **3 eram 403**, que é o servidor dizendo não. A distinção é a do §170: recusa se respeita,
    ausência de resposta não é recusa."""
    import urllib.error
    if isinstance(e, urllib.error.HTTPError):
        if e.code in (401, 402, 403, 429, 451):
            return "acesso recusado", f"HTTP {e.code} — o servidor respondeu NÃO; não se contorna"
        if e.code in (404, 410):
            return "consultado sem achado", f"HTTP {e.code} — o caminho tentado não existe neste domínio"
        return "erro", f"HTTP {e.code} — servidor com defeito"
    return "erro", f"{type(e).__name__} — sem resposta do servidor (não é recusa; ver §170)"


def sondar(uf: str, setor: str, fila: dict) -> list:
    """Sonda um alvo (UF + setor). Nunca levanta: falha de rede vira acesso_recusado."""
    dominio = dominio_para(uf, setor)
    achados = []
    consultadas = 0
    for caminho in CAMINHOS[:3]:        # 3 páginas por alvo — mesma disciplina de custo
        url = f"https://{dominio}{caminho}"
        try:
            html = buscar(url, timeout=30).decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001 — tolerante por design
            decisao, motivo = classificar_falha(e)
            log_busca("sonda de painéis", 1, [url], decisao,
                      resultados=f"{motivo} ({type(e).__name__}: {e})", uf=uf)
            time.sleep(2.0)
            continue
        consultadas += 1
        for ref in achar_hospedeiros(html):
            achados.append({"uf": uf, "setor": setor, "dominio": dominio,
                            "pagina_origem": url, **ref})
        time.sleep(2.0)                 # backoff: nunca mais de 1 req/2s por domínio
    novos = registrar(fila, achados)
    if achados:
        log_busca("sonda de painéis", 1, [dominio], "pista",
                  resultados="; ".join(sorted({a["tipo"] for a in achados})),
                  uf=uf, n_resultados=len(achados))
    elif consultadas:
        # §181: o silêncio era o pior dos registros. Sem esta linha, "consultei e não havia painel"
        # e "nunca consultei" ficam idênticos no log — e a leitura do resultado erra, porque só as
        # falhas aparecem. Aconteceu de verdade na leitura da rodada de 23/09.
        log_busca("sonda de painéis", 1, [dominio], "consultado sem achado",
                  resultados=f"consultado em {consultadas} página(s); nenhuma referência a "
                             f"hospedeiro de painel no HTML bruto", uf=uf, n_resultados=0)
    return novos


STATUS_VERIFICADO = "verificado_em_navegador"


def anotar_verificacao(fila: dict, anotacoes: list) -> list:
    """Registra na fila o que cada painel É, depois de aberto em navegador (§181, 23/09/2026).

    A sonda diz que existe uma camada; só a abertura diz o que há dentro. Sem este registro, cada
    sessão reabre os mesmos painéis para redescobrir que o de MG é boletim meteorológico — e, pior,
    a ausência de plano municipal fica indistinguível de "ninguém olhou". Vocabulário fechado:
    `traz_planos_municipais` é True, False ou None (não deu para determinar), e `coletar: False`
    exige motivo escrito. Nunca toca em `promovivel` nem em `documento_oficial_confirmado`: promoção
    segue humana (R7)."""
    aplicadas = []
    for a in anotacoes:
        alvo = [i for i in fila["itens"] if i.get("uf") == a["uf"] and i.get("setor") == a["setor"]]
        if a.get("url"):
            alvo = [i for i in alvo if i.get("url") == a["url"]]
        if not alvo:
            raise ValueError(f"nenhum item na fila para {a['uf']}/{a['setor']}")
        if a.get("traz_planos_municipais") not in (True, False, None):
            raise ValueError("traz_planos_municipais: só True, False ou None")
        if a.get("coletar") not in (True, False):
            raise ValueError("coletar: só True ou False")
        if a["coletar"] is False and not a.get("motivo"):
            raise ValueError("coletar=False exige motivo escrito")
        for i in alvo:
            i["status"] = STATUS_VERIFICADO
            i["verificado_em"] = a.get("verificado_em") or hoje()
            i["conteudo"] = a["conteudo"]
            i["traz_planos_municipais"] = a.get("traz_planos_municipais")
            i["coletar"] = a["coletar"]
            if a.get("motivo"):
                i["motivo"] = a["motivo"]
            aplicadas.append(i)
    return aplicadas


def autoteste() -> int:
    def t_acha_powerbi_em_iframe():
        html = '<iframe src="https://app.powerbi.com/view?r=eyJrIjoiAB" width="800"></iframe>'
        a = achar_hospedeiros(html)
        return len(a) >= 1 and a[0]["hospedeiro"] == "app.powerbi.com" and "view?r=" in a[0]["url"]

    def t_html_sem_painel_nao_inventa():
        return achar_hospedeiros("<html><body><p>Plano de contingência 2026</p></body></html>") == []

    def t_varios_hospedeiros():
        html = ('a <a href="https://drive.google.com/drive/folders/XYZ">pasta</a> '
                'e <iframe src="https://public.tableau.com/views/plano"></iframe>')
        tipos = {x["hospedeiro"] for x in achar_hospedeiros(html)}
        return "drive.google.com" in tipos and "public.tableau.com" in tipos

    def t_dedup_e_trava_de_campo():
        fila = {"_governanca": "x", "itens": []}
        item = {"uf": "XX", "setor": "defesa_civil", "dominio": "d", "pagina_origem": "p",
                "hospedeiro": "app.powerbi.com", "tipo": "painel Power BI",
                "url": "https://app.powerbi.com/view?r=1"}
        a = registrar(fila, [dict(item)])
        b = registrar(fila, [dict(item)])
        if not (len(a) == 1 and len(b) == 0):
            return False
        i = fila["itens"][0]
        return (i["documento_oficial_confirmado"] is None and i["promovivel"] is False
                and i["status"] == "pendente_abertura_em_navegador")

    def t_trava_estrutural():
        fonte = (RAIZ / "sondar_paineis.py").read_text(encoding="utf-8")
        for proibido in ["estados.json", "saude_uf.json", "municipios.json",
                         "indice.json", "monitor_saude.json"]:
            if re.search(r'gravar\(\s*["\']' + re.escape(proibido), fonte):
                return False
            if re.search(r'open\([^)]*' + re.escape(proibido) + r'[^)]*,\s*["\']([wa])', fonte):
                return False
        return True

    def t_caso_am_reproduz():
        """Regressão do caso que originou a sonda: o HTML do sítio da Defesa Civil do AM
        com o link do painel tem de virar pista."""
        html = ('<p>Confira o <a href="https://app.powerbi.com/view?r=eyJrIjoiNDhmOGE4YjMt">'
                'Painel de Informações</a> da Defesa Civil.</p>')
        a = achar_hospedeiros(html)
        return len(a) == 1 and a[0]["tipo"] == "painel Power BI"

    def t_404_nao_e_recusa():
        import urllib.error
        e = urllib.error.HTTPError("https://x/planos", 404, "Not Found", None, None)
        d, motivo = classificar_falha(e)
        return d == "consultado sem achado" and "não existe" in motivo

    def t_403_e_recusa_que_se_respeita():
        import urllib.error
        e = urllib.error.HTTPError("https://x/", 403, "Forbidden", None, None)
        d, motivo = classificar_falha(e)
        return d == "acesso recusado" and "NÃO" in motivo

    def t_500_e_defeito_do_servidor():
        import urllib.error
        e = urllib.error.HTTPError("https://x/", 500, "Server Error", None, None)
        return classificar_falha(e)[0] == "erro"

    def t_sem_resposta_nao_e_recusa():
        import urllib.error
        d, motivo = classificar_falha(urllib.error.URLError("[Errno 11001] getaddrinfo failed"))
        return d == "erro" and "não é recusa" in motivo

    def t_anotacao_registra_o_que_o_painel_e():
        fila = {"itens": [{"uf": "MG", "setor": "defesa_civil", "url": "u", "hash": "h",
                           "status": "pendente_abertura_em_navegador", "promovivel": False,
                           "documento_oficial_confirmado": None}]}
        anotar_verificacao(fila, [{"uf": "MG", "setor": "defesa_civil", "conteudo": "boletim",
                                   "traz_planos_municipais": False, "coletar": False,
                                   "motivo": "não traz tabela de planos"}])
        i = fila["itens"][0]
        return (i["status"] == STATUS_VERIFICADO and i["traz_planos_municipais"] is False
                and i["coletar"] is False and i["motivo"]
                # a anotação é triagem, não promoção: as travas de campo continuam de pé
                and i["promovivel"] is False and i["documento_oficial_confirmado"] is None)

    def t_anotacao_sem_motivo_para_nao_coletar_reprova():
        fila = {"itens": [{"uf": "SC", "setor": "saude", "url": "u", "hash": "h"}]}
        try:
            anotar_verificacao(fila, [{"uf": "SC", "setor": "saude", "conteudo": "x",
                                       "traz_planos_municipais": False, "coletar": False}])
            return False
        except ValueError:
            return True

    def t_anotacao_de_alvo_inexistente_reprova():
        try:
            anotar_verificacao({"itens": []}, [{"uf": "ZZ", "setor": "saude", "conteudo": "x",
                                                "traz_planos_municipais": None, "coletar": False,
                                                "motivo": "m"}])
            return False
        except ValueError:
            return True

    return rodar_autoteste({
        "§181 404 em caminho adivinhado não é recusa": t_404_nao_e_recusa,
        "§181 403 é recusa que se respeita": t_403_e_recusa_que_se_respeita,
        "§181 5xx é defeito do servidor": t_500_e_defeito_do_servidor,
        "§181 falha de conexão é ausência de resposta, não recusa": t_sem_resposta_nao_e_recusa,
        "§181 anotação registra o que o painel é, sem promover": t_anotacao_registra_o_que_o_painel_e,
        "§181 não coletar exige motivo escrito": t_anotacao_sem_motivo_para_nao_coletar_reprova,
        "§181 anotação de alvo inexistente reprova": t_anotacao_de_alvo_inexistente_reprova,
        "acha Power BI em iframe (com a URL completa)": t_acha_powerbi_em_iframe,
        "HTML sem painel não produz achado": t_html_sem_painel_nao_inventa,
        "acha vários hospedeiros na mesma página": t_varios_hospedeiros,
        "fila: deduplica e nasce travada (não promovível)": t_dedup_e_trava_de_campo,
        "trava estrutural: não escreve no banco": t_trava_estrutural,
        "regressão do caso AM (painel da Defesa Civil)": t_caso_am_reproduz,
    })


def main() -> int:
    if "--anotar" in sys.argv:
        # §181: aplica à fila o que a abertura em navegador mostrou. O arquivo é uma lista de
        # anotações; a validação está em anotar_verificacao(), com vocabulário fechado.
        import json as _json
        caminho = sys.argv[sys.argv.index("--anotar") + 1]
        fila = ler(FILA, {"itens": []})
        with open(caminho, encoding="utf-8") as f:
            anotacoes = _json.load(f)
        aplicadas = anotar_verificacao(fila, anotacoes)
        gravar(FILA, fila)
        for i in aplicadas:
            marca = "coletar" if i.get("coletar") else "não coletar"
            print(f"  {i['uf']}/{i['setor']}: {i['conteudo'][:60]} → {marca}")
        print(f"{len(aplicadas)} item(ns) anotado(s) na fila.")
        return 0
    if "--autoteste" in sys.argv:
        return autoteste()
    setores = ["defesa_civil", "saude"]
    if "--setor" in sys.argv:
        setores = [sys.argv[sys.argv.index("--setor") + 1]]
    limite = None
    if "--limite" in sys.argv:
        limite = int(sys.argv[sys.argv.index("--limite") + 1])
    fila = carregar_fila()
    alvos = [(uf, s) for s in setores for uf in UFS][:limite]
    total = 0
    for uf, setor in alvos:
        novos = sondar(uf, setor, fila)
        total += len(novos)
        for n in novos:
            print(f"  + {uf}/{setor}: {n['tipo']} — {n['url'][:100]}")
    gravar(FILA, fila)
    print(f"\n{total} pista(s) de camada nova(s); fila com {len(fila['itens'])} item(ns).")
    print("Nenhuma entra no banco sem abertura em navegador e confirmação humana.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
