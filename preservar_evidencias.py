#!/usr/bin/env python3
"""
preservar_evidencias.py (v2.2.4, §3.8)
======================================
Para cada registro PONTUÁVEL de data/municipios.json com URL e sem
`hash_evidencia`, baixa o documento, guarda em evidencias/<sha256>.<ext> (ou só
o hash + Wayback se > 5 MB), indexa em data/evidencias.json e grava o hash no
registro. Idempotente: quem já tem hash é pulado. Falha de rede = lacuna
declarada (o portão verificar_evidencias.py cobra depois). É a ÚNICA edição
programática permitida em municipios.json fora de aplicar_revisao.py, porque
não altera nenhum campo de julgamento — só acrescenta prova.
"""
import hashlib, io, mimetypes, re, sys, urllib.error
from pathlib import Path
from coletores_base import buscar, preservar_evidencia, ler, gravar, registrar_lacuna, log_busca, EVID, redigir_dados_pessoais

LIMITE_PDF_COPIA = 5 * 1024 * 1024   # cópia do binário só até 5 MB; o TEXTO extraído é guardado sempre


def extrair_texto_por_pagina(pdf_bytes: bytes) -> list:
    """Lista de textos, um por página (pypdf; pdfplumber como reserva na página vazia). Função pura."""
    paginas = []
    try:
        from pypdf import PdfReader
        rd = PdfReader(io.BytesIO(pdf_bytes))
        for pg in rd.pages:
            try: paginas.append((pg.extract_text() or "").strip())
            except Exception: paginas.append("")  # noqa: BLE001
    except Exception:  # noqa: BLE001
        return []
    if paginas and sum(len(t) for t in paginas) < 200:
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                paginas = [(pg.extract_text() or "").strip() for pg in pdf.pages]
        except Exception:  # noqa: BLE001
            pass
    return paginas


def gravar_texto(h: str, paginas: list) -> str:
    """evidencias/<sha256>.txt com marcador de página; devolve o hash do texto.
    12/09/2026 (achado de auditoria): redige CPF antes de gravar E antes de calcular o hash — o
    documento fonte pode trazer CPF de quem assina (prática comum em atos oficiais brasileiros), e
    o Monitor não precisa dessa informação para nada do que mede. Ver redigir_dados_pessoais() em
    coletores_base.py para a fundamentação (LGPD art. 6º, III)."""
    EVID.mkdir(exist_ok=True)
    txt = "".join(f"\n=== página {i+1} ===\n{t}\n" for i, t in enumerate(paginas))
    txt, n_cpfs = redigir_dados_pessoais(txt)
    if n_cpfs:
        print(f"  [redação] {n_cpfs} CPF(s) removido(s) do texto antes de preservar")
    # newline="\n" (§174): sem isso, no Windows o texto sai em CRLF enquanto o texto_hash abaixo é
    # calculado sobre a string em memória, com \n — o hash registrado deixaria de bater com o
    # arquivo em disco, e a cópia preservada divergiria da que o runner gera. Ver §163.
    (EVID / f"{h}.txt").write_text(txt, encoding="utf-8", newline="\n")
    return hashlib.sha256(txt.encode("utf-8")).hexdigest()


def filtrar_alvos(alvos: list, trecho: str | None) -> list:
    """Restringe a fila ao que casa com um trecho da URL (§187): a fila tem dezenas de alvos, e
    esperar a vez de um documento específico gasta rede em quem já foi lido. Sem trecho, devolve
    tudo — o comportamento da cadência não muda."""
    if not trecho:
        return alvos
    t = trecho.lower()
    return [(h, it) for h, it in alvos if t in str(it.get("url", "")).lower()]


