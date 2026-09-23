#!/usr/bin/env python3
"""
verificar_evidencias.py — portão 6 (v2.2.4, §3.8 / §6)
======================================================
Todo registro PONTUÁVEL com URL precisa de evidência preservada
(`hash_evidencia` presente em `data/evidencias.json`, com cópia binária em
`evidencias/`, texto extraído do PDF, ou snapshot real no Wayback — ver
`prova_preservada()`, §174: a anotação de que a tentativa de snapshot falhou
NÃO é prova, embora tenha contado como se fosse até 22/09/2026). Regime declarado:
  - até 14/09/2026: AVISO — lista o que falta, sai 0 (prazo original 09/09, adiado em 08/09/2026 com errata:
    69 registros do ES não tinham cópia por falha do nosso próprio cliente HTTP — IRI com "ê" cru no caminho,
    corrigida em coletores_base.url_ascii; a primeira rodada do robô com a correção é segunda 14/09);
  - a partir de 15/09/2026: BLOQUEANTE — sai 1 se faltar.
Também confere a integridade dos arquivos preservados: sha256 do binário = chave, e
sha256 do texto extraído = `texto_hash` (§175 — o do texto não era conferido).
"""
import hashlib, json, pathlib, sys
from datetime import date

RAIZ = pathlib.Path(__file__).parent
PONT = {"plano", "plano_antigo", "plano_elaboracao", "coberto_estadual"}
BLOQUEIA_A_PARTIR = date(2026, 9, 15)


def checar_cliente_http() -> list:
    """Teste negativo permanente (08/09/2026): toda URL pontuável tem de sair de coletores_base.url_ascii em ASCII puro,
    idêntica quando já estava codificada. Foi um "ê" cru em 69 URLs do ES que deixou 69 registros sem evidência."""
    sys.path.insert(0, str(RAIZ))
    from coletores_base import url_ascii
    erros = []
    exemplo = "https://defesacivil.es.gov.br/Media/DefesaCivil/Plano%20de%20Contingência%20atualizado/2026/%C3%81GUA.pdf"
    if url_ascii(exemplo) != "https://defesacivil.es.gov.br/Media/DefesaCivil/Plano%20de%20Conting%C3%AAncia%20atualizado/2026/%C3%81GUA.pdf":
        erros.append("url_ascii não codifica caractere cru no caminho")
    ja = "https://x.org/a%20b?c=1&d=%C3%81#f"
    if url_ascii(ja) != ja: erros.append("url_ascii altera URL já codificada")
    mun = json.load(open(RAIZ / "data" / "municipios.json", encoding="utf-8"))
    for m in mun:
        u = str(m.get("url", ""))
        if u.startswith("http") and not url_ascii(u).isascii(): erros.append(f"URL não ASCII após url_ascii: {u[:70]}")
    return erros


def checar_preservacao_na_cadencia() -> list:
    """Teste negativo permanente (22/09/2026, §164): a cadência TEM de chamar preservar_evidencias.py.

    Este portão é bloqueante desde 15/09, mas o script que o mantém verde não era chamado por
    workflow nenhum — dependia de alguém rodar à mão. Quando o juiz passou a aplicar municípios
    sozinho (§158), Feira de Santana/BA entrou no banco sem hash_evidencia e a main ficou vermelha
    até uma sessão humana notar (§162). Sem esta trava, tirar o passo do workflow volta a ser
    silencioso: o portão só acusaria na próxima aplicação automática."""
    wf = RAIZ / ".github" / "workflows" / "atualizar.yml"
    if not wf.exists():
        return []   # fora do repositório completo (cópia parcial), não é falha do dado
    texto = wf.read_text(encoding="utf-8")
    # A chamada pode estar num `run:` de uma linha só ou num bloco `run: |`; o que importa é
    # existir uma linha que execute o script e não esteja comentada.
    def executa(linha: str) -> bool:
        corpo = linha.strip()
        for prefixo in ("- run:", "run:"):
            if corpo.startswith(prefixo):
                corpo = corpo[len(prefixo):].strip()
                break
        return (corpo.startswith("python3 ") and "preservar_evidencias.py" in corpo
                and not corpo.startswith("#"))

    linhas = [l for l in texto.splitlines() if executa(l)]
    if not linhas:
        return ["a cadência (.github/workflows/atualizar.yml) não chama preservar_evidencias.py — "
                "registro aplicado pelo juiz ficaria sem cópia do documento e este portão fecharia "
                "vermelho na main até alguém rodar à mão (ver §164)"]
    if not any("--ler" in l for l in linhas):
        return ["a cadência chama preservar_evidencias.py mas não no modo --ler — sem a leitura, o "
                "documento acima de 5 MB fica sem nenhuma cópia preservada, só com a tentativa de "
                "Wayback registrada (ver §174)"]
    if not any("--ocr" in l for l in linhas):
        return ["a cadência chama preservar_evidencias.py mas não no modo --ocr — o PDF escaneado "
                "acima de 5 MB continua sem prova de espécie alguma, que é a lacuna declarada do "
                "§174 e o que o §177 fecha"]
    if not any("tesseract-ocr-por" in l for l in texto.splitlines()):
        return ["a cadência roda --ocr mas não instala tesseract-ocr-por — com o modelo em inglês o "
                "OCR troca acento no português e a cópia legível sai pior do que precisa (§177)"]
    return []


