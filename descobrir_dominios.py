#!/usr/bin/env python3
"""Busca ATIVA do domínio oficial de cada UF, por setor (§184, 23/09/2026).

O PROBLEMA QUE ISTO RESOLVE. Até aqui o projeto chutava `defesacivil.<uf>.gov.br` e
`saude.<uf>.gov.br`, com sete correções feitas à mão no §179. O chute erra de três maneiras, e
todas viram lacuna falsa: o subdomínio não existe (a defesa civil da PB fica sob o Corpo de
Bombeiros), existe mas só responde com `www.` (o caso do PR, apontado pela editoria em 23/09), ou
responde e é outra coisa. Lacuna por endereço errado não é ausência de plano — é ausência de
busca, e o §11 exige que as duas sejam distinguíveis.

O QUE ESTE SCRIPT FAZ. Para cada UF e setor, testa uma lista declarada de padrões de endereço,
registra o que cada um respondeu (status, redirecionamento, título) e só aceita como domínio
oficial quem **se identifica como a instituição procurada** no título ou no corpo. O resultado vai
para `data/dominios_oficiais.json` com a trilha inteira — inclusive os candidatos que falharam,
porque saber que `cbm.<uf>.gov.br` não existe é informação, não ruído.

O QUE ESTE SCRIPT NÃO FAZ. Não procura plano, não lê documento, não toca em banco nem em nota.
Quem usa o domínio é `descobrir_planos.py` (e, por ele, a sonda de camada). Confiança `baixa`
nunca substitui o chute: um endereço que responde mas não se identifica é pior que nenhum, porque
daria aparência de busca feita.

REGRAS herdadas do §11: cliente identificado (`coletores_base.UA`), no máximo uma requisição por
domínio a cada 2 s, e 403 é recusa que se respeita (§170) — anotada, nunca contornada.

  python3 descobrir_dominios.py                 # todas as UFs, os dois setores
  python3 descobrir_dominios.py --uf PR --setor defesa_civil
  python3 descobrir_dominios.py --continuar     # retoma sem re-sondar quem já está registrado
  python3 descobrir_dominios.py --autoteste     # offline, sem rede
"""
import re
import sys
import time

from coletores_base import ler, gravar, hoje, log_busca, rodar_autoteste, buscar

ARQUIVO = "dominios_oficiais.json"

UFS = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
       "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]

# Padrões de endereço observados em portais estaduais brasileiros. Lista DECLARADA e certamente
# incompleta: padrão que falta só reduz recall, nunca inventa domínio. A ordem é a da chance de
# acerto, e a busca para no primeiro candidato de confiança alta — cada tentativa custa 2 s.
PADROES = {
    "defesa_civil": ["defesacivil.{uf}.gov.br", "www.defesacivil.{uf}.gov.br",
                     "cbm.{uf}.gov.br", "bombeiros.{uf}.gov.br", "www.bombeiros.{uf}.gov.br",
                     "cedec.{uf}.gov.br", "sedec.{uf}.gov.br", "defesacivil.{uf}.def.br",
                     "portal.defesacivil.{uf}.gov.br", "portal.{uf}.gov.br",
                     "www.{uf}.gov.br", "{uf}.gov.br"],
    # §187: "portal." é convenção comum no governo estadual brasileiro e faltava aqui. É ALARGAMENTO
    # DE ALCANCE, não correção de defeito, e a distinção está medida: o Plano Estadual de Saúde para
    # o El Niño de SP é servido com o MESMO sha256 em saude.sp.gov.br, www.saude.sp.gov.br e
    # portal.saude.sp.gov.br — o host escolhido pelo §184 sempre servia o documento. O que escondeu
    # o plano foi o caminho fundo e não linkado, e a busca não conferir o que o banco já registrava.
    "saude": ["saude.{uf}.gov.br", "www.saude.{uf}.gov.br", "portal.saude.{uf}.gov.br",
              "ses.{uf}.gov.br", "sesa.{uf}.gov.br", "sesau.{uf}.gov.br", "sus.{uf}.gov.br",
              "portal.{uf}.gov.br", "www.{uf}.gov.br", "{uf}.gov.br"],
}

# Marcas de identidade: o que a página tem de dizer para ser aceita como a instituição procurada.
# São EXPRESSÕES, não frases fixas. Defeito medido na primeira rodada (23/09/2026): a marca
# "secretaria de estado da saude" não casou com o título real da SES-MG, "Home | Secretaria De
# Estado De Saúde De Minas Gerais" — porque o órgão escreve "de saúde", não "da saúde". Uma
# preposição derrubou a identificação de um domínio que responde e se nomeia. Frase fixa é frágil
# por natureza; o que importa é "secretaria" perto de "saúde".
IDENTIDADE = {
    "defesa_civil": (r"defesa\s+civil", r"protecao\s+(e\s+)?defesa\s+civil",
                     r"\bcompdec\b", r"\bcedec\b", r"\bsedec\b",
                     r"corpo\s+de\s+bombeiros", r"\bcbm\b"),
    "saude": (r"secretaria[^.]{0,30}\bsaude\b", r"\bsaude\b[^.]{0,20}do\s+estado",
              r"vigilancia\s+em\s+saude", r"secretaria\s+estadual[^.]{0,20}saude"),
}