def ler_pdfs(limite: int = 40, alvo: str | None = None) -> int:
    """§10.1 peça 1: para todo item do índice com URL de PDF sem texto (e para registros com URL de PDF ainda sem hash),
    baixa com o UA do Monitor, extrai o texto por página, grava evidencias/<sha>.txt e indexa (texto_arquivo, paginas, texto_hash).
    Sítio que recusa (401/403) → decisão 'acesso recusado' no log (candidato a pedido de LAI)."""
    idx = ler("evidencias.json", {"itens": {}}); itens = idx.setdefault("itens", {})
    # 11/09/2026: `not it.get("texto_arquivo")` já exclui itens de texto manual (texto_manual), que registram
    # texto_arquivo apontando para o próprio arquivo preservado — reextrair sobrescreveria evidencias/<h>.txt sob
    # o mesmo nome e violaria o portão de integridade (sha256(arquivo) == chave). Explicitado por segurança.
    alvos = [(h, it) for h, it in itens.items() if str(it.get("url", "")).lower().split("?")[0].endswith(".pdf") and not it.get("texto_arquivo") and not it.get("texto_manual")]
    # registros estaduais/municipais com URL .pdf ainda sem hash
    for reg, fonte in ((ler("estados.json", {}).get("ufs") or [], "estados"), (ler("municipios.json", []) or [], "municipios")):
        for r in reg:
            u = str(r.get("url") or ""); 
            if u.lower().split("?")[0].endswith(".pdf") and not r.get("hash_evidencia") and all(it.get("url") != u for it in itens.values()):
                alvos.append((None, {"url": u, "origem": f"ler_pdfs/{fonte}", "_reg": r}))
    lidos = recusados = falhas = 0
    alvos = filtrar_alvos(alvos, alvo)
    for h, it in alvos[:limite]:
        u = it["url"]
        try:
            bruto = buscar(u, timeout=90)
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                recusados += 1; log_busca("site_municipal", 2, [u], "acesso recusado", resultados=f"HTTP {e.code} ao ler PDF — candidato a pedido de LAI")
            else:
                falhas += 1; registrar_lacuna(f"leitura de PDF {u[:60]}", f"HTTP {e.code}", canal="DOM", camada=2, strings=[u])
            continue
        except Exception as e:  # noqa: BLE001
            falhas += 1; registrar_lacuna(f"leitura de PDF {u[:60]}", type(e).__name__, canal="DOM", camada=2, strings=[u]); continue
        if bruto[:4] != b"%PDF":
            falhas += 1; registrar_lacuna(f"leitura de PDF {u[:60]}", "resposta não é PDF", canal="DOM", camada=2, strings=[u]); continue
        h_novo = hashlib.sha256(bruto).hexdigest()
        if h is None:
            h = preservar_evidencia(bruto, u, "pdf", it["origem"]); it = itens.get(h, it)
            if it.get("_reg") is not None: it["_reg"]["hash_evidencia"] = h
        elif h_novo != h:
            registrar_lacuna(f"leitura de PDF {u[:60]}", f"documento mudou desde o hash registrado ({h[:12]}… → {h_novo[:12]}…)", canal="DOM", camada=2, strings=[u])
        paginas = extrair_texto_por_pagina(bruto)
        if not paginas:
            falhas += 1; registrar_lacuna(f"leitura de PDF {u[:60]}", "PDF sem texto extraível (imagem?)", canal="DOM", camada=2, strings=[u]); continue
        th = gravar_texto(h, paginas)
        item = itens.setdefault(h, {"url": u, "origem": it.get("origem"), "preservado_em": None, "tamanho": len(bruto), "arquivo": None, "wayback": None})
        item.update({"texto_arquivo": f"evidencias/{h}.txt", "paginas": len(paginas), "texto_hash": th, "lido_em": __import__("datetime").date.today().isoformat(), "caracteres": sum(len(t) for t in paginas)})
        if len(bruto) <= LIMITE_PDF_COPIA and not item.get("arquivo"):
            (EVID / f"{h}.pdf").write_bytes(bruto); item["arquivo"] = f"evidencias/{h}.pdf"
        lidos += 1
    for it in itens.values(): it.pop("_reg", None)
    gravar("evidencias.json", idx)
    print(f"leitura de PDFs: {lidos} lido(s) com texto, {recusados} acesso recusado (LAI), {falhas} falha(s); {len(alvos)} alvo(s) na fila")
    return 0