MIN_CARACTERES_TEXTO = 200   # mesmo piso que ler_pdfs() usa para decidir se a extração serviu

# §174 (22/09/2026): lacuna DECLARADA e DATADA — mecanismo, hoje sem nenhuma lacuna em uso.
# Quatro registros pontuáveis do ES não tinham prova preservada de espécie alguma: PDF acima do
# teto de cópia (5 MB), Wayback sem snapshot (consultado, não só tentado) e PDF escaneado, sem
# camada de texto — a leitura do §10.1 devolvia zero caractere. Até 22/09/2026 passavam no portão
# porque a STRING "tentativa falhou (...)" contava como prova. Decisão da editoria: declarar em vez
# de esconder, com aviso a cada execução e bloqueio a partir da data abaixo.
# §177 (23/09/2026): os quatro ganharam cópia legível por OCR (modelo português) e SAÍRAM daqui —
# a lista fica vazia de propósito, e o mecanismo continua de pé para a próxima lacuna que precise
# ser declarada. A chave é o hash do documento: represervado, o hash muda e a exceção cai sozinha.
# O portão também avisa quando uma lacuna declarada já foi resolvida, para a lista não apodrecer.
LACUNA_BLOQUEIA_A_PARTIR = date(2026, 10, 31)
LACUNA_DECLARADA = {}


def prova_preservada(item: dict) -> bool:
    """Há prova mesmo, e não só a anotação de que a tentativa falhou? (§174, 22/09/2026)

    Achado real: a condição anterior era `item["arquivo"] or item["wayback"]`, e
    `preservar_evidencia()` grava em `wayback` a STRING "tentativa falhou (HTTPError)" quando o
    pedido de snapshot não vai — string não vazia, portanto verdadeira. O portão dava por provados
    34 dos 92 registros pontuáveis que não tinham cópia nenhuma: são os documentos acima do limite
    de 5 MB (mediana de 13 MB, um de 70 MB), em que a cópia binária é pulada por desenho e o
    Wayback era a única rede de segurança. Agora só conta prova de verdade: a cópia binária, o
    TEXTO extraído (`texto_arquivo`, §10.1 — é cópia preservada, legível e com hash próprio) ou um
    endereço de snapshot que comece com http."""
    if item.get("arquivo"):
        return True
    # O texto só é prova se houver texto: quatro PDFs escaneados do ES produziam um .txt com os
    # marcadores de página e zero caractere de conteúdo, que contaria como cópia preservada.
    if item.get("texto_arquivo") and (item.get("caracteres") or 0) >= MIN_CARACTERES_TEXTO:
        return True
    # §177 (23/09/2026): o texto de OCR é cópia preservada e LEGÍVEL de PDF escaneado — é prova,
    # com o mesmo piso de caracteres. Guardado em campo próprio (`ocr_*`) exatamente para não virar
    # insumo de classificação: o ato que pontua tem de ser lido no documento (§156).
    if item.get("ocr_arquivo") and (item.get("ocr_caracteres") or 0) >= MIN_CARACTERES_TEXTO:
        return True
    wb = item.get("wayback")
    return isinstance(wb, str) and wb.startswith("http")