def _plano(t: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", (t or "").lower())
                   if unicodedata.category(c) != "Mn")


def titulo_de(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html or "", re.IGNORECASE | re.DOTALL)
    return re.sub(r"\s+", " ", m.group(1)).strip()[:160] if m else ""


def confianca(html: str, setor: str) -> tuple:
    """(confianca, onde) — 'alta' quando a identidade está no título, 'media' no corpo, 'baixa' fora.

    Título é o lugar em que o órgão se nomeia; corpo pode ser menção de passagem (um link para a
    Defesa Civil no portal do estado). Por isso o portal do estado, que é o último recurso da
    lista, dificilmente passa de 'media' — e é assim que deve ser."""
    titulo = _plano(titulo_de(html))
    corpo = _plano(re.sub(r"(?s)<[^>]+>", " ", html or ""))[:120000]
    marcas = [re.compile(m) for m in IDENTIDADE[setor]]
    if any(m.search(titulo) for m in marcas):
        return "alta", "titulo"
    if any(m.search(corpo) for m in marcas):
        return "media", "corpo"
    return "baixa", "nenhuma"


def sondar_candidato(dominio: str, setor: str, buscar_fn) -> dict:
    """Uma tentativa. Nunca levanta: a falha é o dado. 403 fica anotado como recusa (§170)."""
    reg = {"dominio": dominio, "tentado_em": hoje()}
    try:
        corpo = buscar_fn(f"https://{dominio}/", timeout=25)
    except Exception as e:  # noqa: BLE001
        codigo = getattr(e, "code", None)
        reg.update({"respondeu": False, "erro": f"{type(e).__name__}: {str(e)[:70]}",
                    "http": codigo,
                    "recusa": codigo in (401, 402, 403, 429, 451)})
        return reg
    html = corpo.decode("utf-8", "replace")
    conf, onde = confianca(html, setor)
    reg.update({"respondeu": True, "http": 200, "bytes": len(corpo), "titulo": titulo_de(html),
                "confianca": conf, "identidade_em": onde})
    return reg


def escolher(tentativas: list) -> dict | None:
    """O melhor candidato: identidade no título vence identidade no corpo; ninguém com confiança
    'baixa' é escolhido — endereço que responde sem se identificar daria aparência de busca feita."""
    ordem = {"alta": 0, "media": 1}
    validos = [t for t in tentativas if t.get("respondeu") and t.get("confianca") in ordem]
    if not validos:
        return None
    return sorted(validos, key=lambda t: (ordem[t["confianca"]], tentativas.index(t)))[0]


def motivo_da_falta(tentativas: list) -> str:
    """Por que não houve domínio — em vocabulário que distingue o que é diferente.

    "Nenhum candidato se identificou" escondia coisas muito distintas: endereço que não existe no
    DNS, certificado que não valida, caminho 404 e recusa explícita. Sem essa distinção, um estado
    cujo portal está com TLS quebrado aparece igual a um estado que não tem defesa civil na web —
    e o §11 exige que ausência de busca e ausência de dado nunca se confundam."""
    respondeu = [t for t in tentativas if t.get("respondeu")]
    dns = sum(1 for t in tentativas if "getaddrinfo" in str(t.get("erro", "")))
    tls = sum(1 for t in tentativas if "CERTIFICATE" in str(t.get("erro", "")).upper())
    recusa = sum(1 for t in tentativas if t.get("recusa"))
    quatro04 = sum(1 for t in tentativas if t.get("http") in (404, 410))
    partes = []
    if respondeu:
        partes.append(f"{len(respondeu)} respondeu(ram) sem se identificar como a instituição")
    if dns:
        partes.append(f"{dns} endereço(s) não existe(m) no DNS")
    if tls:
        partes.append(f"{tls} com certificado TLS que não valida (não se contorna)")
    if quatro04:
        partes.append(f"{quatro04} com caminho inexistente (404/410)")
    if recusa:
        partes.append(f"{recusa} recusou(aram) acesso (§170: recusa se respeita)")
    return "; ".join(partes) or "nenhuma tentativa registrada"