# ---------------------------------------------------------------------------------
# §177 (23/09/2026): OCR do PDF escaneado — cópia LEGÍVEL, nunca insumo de julgamento.
# Quatro PLANCON do ES (Anchieta, Itaguaçu, São José do Calçado e Venda Nova do Imigrante)
# entraram em LACUNA_DECLARADA no §174: PDF de 10 a 19 MB, acima do teto de cópia, escaneado
# (cada página é uma imagem), leitura devolve zero caractere e o Wayback não tem snapshot.
# Sem cópia, sem texto e sem snapshot, não há prova preservada de nenhuma espécie.
#
# REGRA QUE VEM COM O RECURSO: o texto de OCR é cópia preservada e LEGÍVEL, marcada como tal
# (campos `ocr_*`, arquivo `<hash>.ocr.txt`) — e NUNCA insumo do classificador nem do juiz. O
# ato que pontua no índice tem de ser lido no documento (§156); OCR erra caractere, e um erro
# de leitura não pode virar nota. Por isso o texto de OCR não entra em `texto_arquivo`, que é o
# campo que classificar_saude_no_plano.py lê.
OCR_DPI = 200
OCR_MIN_CARACTERES = 200          # o mesmo piso de ler_pdfs() e de prova_preservada()
OCR_TIMEOUT_PAGINA = 120          # segundos por página; fonte lenta não segura a rodada (§172)
OCR_EXECUTAVEIS_WINDOWS = (r"C:\Program Files\Tesseract-OCR\tesseract.exe",)


def tesseract_disponivel():
    """Caminho do executável do Tesseract, ou None. No runner vem do apt (`tesseract-ocr`);
    fora dele, do instalador padrão do Windows. Ausência é lacuna declarada, nunca erro fatal."""
    import shutil
    achado = shutil.which("tesseract")
    if achado:
        return achado
    return next((c for c in OCR_EXECUTAVEIS_WINDOWS if Path(c).exists()), None)


def motor_ocr(exe: str) -> tuple:
    """(versão, idioma) do Tesseract. `por` quando o modelo está instalado; senão `eng`, e o
    registro diz qual leu — modelo errado explica erro de leitura, e calar isso esconde a causa."""
    import subprocess
    versao = "desconhecida"
    try:
        saida = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=30).stdout
        versao = (saida.splitlines() or ["tesseract"])[0].replace("tesseract ", "").strip()
    except Exception:  # noqa: BLE001
        pass
    idioma = "eng"
    try:
        saida = subprocess.run([exe, "--list-langs"], capture_output=True, text=True, timeout=30).stdout
        if "por" in {l.strip() for l in saida.splitlines()[1:]}:
            idioma = "por"
    except Exception:  # noqa: BLE001
        pass
    return versao, idioma


def rasterizar(pdf_bytes: bytes, dpi: int = OCR_DPI, limite_paginas: int = 0) -> list:
    """Páginas do PDF como PNG, por pypdfium2 (já é dependência, via pdfplumber). Função pura."""
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(io.BytesIO(pdf_bytes))
    total = len(doc)
    quantas = min(total, limite_paginas) if limite_paginas else total
    paginas = []
    for i in range(quantas):
        bitmap = doc[i].render(scale=dpi / 72)
        buf = io.BytesIO()
        bitmap.to_pil().save(buf, format="PNG")
        paginas.append(buf.getvalue())
    return paginas


def ocr_pagina(png: bytes, exe: str, idioma: str, dpi: int = OCR_DPI) -> str:
    """Texto de uma página, por stdin/stdout do Tesseract — nenhum arquivo temporário em disco.

    Achado na primeira rodada real (23/09/2026): o Tesseract do Windows devolve as quebras de linha
    em CRLF no próprio stdout. `newline="\n"` na gravação não resolve — ele traduz o que o Python
    escreve, não o "\r" que já vem dentro do texto. Sem normalizar aqui, a cópia preservada sairia
    diferente byte a byte da que o runner produz, que é a série do §163 de novo, agora no conteúdo."""
    import subprocess
    r = subprocess.run([exe, "-", "-", "-l", idioma, "--dpi", str(dpi)],
                       input=png, capture_output=True, timeout=OCR_TIMEOUT_PAGINA)
    bruto = r.stdout.decode("utf-8", errors="replace")
    return bruto.replace("\r\n", "\n").replace("\r", "\n").strip()


