#!/usr/bin/env python3
"""Aplica no banco as promoções do juiz automático — Etapa 7, com rede de proteção.

Item 1 do bloco das 19:50 de 28/09/2026 (decisão da central). Não é decisão nova: é a Etapa 7 do
handover do juiz, decidida pela editoria em 27/09 — o juiz promove quando **todos** os critérios
passam sobre o documento primário.

O QUE FALTAVA
-------------
O juiz gravava `promove: true` em `data/promocoes_automaticas.json` e **nada lia aquele campo**.
Quem aplicava no banco era `julgar_e_aplicar_descobertas.py`, que só olha pistas de imprensa com
status `pendente_confirmacao_documento`. O veredito do codebook morria no arquivo.

A SEQUÊNCIA, E O QUE A PROTEGE
------------------------------
  backup em memória → aplica → `recalcular_mare.py --write` → suíte de portões
  portão vermelho → restaura os bytes originais e devolve a pista com o erro escrito

A rede de proteção é a mesma de `julgar_e_aplicar_descobertas.py`, testada desde 31/08/2026: ela
guarda também `recalcular_mare.py` e as páginas que a aplicação estadual toca, porque reverter pela
metade é pior que não aplicar.

SÓ A VERSÃO EM VIGOR DO CODEBOOK
--------------------------------
Aplica apenas vereditos cujo `codebook` é o em vigor e que não estejam superados. Em 28/09/2026 a
regra frouxa de objeto ex-ante promoveu **quatro registros falsos de cinco** (§286); eles ficaram no
arquivo, marcados como superados, e esta trava é o que impede que voltem pelo caminho novo.

PROVENIÊNCIA
------------
Cada registro aplicado carrega `hash_evidencia`, `url`, `data`, `categoria`, o `pista_id` e a versão
do codebook. Os critérios com trecho ficam em `promocoes_automaticas.json`, ligados pelo `pista_id`
— é esse par que a auditoria amostral semanal lê. Errata humana reverte com uma linha: basta apagar
o registro do banco; a decisão continua no registro, dizendo o que foi feito e por quê.

USO
  python3 aplicar_promocoes_do_juiz.py                 # relatório, nada escrito
  python3 aplicar_promocoes_do_juiz.py --aplicar
  python3 aplicar_promocoes_do_juiz.py --autoteste
"""
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

REGISTRO = RAIZ / "data" / "promocoes_automaticas.json"
MUNICIPIOS = RAIZ / "data" / "municipios.json"
PONTOS = RAIZ / "data" / "pontos_mapa.json"


def dominio_divergente(veredito: dict, dono) -> bool:
    """O documento está em domínio oficial de OUTRO município? Função pura dado o dono.

    09/10/2026 (A1-01). Três dos trinta vereditos que promoveram no registro creditam município
    que não é o dono do domínio do documento:

        Candeias/MG     ← prefeitura.candeias.ba.gov.br   (outra UF)
        Rio do Oeste/SC ← defesacivil.taio.sc.gov.br      (o plano é de Taió)
        Santa Rosa/RS   ← trindadedosul.rs.gov.br         (o plano é de Trindade do Sul)

    O domínio é prova mais forte que um nome no meio do texto, e o corretor de atribuição já
    reatribui a pista antes de julgar. Esta é a rede: aplicar no banco um par que o próprio
    domínio contradiz grava registro falso, e registro falso pontua.

    Host que não resolve município nenhum (diário consorciado, domínio federal, armazenamento)
    devolve `None` e não decide nada aqui — quem cuida disso são as etapas 0 e 3 do codebook.
    """
    if not dono:
        return False
    nome = str(veredito.get("municipio") or "").strip().lower()
    uf = str(veredito.get("uf") or "").strip().upper()
    return (str(dono.get("uf") or "").upper() != uf
            or str(dono.get("nome") or "").strip().lower() != nome)