def autoteste_prova() -> list:
    """Teste negativo permanente da regra acima — a falha registrada NUNCA pode contar como prova."""
    casos = [
        ({"arquivo": None, "wayback": "tentativa falhou (HTTPError)"}, False),
        ({"arquivo": None, "wayback": "tentativa falhou (URLError)"}, False),
        ({"arquivo": None, "wayback": "tentativa falhou (TimeoutError)"}, False),
        ({"arquivo": None, "wayback": None}, False),
        ({"arquivo": "evidencias/x.pdf", "wayback": None}, True),
        ({"arquivo": None, "texto_arquivo": "evidencias/x.txt", "caracteres": 9407,
          "wayback": "tentativa falhou (X)"}, True),
        ({"arquivo": None, "wayback": "https://web.archive.org/web/*/http://x"}, True),
        # PDF escaneado: o .txt existe, com marcadores de página e nada dentro — não é prova.
        ({"arquivo": None, "texto_arquivo": "evidencias/x.txt", "caracteres": 0}, False),
        ({"arquivo": None, "texto_arquivo": "evidencias/x.txt"}, False),
        ({"arquivo": None, "texto_arquivo": "evidencias/x.txt", "caracteres": 199}, False),
        # §177: a cópia legível por OCR é prova, com o mesmo piso — vazia, não é
        ({"arquivo": None, "wayback": "tentativa falhou (X)", "ocr_arquivo": "evidencias/x.ocr.txt",
          "ocr_caracteres": 12345}, True),
        ({"arquivo": None, "ocr_arquivo": "evidencias/x.ocr.txt", "ocr_caracteres": 199}, False),
        ({"arquivo": None, "ocr_arquivo": "evidencias/x.ocr.txt"}, False),
    ]
    return [f"prova_preservada({c}) deveria ser {esperado}"
            for c, esperado in casos if prova_preservada(c) is not esperado]


def integridade_texto(itens: dict, raiz: pathlib.Path = RAIZ) -> list:
    """sha256(texto_arquivo) == texto_hash, para todo item que registra os dois (§175, 23/09/2026).

    Achado real: o portão conferia a integridade da cópia BINÁRIA (sha256 do arquivo = chave) e
    nunca a do TEXTO — que desde o §174 também conta como prova preservada. A rotina de redação de
    CPF de 12/09/2026 (`scripts/remediar_cpf_evidencias.py`) regravava o `.txt` e não recalculava
    `texto_hash`: Maricá/RJ ficou com o hash de antes da redação, e nada acusava. Um texto cujo hash
    registrado não bate com o arquivo em disco não é prova verificável — é um arquivo qualquer.
    §176: vale também para o texto integral do diário (`texto_integral`/`texto_integral_hash`), e
    arquivo prometido pelo índice e ausente do disco reprova mesmo sem hash registrado."""
    erros = []
    # §176 (23/09/2026): o texto INTEGRAL do diário oficial entra na mesma regra. Eram 148 itens sem
    # hash nenhum do texto, e quatro apontavam para um arquivo que não estava em disco — o campo foi
    # gravado em 12/09 e o `.txt` nunca entrou no commit da rodada. Arquivo prometido e ausente é
    # falha de integridade, com ou sem hash registrado: o índice afirma preservar o que não existe.
    for campo, campo_hash in (("texto_arquivo", "texto_hash"), ("texto_integral", "texto_integral_hash"),
                              ("ocr_arquivo", "ocr_hash")):   # §177
        for h, it in itens.items():
            ta, th = it.get(campo), it.get(campo_hash)
            if not ta:
                continue
            pth = raiz / ta
            if not pth.exists():
                erros.append(f"{h[:12]}… {campo} ausente em disco ({ta})")
                continue
            bruto = pth.read_bytes()
            if th and hashlib.sha256(bruto).hexdigest() != th:
                erros.append(f"{h[:12]}… {campo} não bate com {campo_hash} ({ta}) — regravado sem recalcular o hash?")
            # §177 (23/09/2026, achado na primeira rodada real de OCR): cópia preservada em CRLF é
            # cópia que depende da máquina que a produziu. O Tesseract do Windows devolve CRLF no
            # stdout, e `newline` na gravação não alcança isso — traduz o que o Python escreve, não
            # o "\r" que já vem no texto. A prova tem de sair igual em qualquer máquina (série do §163).
            if b"\r\n" in bruto:
                erros.append(f"{h[:12]}… {campo} está em CRLF ({ta}) — a cópia preservada dependeria da máquina")
    # §177: o texto de OCR não pode ocupar o lugar da camada de texto do documento. Se `ocr_arquivo`
    # e `texto_arquivo` apontarem para o mesmo arquivo, a leitura de máquina (classificar_saude_no_plano)
    # passaria a ler OCR como se fosse o documento — e erro de caractere viraria classificação.
    for h, it in itens.items():
        if it.get("ocr_arquivo") and it.get("ocr_arquivo") == it.get("texto_arquivo"):
            erros.append(f"{h[:12]}… ocr_arquivo é o mesmo arquivo de texto_arquivo — OCR não substitui a camada de texto")
    return erros


