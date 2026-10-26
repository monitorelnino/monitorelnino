#!/usr/bin/env python3
"""coletar_orientacoes_oficiais.py — as páginas oficiais que sustentam o guia do Proteja-se, preservadas por hash.

HANDOVER_PROTEJA_SE §7.1–7.2 (19/10/2026). Duas coisas, uma rodada:
  1. cada página oficial de orientação (Defesa Civil nacional/MIDR, Ministério da Saúde) é buscada,
     preservada por hash em `evidencias/` e registrada em `data/orientacoes_oficiais.json` com URL, data
     da consulta e hash; cada item do guia (`conteudo/proteja-se.json`, chaves `guia-*.item*`) recebe o
     TRECHO da página que o sustenta. Item sem trecho em página nenhuma fica em `itens_sem_fonte`:
     lacuna declarada, e a página não o publica sem fonte;
  2. o diretório das Defesas Civis estaduais (MIDR) é buscado e preservado, e cada telefone e e-mail
     de `data/contatos_uf.json` é conferido contra o texto dele. A data da consulta e o resultado por
     UF entram em `fonte`/`conferencia`; valor divergente é registrado, nunca reescrito em silêncio.

Falha de rede ou recusa (401, 403, 429, 451, muro de robô) mantém o registro anterior daquela fonte,
com o motivo: ausência é lacuna, não zero. Cliente identificado, ritmo e `robots.txt` pelos
`coletores_base`. Três travas: não escreve em arquivo do índice; nada é promovido; a saída é só
`data/orientacoes_oficiais.json` e a conferência em `data/contatos_uf.json`.

Uso:  python3 coletar_orientacoes_oficiais.py              # rede (runner)
      python3 coletar_orientacoes_oficiais.py --autoteste  # sem rede e sem escrever em data/
"""
import io
import itertools
import json
import re
import sys
import unicodedata

import coletores_base as cb

SAIDA = "orientacoes_oficiais.json"
CONTATOS = "contatos_uf.json"
DIRETORIO = ("https://www.gov.br/mdr/pt-br/assuntos/protecao-e-defesa-civil/"
             "defesa-civil-no-brasil-e-no-mundo-1/defesa-civil-no-brasil")
MIDR, MS = "Defesa Civil nacional (MIDR)", "Ministério da Saúde"
G = "https://www.gov.br/"
FONTES = [  # (família, órgão, URL)
    ("chuvas", MIDR, G + "mdr/pt-br/ultimas-noticias/conheca-medidas-de-autoprotecao-que-a-populacao-deve-tomar-em-casos-de-inundacoes"),
    ("chuvas", MIDR, G + "mdr/pt-br/noticias/confira-dicas-da-defesa-civil-nacional-a-chegada-do-periodo-chuvoso"),
    ("chuvas", MIDR, G + "mdr/pt-br/assuntos/protecao-e-defesa-civil/informacoes-uteis/centro-nacional-de-gerenciamento-de-riscos-e-desastres-cenad/chuvasintensas.pdf"),
    ("fogo", MIDR, G + "mdr/pt-br/noticias/conheca-as-medidas-de-autoprotecao-que-a-populacao-deve-tomar-em-casos-de-incendios-florestais"),
    ("fogo", MIDR, G + "mdr/pt-br/assuntos/protecao-e-defesa-civil/IncndiosFlorestais.pdf"),
    ("fogo", MS, G + "saude/pt-br/assuntos/noticias-ms/2026/julho/ministerio-da-saude-monitora-impactos-dos-incendios-florestais-na-saude-e-orienta-populacao-sobre-exposicao-a-fumaca"),
    ("fogo", MS, G + "saude/pt-br/canais-de-atendimento/sala-de-imprensa/notas-a-imprensa/2024/orientacoes-para-evitar-a-exposicao-a-fumaca-intensa-causada-por-queimadas"),
    ("seca", MS, G + "saude/pt-br/centrais-de-conteudo/publicacoes/svsa/vigilancia-ambiental/plano-de-contingencia-seca-e-estiagem.pdf"),
    ("calor", MS, G + "saude/pt-br/assuntos/saude-de-a-a-z/o/ondas-de-calor"),
    ("calor", MS, G + "saude/pt-br/assuntos/noticias/2023/setembro/confira-cuidados-com-a-saude-para-se-proteger-das-altas-temperaturas"),
    ("dengue", MS, G + "saude/pt-br/assuntos/saude-de-a-a-z/d/dengue"),
    ("dengue", MS, G + "saude/pt-br/assuntos/noticias/2024/dezembro/dengue-conheca-os-sintomas-da-doenca-e-saiba-como-prevenir"),
    ("dengue", MS, G + "saude/pt-br/assuntos/noticias/2025/novembro/dez-dicas-para-eliminar-focos-do-mosquito-da-dengue"),
    ("chikungunya", MS, G + "saude/pt-br/assuntos/saude-de-a-a-z/c/chikungunya"),
    # 26/10 (central, 08:00): páginas federais atuais localizadas pela busca; entram só com trecho provado.
    ("chuvas", MIDR, G + "mdr/pt-br/assuntos/protecao-e-defesa-civil/ComoagirInundaesMDR.pdf"),
    ("chuvas", MIDR, G + "mdr/pt-br/assuntos/protecao-e-defesa-civil/deslizamento.pdf"),
    ("fogo", MS, G + "saude/pt-br/assuntos/saude-de-a-a-z/q/queimadas"),
    ("dengue", MS, G + "saude/pt-br/assuntos/noticias/2025/janeiro/conheca-os-oito-principais-sintomas-da-dengue-e-os-criterios-para-alta-medica"),
    ("dengue", MS, G + "saude/pt-br/centrais-de-conteudo/publicacoes/svsa/dengue/dengue-diagnostico-e-manejo-clinico-adulto-e-crianca"),
]
# A aba de dengue ainda não tem item no catálogo: a página oficial entra com as frases que tratam do que o
# guia vai orientar (água parada, recipientes, lixo, sintomas, quando procurar atendimento).
CHAVES_DENGUE = ("agua parada", "agua acumulada", "recipiente", "tamp", "lixo", "sintoma", "procur", "pneu", "caixa", "calha", "repelente")
MINIMO_DE_COBERTURA = 0.7   # fração das palavras do item que a frase da fonte precisa ter