def aplicaveis(decisoes: list, versao: str, resolver=None) -> list:
    """Vereditos que promovem, na versão em vigor, ainda não aplicados nem superados.

    09/10/2026 (A1-29): `nao_aplicado` também exclui — a marca existe para dizer que a decisão
    não vai ao banco, e sem o filtro Taió tinha três decisões vivas para a mesma URL.
    09/10/2026 (A1-01): veredito cujo domínio aponta outro município não é aplicável.
    """
    if resolver is None:
        try:
            from municipio_do_dominio import municipio_de as resolver
        except ImportError:
            def resolver(_url):
                return None
    fora = []
    for v in decisoes:
        if not (v.get("promove") and v.get("codebook") == versao):
            continue
        if v.get("superada_por") or v.get("aplicado_em") or v.get("nao_aplicado"):
            continue
        if dominio_divergente(v, resolver(v.get("url") or "")):
            print(f"   ! nao aplicado: {v.get('municipio')}/{v.get('uf')} — o documento esta em "
                  f"dominio oficial de outro municipio")
            continue
        fora.append(v)
    return fora


def ja_no_banco(municipios: list, nome: str, uf: str) -> bool:
    """Duplicar registro é pior que não aplicar: a revisão humana decide se é atualização."""
    n, u = str(nome or "").strip().lower(), str(uf or "").strip().upper()
    return any(str(m.get("nome", "")).strip().lower() == n
               and str(m.get("uf", "")).strip().upper() == u for m in municipios)


def preservar_o_documento(url: str, origem: str = "juiz_automatico"):
    """Preserva o documento do registro pela porta canônica e devolve o hash. None se não der.

    03/10/2026: o portão de evidências reprovou a primeira promoção do caminho novo — "1 de 93
    registro(s) pontuável(is) com URL sem evidência preservada — BLOQUEANTE". Estava certo: o juiz
    calcula o hash do TEXTO que julgou e, de propósito, **não preserva** (§: duas portas gravando a
    mesma chave é como se perde prova). Quem preserva é quem aplica — e no caminho do plano sem ato
    não havia ninguém antes, porque o documento não vinha de um coletor que já o tivesse baixado.

    A porta é `coletores_base.preservar_evidencia`, a mesma de todos os coletores: ela guarda o
    binário, indexa por sha256 em `data/evidencias.json` e pede snapshot ao Wayback acima do teto.
    Falha de rede devolve None, e aí a promoção não é aplicada — registro pontuável sem evidência
    é exatamente o que o portão existe para impedir.
    """
    if not url:
        return None
    try:
        from coletores_base import buscar, preservar_evidencia
        corpo = buscar(url)
        ext = (str(url).lower().split("?")[0].rsplit(".", 1)[-1] or "html")[:5]
        if ext not in ("pdf", "doc", "docx", "odt", "rtf", "html", "htm", "txt"):
            ext = "html"
        return preservar_evidencia(corpo, url, ext, origem)
    except Exception as e:  # noqa: BLE001
        print(f"   ! evidência não preservada ({type(e).__name__}): {str(e)[:90]}")
        return None


def registro_do_veredito(v: dict, lat, lon, canal: str, fonte_base: str, hoje: str) -> dict:
    """O registro do banco, com a proveniência que permite conferir a decisão depois.

    `categoria` vem do veredito — não é fixa. A versão anterior deste caminho, em
    `julgar_e_aplicar_descobertas.py`, gravava sempre "plano", e um `plano_antigo` entraria como
    plano novo, mudando o que o índice conta."""
    registro = {
        "nome": v["municipio"], "uf": v["uf"], "categoria": v["categoria"],
        "documento": documento_do_veredito(v),
        "data": v.get("data"),
        "fonte": f"{fonte_base} — ato lido e classificado pelo juiz automático em {hoje} "
                 f"(codebook {v.get('codebook')}); critérios em promocoes_automaticas.json",
        "url": v.get("url"), "lat": lat, "lon": lon, "canal": canal,
        "hash_evidencia": v.get("hash_evidencia"),
        "pista_id": v.get("pista_id"), "codebook": v.get("codebook"),
    }
    # DECISÃO DA EDITORIA, 03/10/2026: o plano publicado sem ato de aprovação localizado conta no
    # degrau da leitura, **com a marca visível na ficha**. A marca é do REGISTRO, e não do texto da
    # fonte: quem lê a ficha precisa saber que o documento é o plano publicado e que o ato que o
    # aprova não foi localizado — e a marca sai quando o ato aparecer, numa rodada seguinte.
    if v.get("sem_ato_de_aprovacao"):
        registro["sem_ato_de_aprovacao"] = True
        registro["marca_na_ficha"] = "sem ato de aprovação localizado"
        registro["fonte"] = (f"{fonte_base} — plano publicado em domínio oficial do ente, lido e "
                             f"classificado pelo juiz automático em {hoje} (codebook "
                             f"{v.get('codebook')}); ato de aprovação não localizado até o corte; "
                             "critérios em promocoes_automaticas.json")
    return registro