def autoteste_integridade_texto() -> list:
    """Teste negativo permanente da regra acima: texto regravado sem recalcular o hash reprova."""
    import tempfile
    falhas = []
    with tempfile.TemporaryDirectory() as d:
        raiz = pathlib.Path(d); (raiz / "evidencias").mkdir()
        alvo = raiz / "evidencias" / "a.txt"
        alvo.write_text("\n=== página 1 ===\ntexto preservado\n",
                        encoding="utf-8", newline="\n")
        certo = hashlib.sha256(alvo.read_bytes()).hexdigest()
        # arquivo em CRLF, para o caso negativo da regra de portabilidade da cópia preservada
        (raiz / "evidencias" / "crlf.txt").write_bytes(b"=== pagina 1 ===\r\ntexto\r\n")
        casos = [
            ({"texto_arquivo": "evidencias/a.txt", "texto_hash": certo}, 0),
            ({"texto_arquivo": "evidencias/a.txt", "texto_hash": "0" * 64}, 1),      # regravado sem recalcular
            ({"texto_arquivo": "evidencias/ausente.txt", "texto_hash": certo}, 1),   # texto perdido
            ({"texto_arquivo": None, "texto_hash": None}, 0),
            ({"arquivo": "evidencias/a.pdf"}, 0),                                    # só cópia binária: fora desta regra
            # §176: texto integral do diário — mesma régua, e o arquivo prometido tem de existir
            ({"texto_integral": "evidencias/a.txt", "texto_integral_hash": certo}, 0),
            ({"texto_integral": "evidencias/a.txt", "texto_integral_hash": "0" * 64}, 1),
            ({"texto_integral": "evidencias/ausente.txt"}, 1),                        # prometido e ausente
            ({"texto_integral": "evidencias/a.txt"}, 0),                             # ainda sem hash: selagem pendente
            # §177: cópia legível por OCR — mesma régua de integridade, e arquivo próprio
            ({"ocr_arquivo": "evidencias/a.txt", "ocr_hash": certo}, 0),
            ({"ocr_arquivo": "evidencias/a.txt", "ocr_hash": "0" * 64}, 1),
            ({"ocr_arquivo": "evidencias/a.txt", "ocr_hash": certo,
              "texto_arquivo": "evidencias/a.txt", "texto_hash": certo}, 1),           # OCR no lugar da camada de texto
            # §177: cópia preservada em CRLF reprova, com ou sem hash registrado
            ({"texto_arquivo": "evidencias/crlf.txt"}, 1),
            ({"ocr_arquivo": "evidencias/crlf.txt"}, 1),
        ]
        for i, (item, esperado) in enumerate(casos):
            n = len(integridade_texto({f"{i:064d}": item}, raiz))
            if n != esperado:
                falhas.append(f"integridade_texto({item}) devolveu {n} problema(s); esperado {esperado}")
    return falhas