def gravar_ocr(h: str, paginas: list) -> str:
    """evidencias/<sha256 do PDF>.ocr.txt, com marcador de página e CPF redigido antes do hash
    (mesma regra de gravar_texto). Nome à parte do `.txt` de propósito: o texto de OCR não pode
    ser confundido com camada de texto do documento, nem sobrescrevê-la."""
    EVID.mkdir(exist_ok=True)
    txt = "".join(f"\n=== página {i+1} (OCR) ===\n{t}\n" for i, t in enumerate(paginas))
    # Defesa em profundidade da normalização feita em ocr_pagina(): qualquer "\r" que chegue aqui
    # sairia no arquivo preservado e o tornaria dependente da máquina que rodou o OCR.
    txt = txt.replace("\r\n", "\n").replace("\r", "\n")
    txt, n_cpfs = redigir_dados_pessoais(txt)
    if n_cpfs:
        print(f"  [redação] {n_cpfs} CPF(s) removido(s) do texto de OCR antes de preservar")
    (EVID / f"{h}.ocr.txt").write_text(txt, encoding="utf-8", newline="\n")
    return hashlib.sha256(txt.encode("utf-8")).hexdigest()


def alvos_ocr(itens: dict) -> list:
    """Itens cujo PDF foi lido e não tinha texto: `texto_arquivo` gravado com menos caracteres que
    o piso, e sem OCR ainda. Idempotente por construção — quem tem `ocr_arquivo` sai da fila."""
    return [(h, it) for h, it in itens.items()
            if str(it.get("url", "")).lower().split("?")[0].endswith(".pdf")
            and it.get("texto_arquivo") and (it.get("caracteres") or 0) < OCR_MIN_CARACTERES
            and not it.get("ocr_arquivo") and not it.get("texto_manual")]


def ocr_pdfs(limite: int = 10, paginas_max: int = 0, alvo: str | None = None) -> int:
    """§177: cópia legível por OCR dos PDFs escaneados, para que a prova deixe de ser inexistente.

    Não decide nada e não toca em registro: só acrescenta prova, como o resto desta rotina.
    Falha de rede, PDF alterado ou Tesseract ausente viram lacuna declarada no log."""
    from datetime import date
    exe = tesseract_disponivel()
    idx = ler("evidencias.json", {"itens": {}}); itens = idx.setdefault("itens", {})
    alvos = filtrar_alvos(alvos_ocr(itens), alvo)
    if not exe:
        registrar_lacuna("OCR de PDF escaneado", "Tesseract não instalado nesta máquina",
                         canal="DOM", camada=2, strings=[a[0] for a in alvos[:5]])
        print(f"OCR: Tesseract ausente — {len(alvos)} alvo(s) ficam em lacuna declarada")
        return 0
    versao, idioma = motor_ocr(exe)
    feitos = falhas = 0
    for h, it in alvos[:limite]:
        u = it["url"]
        try:
            bruto = buscar(u, timeout=120)
        except Exception as e:  # noqa: BLE001
            falhas += 1
            registrar_lacuna(f"OCR de {u[:60]}", type(e).__name__, canal="DOM", camada=2, strings=[u])
            continue
        if hashlib.sha256(bruto).hexdigest() != h:
            falhas += 1
            registrar_lacuna(f"OCR de {u[:60]}", "documento mudou desde o hash registrado", canal="DOM", camada=2, strings=[u])
            continue
        try:
            imagens = rasterizar(bruto, OCR_DPI, paginas_max)
            textos = [ocr_pagina(png, exe, idioma) for png in imagens]
        except Exception as e:  # noqa: BLE001
            falhas += 1
            registrar_lacuna(f"OCR de {u[:60]}", f"rasterização/OCR falhou ({type(e).__name__})", canal="DOM", camada=2, strings=[u])
            continue
        caracteres = sum(len(t) for t in textos)
        if caracteres < OCR_MIN_CARACTERES:
            falhas += 1
            registrar_lacuna(f"OCR de {u[:60]}", f"OCR devolveu {caracteres} caractere(s) — abaixo do piso de {OCR_MIN_CARACTERES}",
                             canal="DOM", camada=2, strings=[u])
            continue
        oh = gravar_ocr(h, textos)
        it.update({"ocr_arquivo": f"evidencias/{h}.ocr.txt", "ocr_hash": oh, "ocr_paginas": len(textos),
                   "ocr_caracteres": caracteres, "ocr_em": date.today().isoformat(),
                   "ocr_motor": f"tesseract {versao} · modelo {idioma} · {OCR_DPI} DPI"})
        log_busca("site_municipal", 2, [u], "registro", nivel=None, hash_evidencia=h,
                  resultados=(f"cópia legível por OCR preservada: {len(textos)} página(s), {caracteres} caractere(s), "
                              f"modelo {idioma} — prova preservada, nunca insumo de classificação (§177)"))
        feitos += 1
        print(f"  ✓ {h[:12]}… → evidencias/{h}.ocr.txt ({len(textos)} página(s), {caracteres} caractere(s), modelo {idioma})")
    gravar("evidencias.json", idx)
    print(f"OCR: {feitos} cópia(s) legível(is) preservada(s), {falhas} falha(s); {len(alvos)} alvo(s) na fila")
    return 0