def buscar_uf(uf: str, setor: str, buscar_fn=buscar, pausa: float = 2.0) -> dict:
    """Testa os padrões declarados e devolve o registro da UF/setor, com a trilha inteira."""
    tentativas = []
    for padrao in PADROES[setor]:
        dominio = padrao.format(uf=uf.lower())
        if any(t["dominio"] == dominio for t in tentativas):
            continue
        t = sondar_candidato(dominio, setor, buscar_fn)
        tentativas.append(t)
        if t.get("confianca") == "alta":
            break                      # não bater em mais nada: já se identificou no título
        if pausa:
            time.sleep(pausa)
    escolhido = escolher(tentativas)
    return {"uf": uf, "setor": setor, "verificado_em": hoje(),
            "dominio": escolhido["dominio"] if escolhido else None,
            "confianca": escolhido["confianca"] if escolhido else None,
            "titulo": escolhido.get("titulo") if escolhido else None,
            "motivo_sem_dominio": None if escolhido else motivo_da_falta(tentativas),
            "tentativas": tentativas}


def autoteste() -> int:
    PAGINA_DC = "<html><head><title>Defesa Civil do Paraná</title></head><body>Notícias</body></html>"
    PAGINA_PORTAL = ("<html><head><title>Governo do Estado</title></head><body>"
                     "<a href='/defesa-civil'>Defesa Civil</a></body></html>")
    PAGINA_QUALQUER = "<html><head><title>Detran</title></head><body>Habilitação</body></html>"

    def fabricar(respostas):
        def fn(url, timeout=0):
            host = url.split("//", 1)[1].split("/", 1)[0]
            if host not in respostas:
                raise OSError("getaddrinfo failed")
            r = respostas[host]
            if isinstance(r, int):
                e = OSError(f"HTTP Error {r}")
                e.code = r
                raise e
            return r.encode()
        return fn

    def t_titulo_vence():
        r = buscar_uf("PR", "defesa_civil", fabricar({"www.defesacivil.pr.gov.br": PAGINA_DC}), pausa=0)
        return r["dominio"] == "www.defesacivil.pr.gov.br" and r["confianca"] == "alta"

    def t_para_no_primeiro_de_confianca_alta():
        r = buscar_uf("PR", "defesa_civil", fabricar({"defesacivil.pr.gov.br": PAGINA_DC,
                                                      "cbm.pr.gov.br": PAGINA_DC}), pausa=0)
        return len(r["tentativas"]) == 1 and r["dominio"] == "defesacivil.pr.gov.br"

    def t_corpo_serve_quando_nao_ha_titulo():
        r = buscar_uf("XX", "defesa_civil", fabricar({"www.xx.gov.br": PAGINA_PORTAL}), pausa=0)
        return r["confianca"] == "media" and r["dominio"] == "www.xx.gov.br"

    def t_pagina_que_nao_se_identifica_nao_e_escolhida():
        r = buscar_uf("XX", "saude", fabricar({"saude.xx.gov.br": PAGINA_QUALQUER}), pausa=0)
        # §184: o motivo passa a distinguir o que é diferente — responder sem se identificar não é
        # o mesmo que DNS inexistente, certificado inválido, 404 ou recusa.
        return (r["dominio"] is None and "sem se identificar" in r["motivo_sem_dominio"]
                and "DNS" in r["motivo_sem_dominio"])

    def t_recusa_fica_anotada_e_nao_vira_dominio():
        r = buscar_uf("XX", "saude", fabricar({"saude.xx.gov.br": 403}), pausa=0)
        t = [x for x in r["tentativas"] if x["dominio"] == "saude.xx.gov.br"][0]
        return t["recusa"] is True and r["dominio"] is None

    def t_nada_responde_vira_motivo_declarado():
        r = buscar_uf("XX", "saude", fabricar({}), pausa=0)
        return r["dominio"] is None and "DNS" in r["motivo_sem_dominio"]

    def t_motivo_separa_tls_de_ausencia():
        """Certificado que não valida é achado sobre o sítio, não ausência de instituição."""
        def buscar_tls(url, timeout=0):
            raise OSError("[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed")
        r = buscar_uf("XX", "saude", buscar_tls, pausa=0)
        return "TLS" in r["motivo_sem_dominio"] and "não se contorna" in r["motivo_sem_dominio"]

    def t_identidade_tolera_preposicao():
        """O defeito real de 23/09: "Secretaria De Estado De Saúde" não casava com marca fixa."""
        return (confianca("<html><head><title>Home | Secretaria De Estado De Saúde De Minas "
                          "Gerais</title></head></html>", "saude")[0] == "alta"
                and confianca("<html><head><title>Portal MG</title></head><body>Notícias</body>"
                              "</html>", "saude")[0] == "baixa")

    def t_ordem_de_prova_em_dominio_para():
        """A ordem do §184 dentro de descobrir_planos: título > curadoria > corpo > palpite."""
        import descobrir_planos as dp
        real_ler = dp.ler
        try:
            def ler_falso(nome, padrao=None):
                if nome == "dominios_oficiais.json":
                    return {"alvos": {
                        "ZZ/defesa_civil": {"dominio": "achado-alta.zz.gov.br", "confianca": "alta"},
                        "YY/defesa_civil": {"dominio": "achado-media.yy.gov.br", "confianca": "media"},
                    }}
                return real_ler(nome, padrao)
            dp.ler = ler_falso
            curados = dp.DOMINIOS_CONHECIDOS["defesa_civil"]
            curados["ZZ"] = "curado.zz.gov.br"
            curados["YY"] = "curado.yy.gov.br"
            alta_vence = dp.dominio_para("ZZ", "defesa_civil") == "achado-alta.zz.gov.br"
            curadoria_vence_media = dp.dominio_para("YY", "defesa_civil") == "curado.yy.gov.br"
            curados.pop("YY")
            media_vence_palpite = dp.dominio_para("YY", "defesa_civil") == "achado-media.yy.gov.br"
            palpite_por_ultimo = dp.dominio_para("WW", "defesa_civil") == "defesacivil.ww.gov.br"
            curados.pop("ZZ", None)
            return alta_vence and curadoria_vence_media and media_vence_palpite and palpite_por_ultimo
        finally:
            dp.ler = real_ler

    def t_padrao_cobre_o_host_do_plano_de_sp():
        """§187: as grafias com "portal." entram no leque, antes do palpite genérico www.{uf}. Trava de
        alcance, não de defeito — medido em 23/09, os três hosts de SP servem o mesmo documento."""
        alvos = [x.format(uf="sp") for x in PADROES["saude"]]
        return ("portal.saude.sp.gov.br" in alvos
                and alvos.index("portal.saude.sp.gov.br") < alvos.index("www.sp.gov.br"))

    return rodar_autoteste({
        "§187 padrão de saúde cobre portal.saude.<uf>": t_padrao_cobre_o_host_do_plano_de_sp,
        "ordem de prova: título > curadoria > corpo > palpite": t_ordem_de_prova_em_dominio_para,
        "identidade no título escolhe o domínio": t_titulo_vence,
        "para de bater no primeiro de confiança alta": t_para_no_primeiro_de_confianca_alta,
        "identidade no corpo serve como segunda opção": t_corpo_serve_quando_nao_ha_titulo,
        "página que não se identifica não é escolhida": t_pagina_que_nao_se_identifica_nao_e_escolhida,
        "403 fica anotado como recusa e não vira domínio": t_recusa_fica_anotada_e_nao_vira_dominio,
        "nenhuma resposta vira motivo declarado": t_nada_responde_vira_motivo_declarado,
        "motivo separa certificado inválido de ausência": t_motivo_separa_tls_de_ausencia,
        "identidade tolera a preposição (caso real da SES-MG)": t_identidade_tolera_preposicao,
    })


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    ufs = [sys.argv[sys.argv.index("--uf") + 1].upper()] if "--uf" in sys.argv else UFS
    setores = [sys.argv[sys.argv.index("--setor") + 1]] if "--setor" in sys.argv else list(PADROES)
    d = ler(ARQUIVO, {"_governanca": "Domínio oficial por UF e setor, achado por busca ativa (§184). "
                                     "Trilha completa das tentativas, inclusive as que falharam. "
                                     "Insumo de descobrir_planos.dominio_para(); nunca lido pelo cálculo "
                                     "da nota.", "alvos": {}})
    achados = faltando = 0
    continuar = "--continuar" in sys.argv   # retoma de onde parou: alvo já registrado não é re-sondado
    refazer_faltantes = "--refazer-sem-dominio" in sys.argv
    for uf in ufs:
        for setor in setores:
            registrado = d["alvos"].get(f"{uf}/{setor}")
            if refazer_faltantes and registrado and registrado.get("dominio"):
                continue
            if continuar and registrado and not refazer_faltantes:
                continue
            r = buscar_uf(uf, setor)
            d["alvos"][f"{uf}/{setor}"] = r
            if r["dominio"]:
                achados += 1
                print(f"  ✓ {uf}/{setor:12s} {r['dominio']:34s} [{r['confianca']}] {str(r['titulo'])[:48]}")
            else:
                faltando += 1
                print(f"  — {uf}/{setor:12s} sem domínio: {r['motivo_sem_dominio']}")
            log_busca("busca ativa de domínio", 1, [t["dominio"] for t in r["tentativas"]],
                      "pista" if r["dominio"] else "consultado sem achado", uf=uf,
                      resultados=(f"{r['dominio']} (confiança {r['confianca']})" if r["dominio"]
                                  else r["motivo_sem_dominio"]),
                      n_resultados=1 if r["dominio"] else 0)
            gravar(ARQUIVO, d)          # grava a cada alvo: rodada interrompida não perde o que achou
    print(f"\n{achados} domínio(s) identificado(s), {faltando} sem domínio (lacuna declarada).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