def main() -> int:
    e = (checar_cliente_http() + checar_preservacao_na_cadencia() + autoteste_prova()
         + autoteste_integridade_texto())
    if e:
        print("✗ EVIDÊNCIAS: pré-condições do portão:"); [print("   ", x) for x in e]; return 1
    mun = json.load(open(RAIZ / "data" / "municipios.json", encoding="utf-8"))
    p_idx = RAIZ / "data" / "evidencias.json"
    idx = json.load(open(p_idx, encoding="utf-8")) if p_idx.exists() else {"itens": {}}
    itens = idx.get("itens", {})
    faltam, corrompidos = [], []
    declarados, resolvidos = [], []
    for m in mun:
        if m.get("categoria") in PONT and str(m.get("url", "")).startswith("http"):
            h = m.get("hash_evidencia")
            if not h or h not in itens or not prova_preservada(itens[h]):
                if h in LACUNA_DECLARADA and date.today() < LACUNA_BLOQUEIA_A_PARTIR:
                    declarados.append(LACUNA_DECLARADA[h])
                else:
                    faltam.append(f"{m['nome']}/{m['uf']}")
            elif h in LACUNA_DECLARADA:
                resolvidos.append(LACUNA_DECLARADA[h])
    for h, it in itens.items():
        arq = it.get("arquivo")
        if arq:
            p = RAIZ / arq
            if not p.exists():
                corrompidos.append(f"{h[:12]}… arquivo ausente ({arq})")
            elif hashlib.sha256(p.read_bytes()).hexdigest() != h:
                corrompidos.append(f"{h[:12]}… conteúdo não bate com o hash ({arq})")
    # §175 (23/09/2026): o texto extraído é prova desde o §174 — e o hash dele nunca era conferido.
    corrompidos += integridade_texto(itens)
    # 11/09/2026 (achado do ensaio): teste negativo permanente. Um item cuja `arquivo` é um .txt e cuja URL de origem
    # é um .pdf tem a chave = sha256 do TEXTO, não do binário. Sem a marca `texto_manual`, `preservar_evidencias --ler`
    # o elege como alvo, reextrai o PDF e regrava evidencias/<h>.txt sob o mesmo nome — o conteúdo deixa de bater com a
    # chave e este portão fica vermelho na rodada (foi o que derrubou o job em 10/09 21h e o ensaio de 11/09).
    for h, it in itens.items():
        arq = str(it.get("arquivo") or "")
        if arq.endswith(".txt") and str(it.get("url", "")).lower().split("?")[0].endswith(".pdf") and not it.get("texto_manual"):
            corrompidos.append(f"{h[:12]}… evidência de texto com URL .pdf sem `texto_manual: true` — seria sobrescrita por preservar_evidencias --ler ({arq})")
    if corrompidos:
        print("✗ EVIDÊNCIAS: integridade violada:"); [print("   ", c) for c in corrompidos]; return 1
    total = sum(1 for m in mun if m.get("categoria") in PONT and str(m.get("url", "")).startswith("http"))
    if faltam:
        regime = "BLOQUEANTE" if date.today() >= BLOQUEIA_A_PARTIR else "aviso (bloqueante a partir de 15/09/2026)"
        print(f"{'✗' if regime == 'BLOQUEANTE' else '⚠'} EVIDÊNCIAS: {len(faltam)} de {total} registro(s) pontuável(is) com URL sem evidência preservada — {regime}")
        for f in faltam[:8]: print("   ", f)
        if len(faltam) > 8: print(f"    … e mais {len(faltam) - 8}")
        return 1 if regime == "BLOQUEANTE" else 0
    if resolvidos:
        print(f"⚠ EVIDÊNCIAS: {len(resolvidos)} lacuna(s) declarada(s) já resolvida(s) — tirar de "
              f"LACUNA_DECLARADA para a lista não apodrecer:")
        for r in resolvidos: print("   ", r)
    if declarados:
        print(f"⚠ EVIDÊNCIAS: {len(declarados)} de {total} registro(s) pontuável(is) sem prova preservada, "
              f"em LACUNA DECLARADA (§174) — bloqueante a partir de {LACUNA_BLOQUEIA_A_PARTIR.strftime('%d/%m/%Y')}:")
        for d in declarados: print("   ", d)
    print(f"✓ EVIDÊNCIAS OK — {total - len(declarados)} de {total} registro(s) pontuável(is) com URL com "
          f"evidência preservada; {len(declarados)} em lacuna declarada; {len(itens)} item(ns) íntegro(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