def sem_acento(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", str(t).lower()) if unicodedata.category(c) != "Mn")


def palavras(t: str) -> set:
    return {p for p in re.findall(r"[a-z0-9]+", sem_acento(t)) if len(p) >= 4}


def texto_do_html(corpo: bytes) -> str:
    """Texto visível de uma página HTML, uma frase por linha. Função pura."""
    t = corpo.decode("utf-8", "replace")
    t = re.sub(r"(?is)<(script|style|noscript|nav|header|footer)\b.*?</\1>", " ", t)
    t = re.sub(r"(?i)</?(li|p|div|br|tr|h[1-6]|ul|ol|section|article)\b[^>]*>", "\n", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    import html
    t = html.unescape(t)
    return "\n".join(re.sub(r"\s+", " ", l).strip() for l in t.split("\n") if l.strip())


def texto_do_pdf(corpo: bytes) -> str:
    import pypdf
    leitor = pypdf.PdfReader(io.BytesIO(corpo))
    return "\n".join((p.extract_text() or "") for p in leitor.pages)


def frases(texto: str) -> list:
    return [f.strip() for l in texto.split("\n") for f in re.split(r"(?<=[.!?])\s+", l) if len(f.strip()) >= 25]


def trecho_que_sustenta(item: str, texto: str):
    """A frase da fonte que cobre ao menos 70% das palavras do item, ou None. Função pura.

    Cobertura de palavras, não de significado: o trecho é o que a fonte DIZ, e quem lê o guia vê os
    dois lado a lado. Item sem frase que o cubra não ganha fonte."""
    alvo = palavras(item)
    if len(alvo) < 3:
        return None
    melhor, cobertura = None, 0.0
    for f in frases(texto):
        c = len(alvo & palavras(f)) / len(alvo)
        if c > cobertura:
            melhor, cobertura = f, c
    return melhor[:400] if melhor and cobertura >= MINIMO_DE_COBERTURA else None


def trechos_de_dengue(texto: str) -> list:
    """Frases de orientação da página de dengue e, sob cada cabeçalho com dois-pontos que as palavras-chave
    pegam ("Sinais e sintomas de alerta:"), os itens da lista que o segue, que são curtos demais para `frases`.
    A lista acaba no primeiro parágrafo longo ou no cabeçalho seguinte. Função pura."""
    linhas = texto.split("\n")
    vistos, saida = set(), []

    def anota(f):
        if f not in vistos and len(f) <= 400:
            vistos.add(f)
            saida.append(f)

    for i, l in enumerate(linhas):
        for f in frases(l):
            if any(k in sem_acento(f) for k in CHAVES_DENGUE):
                anota(f)
        if l.endswith(":") and len(l) <= 80 and any(k in sem_acento(l) for k in CHAVES_DENGUE):
            for item in itertools.takewhile(lambda x: len(x) <= 120 and not x.endswith(":"), linhas[i + 1:]):
                anota(item)
    return saida[:30]


VERBOS_DE_ORIENTACAO = ("evit", "nao ", "nunca", "mantenh", "desligu", "coloqu", "fech", "procur", "siga", "acompanh",
                        "aument", "tenh", "mont", "auxili", "garant", "lav", "volt", "beb", "use ", "utiliz", "verifi",
                        "busc", "descart", "desinfet", "se houver", "se a ", "se o ", "se for", "sempre", "analis")


def trechos_de_orientacao(texto: str) -> list:
    """Passos que a página oficial dá ao leitor: item de lista (hífen, bolinha) ou frase que abre com verbo de
    orientação. Só para página escrita ao cidadão (chuvas, fogo); protocolo técnico (seca) e página sem passos
    ficam sem trechos, lacuna declarada. Linha de PDF quebrada em minúscula é emendada. Função pura."""
    linhas = []
    for l in (x.strip() for x in texto.split("\n") if x.strip()):
        if linhas and l[0].islower() and not re.search(r"[.;:!?]$", linhas[-1]):
            linhas[-1] += " " + l
        else:
            linhas.append(l)
    saida = []
    for l in linhas:
        lista = bool(re.match(r"[-•·]\s*", l))
        for f in re.split(r"(?<=[.!?;])\s+", re.sub(r"^[-•·]\s*", "", l)):
            f = f.strip().rstrip(";")
            if 20 <= len(f) <= 300 and (lista or sem_acento(f).startswith(VERBOS_DE_ORIENTACAO)) and f not in saida:
                saida.append(f)
    return saida[:40]


def itens_do_guia(catalogo: dict) -> dict:
    """{id: texto} dos itens `guia-<família>.item*` do catálogo. Função pura."""
    return {k: v for k, v in (catalogo.get("textos") or {}).items()
            if re.match(r"proteja-se\.guia-[a-z]+\.item(_\d+)?$", k)}


def conferir_contatos(contatos: dict, texto: str) -> dict:
    """Por UF: telefone e e-mail de `contatos_uf.json` estão no texto do diretório? Função pura."""
    so_digitos = re.sub(r"\D", "", texto)
    baixo = texto.lower()
    saida = {}
    for uf, c in (contatos.get("uf") or {}).items():
        tels = [t for t in (c.get("telefones") or []) + (c.get("plantao_24h") or []) if t]
        fora = [t for t in tels if re.sub(r"\D", "", t) not in so_digitos]
        mail = (c.get("email") or "").lower()
        saida[uf] = {"telefones_fora_do_diretorio": fora,
                     "email_fora_do_diretorio": bool(mail) and mail not in baixo}
    return saida


def devolveu_outra_pagina(corpo: bytes, url: str):
    """O canônico que a própria página declara, se não for o endereço pedido (o gov.br serve a
    inicial no lugar de notícia removida, com 200). Sem canônico: None. Função pura."""
    m = re.search(rb'<link rel="canonical" href="([^"]+)"', corpo[:200000])
    norm = lambda u: u.strip().lower().split("?")[0].rstrip("/")
    return m.group(1).decode("utf-8", "replace") if m and norm(m.group(1).decode("utf-8", "replace")) != norm(url) else None


def buscar_pagina(url: str, buscar=cb.buscar):
    """(corpo, None) ou (None, motivo). Recusa e falha viram motivo, nunca exceção."""
    try:
        corpo = buscar(url)
        aviso = cb.detectar_muro_de_robo(corpo) if not url.endswith(".pdf") else None
        outra = None if url.endswith(".pdf") else devolveu_outra_pagina(corpo, url)
        return (None, f"muro de robô: {aviso}") if aviso else (None, f"a URL devolve outra página ({outra})") if outra else (corpo, None)
    except Exception as e:  # noqa: BLE001 — qualquer falha é resultado a registrar
        return None, f"{type(e).__name__}: {e}"[:200]


def coletar(buscar=cb.buscar, preservar=cb.preservar_evidencia, ler=cb.ler, gravar=cb.gravar) -> int:
    hoje = cb.hoje_editorial().strftime("%d/%m/%Y")
    anterior = ler(SAIDA, {}) or {}
    antes = {f["url"]: f for f in anterior.get("fontes") or []}
    catalogo = json.loads((cb.RAIZ / "conteudo" / "proteja-se.json").read_text(encoding="utf-8"))
    itens = itens_do_guia(catalogo)
    fontes, textos = [], {}
    for familia, orgao, url in FONTES:
        corpo, motivo = buscar_pagina(url, buscar)
        if corpo is None:
            base = {"familia": familia, "orgao": orgao, "url": url}
            reg = base if motivo.startswith("a URL devolve") else dict(antes.get(url) or base)
            reg.update(tentativa_em=hoje, motivo_da_falha=motivo)
            fontes.append(reg)
            print(f"  ✗ {url[:90]}: {motivo}")
            continue
        pdf = url.endswith(".pdf")
        h = preservar(corpo, url, ".pdf" if pdf else ".html", "orientacoes_oficiais")
        texto = texto_do_pdf(corpo) if pdf else texto_do_html(corpo)
        reg = {"familia": familia, "orgao": orgao, "url": url, "consultado_em": hoje, "hash": h}
        if familia in ("dengue", "chikungunya"):
            reg["trechos"] = trechos_de_dengue(texto)
        elif familia in ("chuvas", "fogo"):
            reg["trechos"] = trechos_de_orientacao(texto)
        # o item é conferido também contra os passos já extraídos (item de lista, quebra em `;`), que `frases` não separa
        textos[url] = (familia, "\n".join([texto, *reg.get("trechos", [])]))
        fontes.append(reg)
        print(f"  ✓ {url[:90]} · {len(texto)} caracteres")
    achados, sem_fonte = {}, []
    for ident, item in sorted(itens.items()):
        familia = ident.split(".")[1].removeprefix("guia-")
        for url, (fam, texto) in textos.items():
            tr = trecho_que_sustenta(item, texto) if fam == familia else None
            if tr:
                achados[ident] = {"texto_do_guia": item, "url": url, "trecho": tr,
                                  "hash": next(f["hash"] for f in fontes if f["url"] == url),
                                  "consultado_em": hoje}
                break
        else:
            anterior_item = (anterior.get("itens") or {}).get(ident)
            if anterior_item and anterior_item.get("texto_do_guia") == item and not textos:
                achados[ident] = anterior_item
            else:
                sem_fonte.append(ident)
    gravar(SAIDA, {
        "_governanca": ("Páginas oficiais de orientação preservadas por hash e o trecho que sustenta cada "
                        "item do guia do Proteja-se (HANDOVER_PROTEJA_SE §7.1). Peso zero; nunca lido "
                        "pelo cálculo do índice. `itens_sem_fonte`: item do guia sem frase de fonte "
                        "oficial que o cubra até a consulta, lacuna declarada; a página não o publica "
                        "sem fonte. `motivo_da_falha`: a fonte recusou ou não respondeu; o registro "
                        "anterior daquela fonte é mantido."),
        "gerado_em": hoje, "fontes": fontes, "itens": achados, "itens_sem_fonte": sem_fonte})
    # 2 · o diretório das defesas civis estaduais
    corpo, motivo = buscar_pagina(DIRETORIO, buscar)
    contatos = ler(CONTATOS, {}) or {}
    if corpo is None:
        print(f"  ✗ diretório MIDR: {motivo}")
        contatos.setdefault("fonte", {})["ultima_falha"] = {"em": hoje, "motivo": motivo}
    else:
        h = preservar(corpo, DIRETORIO, ".html", "orientacoes_oficiais")
        conf = conferir_contatos(contatos, texto_do_html(corpo))
        contatos["fonte"].update(consultado_em=hoje, hash_da_consulta=h)
        contatos["fonte"].pop("ultima_falha", None)
        contatos["conferencia"] = {"em": hoje, "uf_com_divergencia": sorted(
            uf for uf, c in conf.items() if c["telefones_fora_do_diretorio"] or c["email_fora_do_diretorio"]),
            "por_uf": {uf: c for uf, c in conf.items()
                       if c["telefones_fora_do_diretorio"] or c["email_fora_do_diretorio"]}}
        print(f"  ✓ diretório MIDR · divergências: {contatos['conferencia']['uf_com_divergencia'] or 'nenhuma'}")
    gravar(CONTATOS, contatos)
    print(f"→ {len(achados)} item(ns) com fonte · {len(sem_fonte)} sem fonte")
    return 0


def autoteste() -> int:
    FONTE_SEM_TESTE = open(__file__, encoding="utf-8").read().split("def autoteste")[0]
    html = ("<html><nav>menu</nav><p>Não atravesse áreas alagadas: 15 cm de água em movimento podem "
            "derrubar um adulto.</p><ul><li>Evite deixar água parada em pneus e vasos.</li></ul>"
            "<script>x=1</script></html>").encode()
    t = texto_do_html(html)
    item_quebrado = "Aumente ingestão de água, líquidos e membranas respiratórias úmidas"
    contatos = {"uf": {"AC": {"telefones": ["(68) 3215-4736"], "email": "a@ac.gov.br"},
                       "AL": {"telefones": ["(82) 9999-0000"], "email": "b@al.gov.br"}}}
    conf = conferir_contatos(contatos, "AC (68) 3215-4736 a@ac.gov.br · AL (82) 3315-2843 b@al.gov.br")
    cat = {"textos": {"proteja-se.guia-chuvas.item": "x", "proteja-se.guia-chuvas.item_12": "y",
                      "proteja-se.guia-chuvas.texto": "https://x", "proteja-se.guia-seca.titulo": "z"}}
    return cb.rodar_autoteste({
        "o texto sai sem menu nem script": lambda: "menu" not in t and "x=1" not in t and "adulto" in t,
        "o trecho que cobre o item é achado": lambda: (trecho_que_sustenta(
            "Não atravesse áreas alagadas: água em movimento derruba um adulto", t) or "").startswith("Não atravesse"),
        "item que a fonte não diz fica sem trecho": lambda: trecho_que_sustenta(
            "Desligue a energia elétrica e feche o registro do gás", t) is None,
        "linha de PDF quebrada: o passo emendado em `trechos` cobre o item": lambda: (
            lambda pdf: trecho_que_sustenta(item_quebrado, pdf) is None
            and trecho_que_sustenta(item_quebrado, "\n".join([pdf, *trechos_de_orientacao(pdf)])) is not None)(
            "Aumente a ingestão de água e líquidos para manter as\nmembranas respiratórias úmidas e hidratadas."),
        "item curto demais não ganha fonte": lambda: trecho_que_sustenta("Beba água", t) is None,
        "só os itens do guia entram": lambda: sorted(itens_do_guia(cat)) == [
            "proteja-se.guia-chuvas.item", "proteja-se.guia-chuvas.item_12"],
        "dengue: frases de água parada": lambda: trechos_de_dengue(t) == [
            "Evite deixar água parada em pneus e vasos."],
        "telefone diferente do diretório é divergência": lambda: conf["AL"]["telefones_fora_do_diretorio"]
        == ["(82) 9999-0000"] and not conf["AC"]["telefones_fora_do_diretorio"]
        and not conf["AC"]["email_fora_do_diretorio"],
        "página que devolve a inicial não é a pedida": lambda: devolveu_outra_pagina(
            b'<link rel="canonical" href="https://www.gov.br/saude" />', "https://www.gov.br/saude/pt-br/x")
        and not devolveu_outra_pagina(b'<link rel="canonical" href="https://www.gov.br/saude/pt-br/x/" />',
                                      "https://www.gov.br/saude/pt-br/x") and not devolveu_outra_pagina(b"<p>sem canonico</p>", "u"),
        "dengue: lista de passos entra, telefone não": lambda: trechos_de_dengue(
            "Tampe caixas d’água, ralos e pias;\nTeleatendimento: de segunda a sexta, das 8h às 20h.\nColoque areia nos vasos de plantas;") == ["Tampe caixas d’água, ralos e pias;"],
        "dengue: a lista sob o cabeçalho entra inteira e para no parágrafo": lambda: trechos_de_dengue(
            "Sinais e sintomas de alerta:\nDor na barriga;\nVômitos frequentes;\nOutro cabeçalho de sintomas:\nFebre;\n"
            + "Texto corrido longo " * 8) == ["Sinais e sintomas de alerta:", "Dor na barriga;", "Vômitos frequentes;",
                                              "Outro cabeçalho de sintomas:", "Febre;"],
        "orientação: passo entra, definição e título não": lambda: trechos_de_orientacao(
            "Inundações\nSegundo a Cobrade, as inundações são a submersão de áreas.\n- Feche o registro de água\n"
            "Nunca atravesse ruas inundadas, mesmo de carro\nProcure um local alto e espere o nível\nda água baixar.")
        == ["Feche o registro de água", "Nunca atravesse ruas inundadas, mesmo de carro",
            "Procure um local alto e espere o nível da água baixar."],
        "recusa vira motivo, não exceção": lambda: buscar_pagina(
            "x", lambda u: (_ for _ in ()).throw(OSError("recusado")))[1].startswith("OSError"),
        "trava estrutural: não escreve no índice": lambda: not any(
            f'"{n}.json"' in FONTE_SEM_TESTE for n in ("estados", "saude_uf", "municipios", "indice", "monitor_saude")),
    })


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else coletar())