def autoteste_ocr() -> int:
    """Testes negativos permanentes das regras do §177, sem rede e sem Tesseract."""
    falhas = []
    # 1. a fila só chama quem foi lido e não tinha texto, e sai dela ao ganhar OCR
    itens = {
        "a" * 64: {"url": "http://x/p.pdf", "texto_arquivo": "evidencias/a.txt", "caracteres": 0},
        "b" * 64: {"url": "http://x/p.pdf", "texto_arquivo": "evidencias/b.txt", "caracteres": 9407},
        "c" * 64: {"url": "http://x/p.pdf", "texto_arquivo": "evidencias/c.txt", "caracteres": 0,
                   "ocr_arquivo": "evidencias/c.ocr.txt"},
        "d" * 64: {"url": "http://x/pagina.html", "texto_arquivo": "evidencias/d.txt", "caracteres": 0},
        "e" * 64: {"url": "http://x/p.pdf", "texto_arquivo": "evidencias/e.txt", "caracteres": 199},
    }
    fila = {h for h, _ in alvos_ocr(itens)}
    if fila != {"a" * 64, "e" * 64}:
        falhas.append(f"alvos_ocr devolveu {sorted(x[:1] for x in fila)}, esperado o escaneado e o abaixo do piso")
    # 2. o arquivo de OCR tem nome próprio e não sobrescreve a camada de texto do documento
    import tempfile
    global EVID
    real = EVID
    with tempfile.TemporaryDirectory() as d:
        try:
            EVID = Path(d)
            (EVID / "aa.txt").write_text("camada de texto do documento", encoding="utf-8", newline="\n")
            oh = gravar_ocr("aa", ["PREFEITURA MUNICIPAL", "DECRETO n 7.717/2024 CPF 123.456.789-00",
                                   "linha 1\r\nlinha 2\rlinha 3"])   # Tesseract do Windows devolve CRLF
            texto = (EVID / "aa.ocr.txt").read_text(encoding="utf-8")
            if (EVID / "aa.txt").read_text(encoding="utf-8") != "camada de texto do documento":
                falhas.append("gravar_ocr sobrescreveu o .txt do documento — o OCR tem arquivo próprio")
            if "123.456.789-00" in texto:
                falhas.append("gravar_ocr não redigiu CPF antes de preservar")
            if "(OCR)" not in texto:
                falhas.append("o marcador de página do OCR não diz que é OCR")
            if b"\r\n" in (EVID / "aa.ocr.txt").read_bytes():
                falhas.append("o texto de OCR saiu em CRLF (série do §163)")
            if oh != hashlib.sha256(texto.encode("utf-8")).hexdigest():
                falhas.append("o hash devolvido por gravar_ocr não é o do arquivo gravado")
        finally:
            EVID = real
    if falhas:
        print("✗ AUTOTESTE (OCR de escaneado):"); [print("   ", f) for f in falhas]; return 1
    print("✓ AUTOTESTE OK — fila só de escaneado, arquivo próprio do OCR, CPF redigido, marcador e LF.")
    return 0


PONT = {"plano", "plano_antigo", "plano_elaboracao", "coberto_estadual"}