RE_SUJEIRA = re.compile(r"P[áa]gina\s+\d+\s+de\s+\d+|o documento [ÉE] o instrumento|\.\.\.\.|……", re.IGNORECASE)
RE_FIM_DE_TITULO = re.compile(
    r"^(.*?(?:\d{4}(?:\s*[-/]\s*\d{2,4})?|-\s*[A-Z]{2}\b))", re.DOTALL)
RE_TITULO_DE_PLANO = re.compile(
    r"(PLANCON[^\n\r.;]{0,90}|PLANO\s+(?:MUNICIPAL\s+)?DE\s+CONTING[ÊE]NCIA[^\n\r.;]{0,90})",
    re.IGNORECASE)

def titulo_de_plano(texto: str) -> str:
    """O TÍTULO do plano, achado no texto — ou vazio.

    08/10/2026 (A1-06, A4-08). O campo `documento` da ficha vinha do trecho do objeto, e no
    caminho do "plano publicado em domínio oficial" não existe objeto nenhum: o trecho era sobra
    de página. A ficha publicou "o documento É o instrumento nomeado: tanhaém…", "neste Plano.
    11/08/2026 Página 3 de 72…" e "a Católica 8 1.5. INSTRUÇÕES PARA USO…".
    """
    m = RE_TITULO_DE_PLANO.search(" ".join(str(texto or "").split()))
    if not m:
        return ""
    titulo = " ".join(m.group(1).split()).strip(" -–:;,")
    # O título termina onde o documento o termina: no ano (ou no biênio) ou na sigla da UF. O que
    # vem depois é o texto da página seguinte — nome de assinante, número de item, cabeçalho — e
    # entrava no campo porque a janela do casamento é fixa.
    corte = RE_FIM_DE_TITULO.match(titulo)
    if not corte:
        # Sem ano e sem sigla de UF, não há onde o título termine: o que a janela pegou é meio de
        # frase ("Plano de Contingência decorre da operacionalização…"). Devolver isso seria
        # trocar uma sobra de página por outra. Quem chama cai na forma genérica, que é verdadeira.
        return ""
    titulo = corte.group(1).strip(" -–:;,")
    return titulo if len(titulo) >= 12 else ""


def documento_do_veredito(v: dict) -> str:
    """A ementa curta do ato — ou, no caminho do plano sem ato, o TÍTULO do documento.

    A ementa sai do trecho do objeto ex-ante (Etapa 4), que desde o §286 mostra o verbo e o
    instrumento juntos. Quando esse trecho não existe ou vem com sobra de página — marcador
    "Página N de M", frase interna do juiz, reticências de corte, minúscula inicial —, o campo
    passa a ser o título do documento, na forma aprovada "{Título} — {órgão}, {ano}".
    """
    objeto = ((v.get("criterios") or {}).get("4_natureza") or {}).get("objeto") or ""
    objeto = " ".join(str(objeto).split())
    if objeto and not RE_SUJEIRA.search(objeto) and not objeto[:1].islower():
        return objeto[:177] + "…" if len(objeto) > 180 else objeto
    for f in (objeto, v.get("trecho") or "", v.get("titulo") or ""):
        titulo = titulo_de_plano(f)
        if titulo:
            orgao = v.get("orgao") or (f"Prefeitura de {v['municipio']}" if v.get("municipio")
                                       else "")
            ano = str(v.get("data") or "")[-4:]
            cabeca = " — ".join([titulo] + ([orgao] if orgao else []))
            return f"{cabeca}, {ano}" if ano.isdigit() else cabeca
    # A forma genérica só vale quando o próprio texto PROVA que o documento é um plano de
    # contingência. Sem essa prova, nada de nome: vale a frase que diz o que se tem, que é a
    # classificação — inventar título é pior que não ter título.
    prova_de_plano = re.search(r"plano\s+de\s+conting[êe]ncia|PLANCON", objeto, re.IGNORECASE)
    if prova_de_plano and v.get("municipio"):
        ano = str(v.get("data") or "")[-4:]
        cauda = f", {ano}" if ano.isdigit() else ""
        return f"Plano de contingência municipal — Prefeitura de {v['municipio']}{cauda}"
    return f"ato classificado como {v.get('categoria')} pelo juiz automático"