def reconferir(limite: int = 200) -> int:
    """§3.8-bis: a rodada semanal REBAIXA e COMPARA o hash dos documentos-fonte já preservados.
    Hash diferente = 'documento-fonte alterado em dd/mm': entrada no log, marca em
    data/evidencias.json (alterado_em, hash_novo) e evento no feed (tipo documento_alterado).
    Nunca altera a categoria do registro — isso é julgamento humano."""
    from datetime import date
    mun = ler("municipios.json"); idx = ler("evidencias.json", {"itens": {}}); n = alt = falhas = 0
    for m in mun:
        h = m.get("hash_evidencia")
        if not h or not str(m.get("url", "")).startswith("http") or n + falhas >= limite: continue
        if (idx.get("itens") or {}).get(h, {}).get("texto_manual"):
            # 11/09/2026: item cuja chave é o sha256 do TEXTO preservado (extração manual), não do binário de origem.
            # Comparar com o hash do PDF rebaixado divergiria SEMPRE e publicaria um evento falso de
            # "documento-fonte alterado". Alteração desses itens é reconferida por leitura humana.
            continue
        try:
            bruto = buscar(m["url"], timeout=45)
        except Exception as e:  # noqa: BLE001
            falhas += 1; continue
        n += 1; h2 = __import__("hashlib").sha256(bruto).hexdigest()
        if h2 != h:
            alt += 1; hoje = date.today().strftime("%d/%m/%Y")
            it = idx["itens"].setdefault(h, {}); it["alterado_em"] = hoje; it["hash_novo"] = h2; it["municipio"] = f"{m['nome']}/{m['uf']}"
            log_busca(m.get("canal") or "DOM", 2, [m["url"]], "pista", uf=m["uf"], municipio=m["nome"],
                      resultados=f"documento-fonte alterado em {hoje}: hash {h[:12]}… → {h2[:12]}… (categoria mantida; julgamento humano)")
    gravar("evidencias.json", idx)
    print(f"reconferência: {n} documento(s) rebaixado(s) e comparado(s), {alt} alterado(s), {falhas} inacessível(is)")
    return 0


def main(limite: int = 200) -> int:
    mun = ler("municipios.json"); feitos = pulados = falhas = 0
    for m in mun:
        if m.get("categoria") not in PONT or not str(m.get("url", "")).startswith("http"):
            continue
        h_ex = m.get("hash_evidencia")
        if h_ex:
            it = (ler("evidencias.json", {"itens": {}}).get("itens") or {}).get(h_ex, {})
            if it.get("arquivo") or it.get("wayback"):
                pulados += 1; continue
            # 03/09/2026: hash registrado mas cópia perdida (não comitada) → re-preserva
        if feitos + falhas >= limite:
            break
        try:
            bruto = buscar(m["url"], timeout=45)
        except Exception as e:  # noqa: BLE001
            registrar_lacuna(f"evidência {m['nome']}/{m['uf']}", f"{type(e).__name__}", canal=m.get("canal") or "DOM",
                             camada=2, uf=m["uf"], municipio=m["nome"], strings=[m["url"]]); falhas += 1
            continue
        ext = (mimetypes.guess_extension(("application/pdf" if bruto[:4] == b"%PDF" else "text/html")) or ".bin").lstrip(".")
        h_novo = __import__("hashlib").sha256(bruto).hexdigest()
        if h_ex and h_novo != h_ex:
            registrar_lacuna(f"evidência {m['nome']}/{m['uf']}", f"documento mudou desde o hash registrado ({h_ex[:12]}… → {h_novo[:12]}…)", canal=m.get("canal") or "DOM", camada=2, uf=m["uf"], municipio=m["nome"], strings=[m["url"]])
        idx = ler("evidencias.json", {"itens": {}}); idx["itens"].pop(h_ex, None) if h_ex and h_novo != h_ex else None; gravar("evidencias.json", idx)
        m["hash_evidencia"] = preservar_evidencia(bruto, m["url"], ext, "preservar_evidencias")
        feitos += 1
    gravar("municipios.json", mun)
    print(f"evidências: {feitos} preservada(s), {pulados} já tinham hash, {falhas} falha(s) de rede (lacunas no log)")
    return 0


if __name__ == "__main__":
    lim = int(sys.argv[sys.argv.index("--limite") + 1]) if "--limite" in sys.argv else 200
    pgs = int(sys.argv[sys.argv.index("--paginas") + 1]) if "--paginas" in sys.argv else 0
    alv = sys.argv[sys.argv.index("--alvo") + 1] if "--alvo" in sys.argv else None
    sys.exit(autoteste_ocr() if "--autoteste" in sys.argv else
             ocr_pdfs(lim if "--limite" in sys.argv else 10, pgs, alv) if "--ocr" in sys.argv else
             ler_pdfs(lim, alv) if "--ler" in sys.argv else reconferir(lim) if "--reconferir" in sys.argv else main(lim))