def autoteste() -> int:
    casos = []
    V = "1.1 (28/09/2026)"
    base = {"promove": True, "codebook": V, "municipio": "Serra", "uf": "ES",
            "categoria": "plano_antigo", "data": "30/12/2025", "url": "https://x.gov.br/a.pdf",
            "hash_evidencia": "h" * 64, "pista_id": "abc",
            "criterios": {"4_natureza": {"objeto": "Fica instituído o Plano Municipal de Proteção"}}}

    # 08/10/2026 (A1-06, A4-08): o campo `documento` é o título do documento, nunca sobra de
    # página. Os quatro casos abaixo são os quatro registros reais que a ficha publicou errado.
    casos.append(("ementa limpa continua sendo a ementa",
                  documento_do_veredito(base) == "Fica instituído o Plano Municipal de Proteção"))
    casos.append(("marcador de página vira título com órgão e ano",
                  documento_do_veredito({"municipio": "Umuarama", "data": "2026", "criterios": {
                      "4_natureza": {"objeto": "neste Plano. 11/08/2026 Página 3 de 72 Plano de "
                                               "contingência do município de Umuarama - PR 1.2."}}})
                  == "Plano de contingência do município de Umuarama - PR — Prefeitura de "
                     "Umuarama, 2026"))
    casos.append(("frase interna do juiz vira o PLANCON do documento",
                  documento_do_veredito({"municipio": "Itanhaém", "data": "2024", "criterios": {
                      "4_natureza": {"objeto": "o documento É o instrumento nomeado: tanhaém "
                                               "Secretaria Municipal PLANCON PLANO DE CONTIGÊNCIA "
                                               "2024-2025 Tiago"}}})
                  == "PLANCON PLANO DE CONTIGÊNCIA 2024-2025 — Prefeitura de Itanhaém, 2024"))
    casos.append(("meio de frase sem ano nem UF cai na forma genérica, não em outra sobra",
                  documento_do_veredito({"municipio": "Celso Ramos", "data": "2022", "criterios": {
                      "4_natureza": {"objeto": "a Católica 8 1.5. INSTRUÇÕES PARA USO E "
                                               "ATUALIZAÇÃO DO PLANO A efetiva aplicação do "
                                               "Plano de Contingência decorre"}}})
                  == "Plano de contingência municipal — Prefeitura de Celso Ramos, 2022"))
    sem_dono = lambda _u: None            # noqa: E731 — resolvedor nulo, para as travas puras
    casos.append(("veredito da versão em vigor é aplicável",
                  len(aplicaveis([base], V, resolver=sem_dono)) == 1))
    # 09/10/2026 (A1-01): domínio de outro município derruba a aplicação.
    taio = {"nome": "Taió", "uf": "SC", "ibge": "4217808"}
    casos.append(("domínio de outro município não é aplicável",
                  aplicaveis([dict(base, municipio="Rio do Oeste", uf="SC")], V,
                             resolver=lambda _u: taio) == []))
    casos.append(("domínio do próprio município é aplicável",
                  len(aplicaveis([dict(base, municipio="Taió", uf="SC")], V,
                                 resolver=lambda _u: taio)) == 1))
    casos.append(("domínio que não resolve município não decide nada",
                  len(aplicaveis([base], V, resolver=sem_dono)) == 1))
    casos.append(("UF divergente com mesmo nome não é aplicável",
                  aplicaveis([dict(base, municipio="Candeias", uf="MG")], V,
                             resolver=lambda _u: {"nome": "Candeias", "uf": "BA"}) == []))
    # 09/10/2026 (A1-29): `nao_aplicado` exclui.
    casos.append(("veredito marcado nao_aplicado não volta ao banco",
                  aplicaveis([dict(base, nao_aplicado=True)], V, resolver=sem_dono) == []))
    casos.append(("veredito de versão anterior NÃO é aplicável",
                  aplicaveis([dict(base, codebook="1.0 (27/09/2026)")], V) == []))
    casos.append(("veredito superado NÃO é aplicável",
                  aplicaveis([dict(base, superada_por={"codebook": V})], V) == []))
    casos.append(("veredito já aplicado NÃO volta",
                  aplicaveis([dict(base, aplicado_em="2026-09-28")], V) == []))
    casos.append(("recusa nunca é aplicável",
                  aplicaveis([dict(base, promove=False)], V) == []))

    mun = [{"nome": "Serra", "uf": "ES"}]
    casos.append(("município já no banco é reconhecido", ja_no_banco(mun, "serra", "es")))
    casos.append(("município ausente não é falso positivo", not ja_no_banco(mun, "Vitória", "ES")))

    r = registro_do_veredito(base, -20.1, -40.3, "DOM", "Diário oficial municipal", "28/09/2026")
    casos.append(("a categoria vem do veredito, não é fixa em 'plano'",
                  r["categoria"] == "plano_antigo"))
    casos.append(("o registro carrega hash, url e data",
                  r["hash_evidencia"] == "h" * 64 and r["url"].endswith("a.pdf")
                  and r["data"] == "30/12/2025"))
    casos.append(("o registro liga à decisão pelo pista_id e pelo codebook",
                  r["pista_id"] == "abc" and r["codebook"] == V))
    # 03/10/2026: a marca da decisão da editoria viaja do veredito para o registro, e é ela que a
    # ficha mostra. Registro sem a marca não pode ganhá-la por descuido, e com a marca não pode
    # perdê-la — os dois casos abaixo guardam as duas metades.
    r_marca = registro_do_veredito(dict(base, sem_ato_de_aprovacao=True), -1, -2, "c", "f", "01/01/2026")
    casos.append(("plano sem ato: o registro leva a marca para a ficha",
                  r_marca.get("sem_ato_de_aprovacao") is True
                  and r_marca.get("marca_na_ficha") == "sem ato de aprovação localizado"))
    casos.append(("plano sem ato: a fonte do registro diz que o ato não foi localizado",
                  "ato de aprovação não localizado até o corte" in r_marca["fonte"]))
    casos.append(("preservar_o_documento sem URL devolve None, e não quebra",
                  preservar_o_documento("") is None))
    casos.append(("plano COM ato não ganha a marca",
                  "sem_ato_de_aprovacao" not in r and "marca_na_ficha" not in r))
    casos.append(("a fonte diz que foi o juiz, com a versão",
                  "juiz automático" in r["fonte"] and "1.1" in r["fonte"]))
    casos.append(("a ementa sai do objeto ex-ante",
                  r["documento"].startswith("Fica instituído o Plano Municipal")))
    sem_objeto = registro_do_veredito(dict(base, criterios={}), 0, 0, "DOM", "x", "28/09/2026")
    # 09/10/2026 (A1-02): trava ESTRUTURAL do desempacotamento. `rodar_portoes()` devolve
    # `(ok, saida)`; atribuir a tupla inteira a `ok` torna a rede de protecao morta, porque tupla
    # de dois elementos e sempre verdadeira. A trava le o proprio fonte: foi assim que o defeito
    # passou em revisao, e ler o fonte e o unico jeito de pegar o mesmo erro de novo sem rodar a
    # aplicacao de verdade.
    fonte_deste = pathlib.Path(__file__).read_text(encoding="utf-8")
    atribuicoes = [l.strip() for l in fonte_deste.splitlines()
                   if l.strip().endswith("= rodar_portoes()")]
    casos.append(("o retorno de rodar_portoes e desempacotado em (ok, saida)",
                  atribuicoes == ["ok, saida_portoes = rodar_portoes()"]))
    import inspect
    from julgar_e_aplicar_descobertas import rodar_portoes as _rp
    casos.append(("rodar_portoes continua devolvendo dois valores",
                  "return True," in inspect.getsource(_rp)
                  and "return False," in inspect.getsource(_rp)))
    casos.append(("sem objeto, a ementa diz o que é sem inventar texto",
                  "classificado como plano_antigo" in sem_objeto["documento"]))

    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos, sem rede e sem escrita.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()

    from coletores_base import gravar_em, hoje_editorial
    from juiz import CODEBOOK_VERSAO
    from julgar_e_aplicar_descobertas import (backup_dados, buscar_lat_lon, canal_e_fonte,
                                              restaurar_dados, rodar_portoes)

    doc = json.loads(REGISTRO.read_text(encoding="utf-8"))
    decisoes = doc.get("decisoes") or []
    alvo = aplicaveis(decisoes, CODEBOOK_VERSAO)
    print(f"{len(alvo)} promoção(ões) na versão em vigor do codebook ({CODEBOOK_VERSAO}), "
          f"de {len(decisoes)} decisão(ões) no registro")
    for v in alvo:
        print(f"  {v['municipio']}/{v['uf']} · {v['categoria']} · {v.get('data')} · {v.get('url')}")
    if not alvo:
        print("nada a aplicar")
        return 0

    if "--aplicar" not in sys.argv:
        print("relatório apenas; nada escrito (use --aplicar)")
        return 0

    hoje = hoje_editorial()
    backup = backup_dados()
    municipios = json.loads(MUNICIPIOS.read_text(encoding="utf-8"))
    pontos = json.loads(PONTOS.read_text(encoding="utf-8"))
    aplicados, recusados = [], []

    for v in alvo:
        if not v.get("ibge") and not v.get("municipio"):
            recusados.append((v, "veredito sem território — não dá para posicionar"))
            continue
        if ja_no_banco(municipios, v["municipio"], v["uf"]):
            recusados.append((v, "já consta no banco — abstenção registrada (atualização não se presume)"))
            continue
        lat, lon = buscar_lat_lon(v["municipio"], v["uf"])
        if lat is None:
            recusados.append((v, "não consta na referência do IBGE — sem posição no mapa"))
            continue
        canal, fonte_base = canal_e_fonte(v.get("url") or "")
        # A EVIDÊNCIA vem antes do registro: registro pontuável com URL e sem evidência preservada
        # é vermelho no portão 26, e com razão — a prova é o que permite conferir a decisão depois.
        # O hash do documento preservado substitui o hash do texto julgado no registro: o primeiro
        # é do arquivo que ficou guardado, e é esse que a auditoria vai abrir.
        hash_preservado = preservar_o_documento(v.get("url") or "")
        if not hash_preservado:
            recusados.append((v, "documento não pôde ser preservado — registro pontuável exige "
                                 "evidência guardada (portão 26)"))
            continue
        v["hash_evidencia"] = hash_preservado
        municipios.append(registro_do_veredito(v, lat, lon, canal, fonte_base,
                                               hoje.strftime("%d/%m/%Y")))
        pontos.append({"nome": v["municipio"], "uf": v["uf"], "categoria": v["categoria"],
                       "lat": lat, "lon": lon, "fase": 3})
        aplicados.append(v)

    for v, motivo in recusados:
        print(f"  não aplicado: {v['municipio']}/{v['uf']} — {motivo}")
        v["nao_aplicado"] = {"em": hoje.isoformat(), "motivo": motivo}

    if not aplicados:
        print("nenhuma promoção aplicável nesta passada; banco intacto")
        gravar_em(REGISTRO, doc)
        return 0

    gravar_em(MUNICIPIOS, municipios)
    gravar_em(PONTOS, pontos)
    print(f"{len(aplicados)} registro(s) escrito(s); rodando recálculo e portões antes de confirmar")

    # 09/10/2026 (A1-02): `rodar_portoes()` devolve a TUPLA `(ok, saida)`, e aqui ela era atribuida
    # inteira a `ok`. Tupla de dois elementos e sempre verdadeira — a rede de protecao descrita no
    # cabecalho deste arquivo NUNCA disparou: portao vermelho confirmava a aplicacao em vez de
    # desfaze-la. O motivo agora guarda a saida do portao que reprovou, porque reverter sem dizer o
    # que reprovou obriga a repetir a rodada para descobrir.
    ok, saida_portoes = rodar_portoes()
    if not ok:
        restaurar_dados(backup)
        ultima = [l for l in (saida_portoes or "").splitlines() if l.strip()][-6:]
        for v in aplicados:
            v["revertido_por_portao"] = {"em": hoje.isoformat(),
                                         "motivo": "portão vermelho depois da aplicação",
                                         "saida": chr(10).join(ultima)}
        gravar_em(REGISTRO, doc)
        print("X portão vermelho — tudo restaurado em disco; as decisões guardam o erro")
        for l in ultima:
            print(f"   | {l}")
        return 1

    for v in aplicados:
        v["aplicado_em"] = hoje.isoformat()
    gravar_em(REGISTRO, doc)
    print(f"OK {len(aplicados)} promoção(ões) aplicada(s) e confirmada(s) pelos portões")
    return 0


if __name__ == "__main__":
    sys.exit(main())
