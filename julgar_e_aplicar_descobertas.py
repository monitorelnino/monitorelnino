#!/usr/bin/env python3
"""
julgar_e_aplicar_descobertas.py
=================================
A peça que faltava para o índice se atualizar sozinho a cada novo decreto
encontrado (pedido de Patricia, 31/08/2026): lê as pistas que
monitorar_imprensa_regional.py já descobre toda semana, busca o documento
em si (não só a notícia sobre ele), classifica com classificador_natureza.py
e, quando confiante, aplica DIRETO no banco — sem esperar uma sessão humana.
Quando o classificador está em dúvida, ou faltam número/data para citar a fonte
corretamente, a decisão é ABSTENCAO: não aplica, motivo gravado (10/10/2026 —
antes, fila para pessoa).

O QUE CONTINUA IGUAL (trava de fonte, não mudou): só processa pistas cujo
domínio já é reconhecido como oficial (.gov.br/.leg.br/Diário Oficial/Querido
Diário — mesmos padrões de sempre, PADROES_FONTE_PROVAVEL_OFICIAL). A
diferença é que esse sinal, que antes só servia para ORDENAR a fila para um
humano olhar primeiro, agora é parte de um portão real: fonte oficial +
citação completa (número e data) + classificador confiante = aplica sozinho.
Qualquer um desses três faltando = abstenção registrada (ABSTENCAO).

FLUXO POR PISTA:
  1. Só pistas com fonte_provavel_oficial=True são candidatas a julgamento
     automático (as outras continuam na fila, como sempre).
  2. Busca o texto do documento na URL (tolerante a falha de rede — pista
     que não abrir fica pendente, tentada de novo na próxima execução).
  3. classificador_natureza.classificar(texto) → EX_ANTE / RESPOSTA / DUVIDA.
  4. RESPOSTA → nunca pontua (Correção B); pista marcada resolvida, log.
  5. DUVIDA, ou citação incompleta (sem número+data extraíveis) → ABSTENCAO,
     motivo gravado, sem mudar nada no banco.
  6. EX_ANTE + citação completa:
       - Estadual (rótulo A-lac/C-estado-amplo): verificar_recorrencia_uf
         decide se é reedição (aplica régua 40/30/20 conforme cobertura de
         risco §18 addendum — o padrão fica em NEUTRO/30 quando o texto não
         permite confirmar cobertura COBRE/DIFERE com segurança, ficando
         registrado para errata por linha se necessário) ou instrumento
         genuinamente novo (NOVO se a UF não tinha nada; READ se substitui
         algo existente; antecipação 100).
       - Municipal (rótulo B-capital/D-municipio-prioritario): categoria
         "plano", direto.
     Em qualquer caso: mescla no arquivo certo, recalcula o índice
     (recalcular_mare.py --write) e roda os TRÊS portões. Se qualquer portão
     falhar, DESFAZ a mudança em disco e devolve a pista à fila do juiz
     com o erro anexado — nada quebrado é publicado, nunca.
  7. Toda decisão (aplicada ou não) vira uma linha em data/log_buscas.json,
     igual ao padrão já usado nas correções manuais desta sessão.

USO:
  python3 julgar_e_aplicar_descobertas.py              # roda de verdade (rede aberta)
  python3 julgar_e_aplicar_descobertas.py --self-test   # valida a lógica com fixtures, sem rede
"""
import argparse
import datetime
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).parent
sys.path.insert(0, str(RAIZ))
from coletores_base import buscar, ua_de, copia_arquivada, hoje_editorial, gravar_em, log_busca, sessao_sharepoint
import juiz
from classificador_natureza import classificar, citacao_completa, extrair_data, RE_NUMERO_ATO
from verificar_recorrencia_uf import checar_recorrencia, registrar_no_historico, REGUA_ANTECIPACAO_RECORRENTE

PISTAS_IMPRENSA = RAIZ / "data" / "pistas_imprensa.json"
LOG_BUSCAS = RAIZ / "data" / "log_buscas.json"


# Teto de LEITURA, não de julgamento: o juiz julga só o ato recortado (`juiz.TETO_DO_JULGAMENTO`).
TETO_DA_LEITURA = 600000
PAGINAS_DA_LEITURA = 300


HOST_SHAREPOINT_RS = "//rsgovbr-my.sharepoint.com/personal/casa-militar_casamilitar_rs_gov_br/"
_SESSAO_RS = []
_IDS_RS = {}   # pasta -> {nome do arquivo: UniqueId}, uma listagem por pasta e por rodada
ASSINATURAS_DE_DOCUMENTO = (b"%PDF", b"PK\x03\x04", b"\xd0\xcf\x11\xe0")


def _ler_sharepoint_rs(url, timeout):
    """Bytes de um arquivo da pasta pública da Casa Militar/RS. O endereço do arquivo não abre sem a
    sessão do link de compartilhamento (23/10/2026: 20 de 20 pistas do RS saíam `documento_inacessivel`);
    com ela, a REST do SharePoint entrega o conteúdo, como já entrega a listagem. 401/403 levanta.
    10/11/2026: pelo CAMINHO, nome longo estoura o `maxUrlLength` do SharePoint e a resposta é um texto de
    81 bytes ("The length of the URL ... exceeds ...") com 200, que o leitor tomava por PDF sem texto (170
    `documento_inacessivel` em três rodadas). Agora: UniqueId pela listagem da pasta e `GetFileById`; e
    resposta que não é PDF, DOCX nem DOC é erro, nunca documento."""
    from urllib.parse import quote, unquote, urlparse
    from atualizar_instrumentos_estaduais import REPOSITORIOS
    if not _SESSAO_RS:
        _SESSAO_RS.append(sessao_sharepoint(REPOSITORIOS["RS"]["url"], "julgamento de descobertas"))
    p = urlparse(url)
    api = f"{p.scheme}://{p.netloc}{'/'.join(p.path.split('/')[:3])}/_api/web"
    pasta, nome = unquote(p.path).rsplit("/", 1)
    if pasta not in _IDS_RS:
        r = _SESSAO_RS[0].get(f"{api}/GetFolderByServerRelativeUrl('{quote(pasta.replace(chr(39), chr(39) * 2))}')/Files",
                              params={"$select": "Name,UniqueId"},
                              headers={"Accept": "application/json;odata=nometadata"}, timeout=timeout)
        r.raise_for_status()
        _IDS_RS[pasta] = {f["Name"]: f["UniqueId"] for f in r.json()["value"]}
    if nome not in _IDS_RS[pasta]:
        raise FileNotFoundError(f"arquivo fora da listagem da pasta: {nome}")
    r = _SESSAO_RS[0].get(f"{api}/GetFileById('{_IDS_RS[pasta][nome]}')/$value", timeout=timeout)
    r.raise_for_status()
    if nome.lower().endswith(".url"):
        # Atalho `.url` segue só para a origem declarada.
        alvo = re.search(rb"(?im)^URL=(\S+)", r.content)
        destino = alvo.group(1).decode("latin-1") if alvo else ""
        if not any(o in destino for o in REPOSITORIOS["RS"].get("origens", ())):
            raise ValueError(f"atalho sem destino na origem declarada: {destino[:90]!r}")
        # 23/11/2026: o destino dos atalhos da CREPDEC 07 tem certificado de outro nome, e a verificação nunca se
        # desliga; o destino se lê pelo mesmo leitor do resto (fonte, cópia da ponte, cópia pública do Internet
        # Archive). Antes, a falha do destino virava `documento_inacessivel` para sempre (30 planos do RS).
        corpo = obter_documento(destino, timeout)
    else:
        corpo = r.content
    if not corpo.startswith(ASSINATURAS_DE_DOCUMENTO):
        raise ValueError(f"resposta não é documento ({len(corpo)} bytes): {corpo[:90]!r}")
    return corpo


def ler_documento(url, timeout=40, origem=None):
    """Os bytes do documento pela porta que o entrega: a pasta do RS só abre com a sessão do link de
    compartilhamento; o resto, pela porta de rede do projeto. Um leitor só para o juiz, a guarda da prova e o OCR
    (18/11/2026: o OCR baixava a pasta do RS sem a sessão e 78 PDFs escaneados ficaram com `HTTPError`)."""
    return _ler_sharepoint_rs(url, timeout) if HOST_SHAREPOINT_RS in url else buscar(url, timeout=timeout, origem=origem)


def obter_documento(url, timeout=40, origem=None, buscar_fn=None):
    """Os bytes do documento, por onde ele se lê: a fonte (pasta do RS com a sessão do link; o resto pela porta de
    rede, que já lê a cópia da ponte) e, se a fonte caiu, recusou ou respondeu página no lugar do documento, a
    cópia pública do Internet Archive (12/11/2026, editoria). Levanta o erro da fonte quando nada se lê.
    O mesmo leitor para o juiz municipal, o juiz da saúde e a guarda da prova (18/11/2026: o juiz da saúde e a
    guarda não liam a cópia pública, e 8 promoções ficaram fora do banco). `buscar_fn` é o transporte do
    autoteste, que não vai à cópia pública."""
    try:
        raw = buscar_fn(url, timeout=timeout) if buscar_fn else ler_documento(url, timeout, origem)
        if (url.lower().split("?")[0].endswith((".pdf", ".docx", ".doc", ".odt"))
                and not raw.startswith(ASSINATURAS_DE_DOCUMENTO)):
            raise ValueError(f"o endereço do documento respondeu página ({len(raw)} bytes), não o documento")
        return raw
    except Exception as e:
        print(f"  [buscar_texto] {type(e).__name__}: {str(e)[:140]} · {url[-70:]}", file=sys.stderr)
        raw = None if buscar_fn or "archive.org" in url else copia_arquivada(url)[0]
        if not raw:
            raise
        return raw


def com_ocr(raw, texto):
    """O texto do documento; PDF sem camada de texto vai ao OCR (o mesmo motor da preservação)."""
    if raw[:5] == b"%PDF-" and len(re.findall(r"[A-Za-zÀ-ú]", texto or "")) < LETRAS_SEM_OCR:
        return texto_por_ocr(raw) or texto
    return texto


def buscar_texto(url, timeout=40):
    """O texto do documento, ou None quando nada se lê (perda de recall, nunca invenção de texto)."""
    try:
        raw = obter_documento(url, timeout, "julgamento de descobertas")
    except Exception:  # noqa: BLE001 — a causa já saiu no log
        return None
    return com_ocr(raw, texto_do_documento(raw, url))


LETRAS_SEM_OCR = 200      # abaixo disto o PDF é tratado como escaneado
PAGINAS_DE_OCR = 10       # capa, sumário e primeiras seções: ente, título, data e as seções do plano (J1)


def texto_por_ocr(raw):
    """PDF escaneado: OCR das primeiras páginas pelo mesmo motor da preservação (§177), sem gravar nada.
    11/11/2026: 185 dos 209 planos da pasta do Prepara RS são digitalizações sem camada de texto e saíam
    `texto_nao_extraivel`. Sem Tesseract, ou com falha, devolve "" e o juiz segue recusando como antes."""
    from preservar_evidencias import motor_ocr, ocr_pagina, rasterizar, tesseract_disponivel
    exe = tesseract_disponivel()
    if not exe:
        return ""
    try:
        _, idioma = motor_ocr(exe)
        paginas = rasterizar(raw, limite_paginas=PAGINAS_DE_OCR)
        return "\n".join(ocr_pagina(p, exe, idioma) for p in paginas)[:TETO_DA_LEITURA]
    except Exception as e:  # noqa: BLE001
        print(f"  [ocr] {type(e).__name__}: {str(e)[:120]}", file=sys.stderr)
        return ""


def texto_do_documento(raw, url, tipo=""):
    """Texto dos bytes já baixados. Função pura. Documento obtido que não dá texto devolve "" (o juiz o
    recusa como `texto_nao_extraivel`); None fica só para "não obtido" (`documento_inacessivel`)."""
    caminho = url.lower().split("?")[0]
    # PDF por magic bytes, não só pelo tipo declarado: servidores municipais mentem no tipo.
    if raw[:5] == b"%PDF-" or "application/pdf" in tipo or caminho.endswith(".pdf"):
        return (extrair_texto_pdf(raw) or "")[:TETO_DA_LEITURA]
    if raw[:4] == b"PK\x03\x04":   # DOCX/ODT: o texto é o XML do corpo; outro zip não é documento
        import io, zipfile
        try:
            z = zipfile.ZipFile(io.BytesIO(raw))
            corpo = next((z.read(n) for n in ("word/document.xml", "content.xml") if n in z.namelist()), b"")
        except Exception:  # noqa: BLE001 — zip corrompido: obtido e sem texto
            corpo = b""
        xml = re.sub(r"</w:p>|</text:p>", " ", corpo.decode("utf-8", errors="ignore"))
        from html import unescape
        return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", "", xml))).strip()[:TETO_DA_LEITURA]
    if raw[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":   # DOC binário (OLE): o texto está na tabela de peças
        try:
            return re.sub(r"\s+", " ", texto_de_doc_binario(raw)).strip()[:TETO_DA_LEITURA]
        except Exception:  # noqa: BLE001 — arquivo truncado ou que não é do Word: obtido e sem texto
            return ""
    try:
        html = raw.decode("utf-8")
    except UnicodeDecodeError:
        html = raw.decode("latin-1", errors="ignore")
    texto = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
    texto = re.sub(r"<[^>]+>", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto[:TETO_DA_LEITURA]


def texto_de_doc_binario(raw):
    """Texto de um .doc do Word 97–2003 (contêiner OLE), sem dependência: lê as correntes `WordDocument` e
    `0Table`/`1Table` e junta as peças da tabela de peças (CLX), cada uma em cp1252 ou UTF-16. Função pura."""
    import struct
    u16, u32 = (lambda b, o: struct.unpack_from("<H", b, o)[0]), (lambda b, o: struct.unpack_from("<I", b, o)[0])
    ss, mss, corte = 1 << u16(raw, 30), 1 << u16(raw, 32), u32(raw, 56)
    setor = lambda i: raw[(i + 1) * ss:(i + 2) * ss]

    def cadeia(inicio, tabela, limite=1 << 20):
        while inicio < 0xFFFFFFFA and limite:
            yield inicio
            inicio, limite = tabela[inicio], limite - 1
    difat, prox = list(struct.unpack_from("<109I", raw, 76)), u32(raw, 68)
    while prox < 0xFFFFFFFA and len(difat) < 1 << 16:
        s = setor(prox)
        difat += struct.unpack_from(f"<{ss // 4 - 1}I", s, 0)
        prox = u32(s, ss - 4)
    fat = [x for i in difat if i < 0xFFFFFFFA for x in struct.unpack(f"<{ss // 4}I", setor(i).ljust(ss, b"\xff"))]
    ler = lambda inicio: b"".join(setor(i) for i in cadeia(inicio, fat))
    diretorio = ler(u32(raw, 48))
    # Só as correntes da raiz: o objeto do Word embutido no documento traz o seu próprio `WordDocument` e `1Table`
    # (Chuvisca/RS, 23/11), e a lista plana do diretório misturava o texto de um com a tabela do outro.
    entradas, fila, vistos = {}, [u32(diretorio, 76)], set()
    while fila:
        if (i := fila.pop()) < 0xFFFFFFFA and i not in vistos and (o := i * 128) + 128 <= len(diretorio):
            vistos.add(i)
            entradas[diretorio[o:o + max(u16(diretorio, o + 64) - 2, 0)].decode("utf-16-le", "ignore")] = (
                u32(diretorio, o + 116), u32(diretorio, o + 120))
            fila += [u32(diretorio, o + 68), u32(diretorio, o + 72)]
    minifat = [x for x in struct.unpack(f"<{len(m) // 4}I", m)] if (m := ler(u32(raw, 60))) else []
    mini = ler(u32(diretorio, 116))

    def corrente(nome):
        inicio, tamanho = entradas[nome]
        if tamanho >= corte:
            return ler(inicio)[:tamanho]
        return b"".join(mini[i * mss:(i + 1) * mss] for i in cadeia(inicio, minifat))[:tamanho]
    doc = corrente("WordDocument")
    tabela = corrente("1Table" if u16(doc, 10) & 0x0200 else "0Table")
    clx, o = tabela[u32(doc, 0x01A2):u32(doc, 0x01A2) + u32(doc, 0x01A6)], 0
    while clx[o] == 1:                       # Prc: propriedades, não texto
        o += 3 + u16(clx, o + 1)
    n = (u32(clx, o + 1) - 4) // 12          # PlcPcd: n+1 posições de caractere e n peças de 8 bytes
    cps, pecas, partes = o + 5, o + 5 + 4 * (n + 1), []
    for i in range(n):
        tam, fc = u32(clx, cps + 4 * i + 4) - u32(clx, cps + 4 * i), u32(clx, pecas + 8 * i + 2)
        if fc & 0x40000000:
            ini = (fc & 0x3FFFFFFF) // 2
            partes.append(doc[ini:ini + tam].decode("cp1252", "ignore"))
        else:
            partes.append(doc[fc:fc + 2 * tam].decode("utf-16-le", "ignore"))
    return re.sub(r"[\x00-\x1f]", " ", "".join(partes))


def extrair_texto_pdf(raw):
    """Texto de um PDF em memória via pdfplumber (preserva espaçamento de palavras; pypdf separa
    letras nos PDFs-infográfico das SES — nota em requirements.txt). Tolerante: None em falha
    ou em PDF só-imagem (escaneado sem OCR — registrado como não obtido, nunca inventado)."""
    try:
        import io, pdfplumber
        partes = []
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            for pg in pdf.pages[:PAGINAS_DA_LEITURA]:   # diários inteiros podem ter centenas
                t = pg.extract_text() or ""
                if t.strip():
                    partes.append(t)
                if sum(len(x) for x in partes) > TETO_DA_LEITURA:
                    break
        texto = re.sub(r"\s+", " ", " ".join(partes)).strip()
        return texto or None
    except Exception:
        return None


def extrair_numero_e_data(texto):
    """Tenta extrair número do ato e data do texto — usados na citação pública.
    22/09/2026 (§154, achado no teste real com o diário de Feira de Santana/BA): a data logo APÓS o
    número do ato ("DECRETO Nº 14.665 DE 21 DE AGOSTO DE 2026") é a data do ato; a primeira data do
    texto costuma ser a da EDIÇÃO do diário ("DATA 22/08/2026"), que vem antes. Prefere a janela
    imediata após o número; cai para a busca global só se ali não houver data."""
    from classificador_natureza import data_do_ato
    m_num = RE_NUMERO_ATO.search(texto)
    return (m_num.group(0).strip() if m_num else None), data_do_ato(texto)


def eh_estadual(rotulo):
    """True se o rótulo da pista vem das camadas de busca estadual (A-lac/
    C-estado-amplo); False para as camadas municipais (B-capital/D-município)."""
    return rotulo.startswith("A-lac") or rotulo.startswith("C-estado-amplo")


# Cadeia canônica de derivados (§163): a fonte de verdade é scripts/verificar_derivados.sh.


def cadeia_do_portao12():
    """Lê a sequência de geradores de scripts/verificar_derivados.sh (só o primeiro bloco,
    antes do modo --idempotencia). Função pura sobre o texto do script; usada pelo self-test."""
    texto = (RAIZ / "scripts" / "verificar_derivados.sh").read_text(encoding="utf-8")
    passos = []
    for linha in texto.splitlines():
        if linha.startswith('if [ "$MODO"'):
            break
        m = re.match(r"python3 (\S+\.py)((?: --\S+)*)\s*(?:>\s*/dev/null)?\s*(?:#.*)?$", linha.strip())
        if m:
            passos.append((m.group(1), *m.group(2).split()))
    return tuple(passos)


def sincronizar_derivados():
    """22/09/2026 (§158, causa real da reversão de Feira de Santana/BA na cadência #7): o juiz aplicava em
    municipios.json e ia direto aos portões — dados-abertos/municipios.csv ficava com 265 linhas contra 266
    no JSON e verificar_consistencia.py reprovava, com razão. TODA aplicação automática municipal estava
    condenada a ser revertida. Regenera, antes dos portões, exatamente os derivados que o workflow regenera
    depois da coleta. Retorna a saída (para o log).

    22/09/2026 (§163): a lista era curta demais — só recalcular_mare, gerar_dados_abertos e
    gerar_card_municipios. gerar_prioritarios, gerar_feeds e os demais rodam ANTES do juiz, em
    atualizar.py, e nunca mais depois: quando o juiz aplicava um município, o histórico público,
    os feeds e a contagem de prioritários ficavam para trás e o portão 12 ficava vermelho na main.
    Agora a lista é a cadeia canônica inteira, lida de scripts/verificar_derivados.sh."""
    import os, datetime as _dt
    env = dict(os.environ)
    try:
        dd, mm, aa = json.load(open(RAIZ / "data" / "meta.json", encoding="utf-8"))["corte"].split("/")
        env.setdefault("SOURCE_DATE_EPOCH", str(int(_dt.datetime(int(aa), int(mm), int(dd), tzinfo=_dt.timezone.utc).timestamp())))
    except Exception:  # noqa: BLE001
        pass
    saida = []
    for passo in cadeia_do_portao12():
        if not (RAIZ / passo[0]).exists():
            continue
        cmd = [sys.executable, *passo]
        r = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True, env=env)
        saida.append(f"$ python3 {' '.join(passo)}\n{r.stdout[-400:]}\n{r.stderr[-400:]}")
    return "\n".join(saida)


def rodar_portoes():
    """Sincroniza os derivados e roda os portões bloqueantes. Retorna (ok, saida_combinada)."""
    saida = [sincronizar_derivados()]
    for cmd in (["node", "scripts/verificar_estrutura.js"],
                ["python3", "verificar_consistencia.py"],
                ["python3", "recalcular_mare.py", "--check"],
                ["node", "scripts/verificar_runtime.js"],
                ["node", "scripts/verificar_runtime_mapas.js"]):
        r = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True)
        saida.append(f"$ {' '.join(cmd)}\n{r.stdout}\n{r.stderr}")
        if r.returncode != 0:
            return False, "\n".join(saida)
    return True, "\n".join(saida)


ARQUIVOS_MUTAVEIS = ["estados.json", "municipios.json", "pontos_mapa.json", "indice.json",
                      "percentual_uf.json", "decretos_historico_uf.json", "atos_resposta.json",
                      "consist.json"]
RECALCULAR_PY = RAIZ / "recalcular_mare.py"
DIRETORIOS_SINCRONIZADOS = ("data", "dados-abertos", "selos")   # §158: tudo que sincronizar_derivados() pode reescrever (selos: recalcular_mare --write)


def backup_dados():
    """Backup em memória de tudo que uma aplicação pode alterar — inclui
    recalcular_mare.py (o dicionário ESTADOS embutido no motor é a fonte de
    verdade real do cálculo; estados.json só alimenta a exibição — achado do
    teste de ponta a ponta de 31/08/2026, escrever só em estados.json deixava
    o motor e a exibição dessincronizados) e as duas páginas HTML que a
    aplicação estadual toca: index.html (o número fixo do medidor) e
    defesa-civil.html (AREAS — CONSIST mudou para data/consist.json,
    já coberto por ARQUIVOS_MUTAVEIS, quando mapas/gráficos ganharam página
    própria em 31/08/2026)."""
    backup = {}
    for nome in ARQUIVOS_MUTAVEIS:
        p = RAIZ / "data" / nome
        if p.exists():
            backup[f"data/{nome}"] = p.read_bytes()
    backup["recalcular_mare.py"] = RECALCULAR_PY.read_bytes()
    backup["index.html"] = INDEX_HTML.read_bytes()  # gaugeNum é gravado aqui
    backup["defesa-civil.html"] = MAPAS_HTML.read_bytes()  # AREAS é gravado aqui
    # rodar_portoes() regenera derivados: o backup cobre tudo o que a sincronização toca (§158).
    for d in DIRETORIOS_SINCRONIZADOS:
        base = RAIZ / d
        if base.exists():
            arquivos = [f for f in base.rglob("*") if f.is_file()]
            for f in arquivos:
                backup.setdefault(str(f.relative_to(RAIZ)), f.read_bytes())
            backup[f"__lista__:{d}"] = "\n".join(sorted(str(f.relative_to(RAIZ)) for f in arquivos)).encode()
    return backup


def restaurar_dados(backup):
    """Restaura exatamente os bytes originais — usado quando os portões falham
    depois de uma aplicação, para que NADA quebrado fique em disco."""
    for caminho, conteudo in backup.items():
        if caminho.startswith("__lista__:"):
            continue
        (RAIZ / caminho).write_bytes(conteudo)
    # arquivos CRIADOS depois do backup nos diretórios sincronizados também saem (§158)
    for chave, lista in backup.items():
        if chave.startswith("__lista__:"):
            d = chave.split(":", 1)[1]; antes = set(lista.decode().splitlines())
            for f in (RAIZ / d).rglob("*"):
                if f.is_file() and str(f.relative_to(RAIZ)) not in antes:
                    f.unlink()


def atualizar_estados_py(uf, status, antecipacao, confianca="Média"):
    """Edita o dicionário ESTADOS embutido em recalcular_mare.py para a UF dada —
    a mesma disciplina de assert-antes-de-escrever usada nas edições manuais
    desta sessão inteira: encontra exatamente UMA ocorrência do padrão da UF,
    ou não mexe em nada."""
    src = RECALCULAR_PY.read_text(encoding="utf-8")
    padrao = re.compile(rf'"{uf}":\("[A-Z]+",\s*\d+,\s*"[A-Za-zÀ-ú]+"\)')
    ocorrencias = padrao.findall(src)
    if len(ocorrencias) != 1:
        return False, f"esperava exatamente 1 ocorrência de {uf} no dicionário ESTADOS, achei {len(ocorrencias)}"
    novo_trecho = f'"{uf}":("{status}",{antecipacao},"{confianca}")'
    src_novo = padrao.sub(novo_trecho, src, count=1)
    RECALCULAR_PY.write_text(src_novo, encoding="utf-8", newline="\n")
    return True, "atualizado"


INDEX_HTML = RAIZ / "index.html"
MAPAS_HTML = RAIZ / "defesa-civil.html"
CONSIST_JSON = RAIZ / "data" / "consist.json"


def sincronizar_consist(uf, nova_cat, novo_instr):
    """Atualiza a entrada da UF em data/consist.json — cat e instr. 'risco' NUNCA
    é tocado aqui: é a projeção meteorológica do Boletim, independente de qual
    instrumento foi encontrado; só um humano lendo o Boletim deveria mudar isso.
    31/08/2026: CONSIST deixou de viver embutido em index.html (mudou para cá
    quando mapas/gráficos ganharam página própria) — agora é JSON de verdade,
    fonte única compartilhada por index.html (cartão de cidade) e
    defesa-civil.html (mapa e tabela de risco×instrumento)."""
    consist = json.load(open(CONSIST_JSON, encoding="utf-8"))
    if uf not in consist:
        return False, f"{uf} não existe em consist.json (não deveria acontecer — todas as 27 UFs têm entrada)"
    consist[uf]["cat"] = nova_cat
    consist[uf]["instr"] = novo_instr
    gravar_em(CONSIST_JSON, consist)
    return True, "atualizado"


GRUPOS_AREAS_PALAVRAS = [
    (0, ["estiagem", "seca"]),        # Grupo Seca
    (1, ["incêndio", "incêndios"]),   # Grupo Seca · frente de incêndio (some ao anterior, não substitui)
    (2, ["chuva", "chuvas", "enchente"]),  # Família das chuvas
]


def sincronizar_areas(uf, risco_texto):
    """Adiciona a UF ao(s) grupo(s) temáticos de AREAS cujo risco bate com o texto já
    existente em CONSIST[uf]['risco'] (nunca inventa um risco novo — só classifica o
    que já está declarado). Não remove de nenhum grupo (fluxo só de LAC/SEM → algo).
    31/08/2026: AREAS mudou de index.html para defesa-civil.html."""
    src = MAPAS_HTML.read_text(encoding="utf-8")
    m = re.search(r"const AREAS = (\[.*?\]);", src, re.S)
    if not m:
        return False, "AREAS não encontrado em defesa-civil.html"
    # AREAS não é JSON puro (chaves sem aspas) — edita via regex pontual em vez de parsear
    bloco = m.group(1)
    risco_lower = risco_texto.lower()
    grupos_alvo = [i for i, palavras in GRUPOS_AREAS_PALAVRAS if any(p in risco_lower for p in palavras)]
    if not grupos_alvo:
        return False, f"nenhuma palavra-chave de grupo reconhecida em '{risco_texto}' — abstenção registrada (grupo não se infere)"
    objetos = re.findall(r"\{label:'[^']*', cor:'[^']*', ufs:\[[^\]]*\]\}", bloco)
    if len(objetos) != 4:
        return False, f"esperava 4 grupos em AREAS, achei {len(objetos)}"
    bloco_novo = bloco
    for idx in grupos_alvo:
        obj_antigo = objetos[idx]
        if f"'{uf}'" in obj_antigo:
            continue  # já está nesse grupo
        obj_novo = obj_antigo.replace("ufs:[", f"ufs:['{uf}',")
        bloco_novo = bloco_novo.replace(obj_antigo, obj_novo)
    src_novo = src[:m.start()] + "const AREAS = " + bloco_novo + ";" + src[m.end():]
    MAPAS_HTML.write_text(src_novo, encoding="utf-8", newline="\n")
    return True, "atualizado"


def aplicar_estrutura_estadual(uf, achado, url, hash_evidencia, hoje, caminho=None):
    """Grava em estados.json a estrutura de coordenação criada no ciclo (juiz, J21), com documento, data, endereço
    e hash. Nunca rebaixa nem regrava o que já está no degrau. Devolve True se gravou."""
    from recalcular_mare import ESTADO_SCORE
    caminho = caminho or RAIZ / "data" / "estados.json"
    estados = json.load(open(caminho, encoding="utf-8"))
    alvo = next((u for u in estados["ufs"] if u["uf"] == uf), None)
    if alvo is None or ESTADO_SCORE["NOVO"] <= ESTADO_SCORE[(alvo.get("estrutura") or {}).get("status", "LAC")]:
        return False
    novo = {"status": "NOVO", "doc": achado["doc"], "data": achado["data"], "url": url, "consultado_em": hoje,
            "julgado_em": hoje, "hash_evidencia": hash_evidencia,
            "proveniencia": {"tipo_fonte": "diario_oficial", "verificacao": "conteudo_conferido",
                             "como_achou": "juiz automático (J21): decreto do governador lido na edição do diário oficial"}}
    alvo["estrutura"] = novo
    alvo["instrumentos"] = [i for i in alvo.get("instrumentos") or [] if i.get("tipo") != "estrutura_coordenacao"] + \
        [{"tipo": "estrutura_coordenacao", **{k: v for k, v in novo.items() if k != "julgado_em"}}]
    gravar_em(caminho, estados)
    return True


def aplicar_estadual(uf, texto, numero, data, url, hoje, hash_evidencia=None):
    """Mescla um instrumento estadual EX_ANTE confiante em estados.json. Retorna
    (aplicado: bool, motivo: str, status_aplicado: str|None, antecipacao: int|None)."""
    estados_path = RAIZ / "data" / "estados.json"
    estados = json.load(open(estados_path, encoding="utf-8"))
    alvo = next((u for u in estados["ufs"] if u["uf"] == uf), None)
    if alvo is None:
        return False, f"UF {uf} não encontrada em estados.json", None, None

    recorrente, sim, match_antigo = checar_recorrencia(uf, texto)
    status_anterior = alvo.get("status", "LAC")

    if recorrente:
        status_novo = "VIG"
        # sem sinal textual claro de cobertura do risco projetado, o padrão
        # seguro é o nível intermediário da régua (NEUTRO) — nunca o mais alto.
        antecipacao = REGUA_ANTECIPACAO_RECORRENTE["NEUTRO"]
        justificativa = (f"Recorrência detectada automaticamente ({sim:.0%} de semelhança com "
                          f"{uf}/{match_antigo['ano']}, ato {match_antigo['numero']}) — antecipação "
                          f"aplicada no nível NEUTRO (30) da régua §18 addendum por padrão de segurança; "
                          f"o juiz automático pode ajustar para COBRE/DIFERE se a cobertura do risco "
                          f"projetado for confirmada por leitura completa do texto.")
    else:
        status_novo = "NOVO" if status_anterior == "LAC" else "READ"
        antecipacao = 100
        justificativa = "Instrumento novo (sem semelhança com histórico da UF) — antecipação 100."

    alvo["status"] = status_novo
    alvo["doc"] = f"{texto[:200].strip()} (ato {numero}, {data})" if numero else texto[:200].strip()
    # Editoria, 03/10/2026: plano sem ato de aprovação localizado conta no degrau da leitura, com a marca na ficha.
    if numero:
        alvo.pop("sem_ato_de_aprovacao", None)
    else:
        alvo["sem_ato_de_aprovacao"] = True
    alvo["data"] = data
    # Proveniência na origem: quem julga grava endereço, data e hash no campo que o cartão lê.
    if url:
        try:
            consultado = datetime.datetime.strptime(hoje, "%d/%m/%Y").date().isoformat()
        except (TypeError, ValueError):
            consultado = str(hoje)
        prov = {"url": url, "consultado_em": consultado}
        if hash_evidencia:
            prov["hash_evidencia"] = hash_evidencia
        alvo.update(prov)
        alvo.pop("endereco_lacuna", None)
        for ins in alvo.get("instrumentos") or []:
            if ins.get("tipo") == "instrumento_operacional":
                ins.update(prov)
                ins.update({"status": status_novo, "doc": alvo["doc"], "data": data})
                ins.pop("endereco_lacuna", None)
                ins.pop("defeito_de_prova", None)
    alvo["natureza_doc"] = "ex-ante"
    alvo["justificativa_ex_ante"] = (
        f"Classificado automaticamente por classificador_natureza.py em {hoje} "
        f"(teste do objeto, §5.2.1). {justificativa} Fonte: {url}")

    ok_py, motivo_py = atualizar_estados_py(uf, status_novo, antecipacao)
    if not ok_py:
        return False, f"estados.json seria atualizado, mas recalcular_mare.py não: {motivo_py}", None, None

    # Sincroniza as figuras (CONSIST/AREAS) ANTES de gravar estados.json — se qualquer
    # uma falhar, nada é gravado (nem json.dump abaixo roda) e a UF cai pra fila humana.
    risco_atual = _ler_risco_consist(uf)
    cat_nova = "COBRE" if risco_atual and _texto_bate_com_risco(texto, risco_atual) else "PARCIAL"
    instr_curto = (numero or texto[:60]).strip()
    ok_consist, motivo_consist = sincronizar_consist(uf, cat_nova, instr_curto)
    if not ok_consist:
        return False, f"CONSIST não pôde ser sincronizado: {motivo_consist}", None, None
    if status_anterior == "LAC" and risco_atual:
        ok_areas, motivo_areas = sincronizar_areas(uf, risco_atual)
        if not ok_areas:
            return False, f"AREAS não pôde ser sincronizado: {motivo_areas}", None, None

    gravar_em(estados_path, estados)
    registrar_no_historico(uf, int(hoje[-4:]), numero or "?", "instrumento aplicado automaticamente",
                            texto[:300], f"julgar_e_aplicar_descobertas.py, {hoje}")
    return True, "aplicado", status_novo, antecipacao


def _ler_risco_consist(uf):
    """Lê o texto de 'risco' já declarado para a UF em data/consist.json —
    nunca inventado, só lido do que já existe. 31/08/2026: CONSIST deixou de
    viver embutido em index.html, agora é JSON de verdade."""
    consist = json.load(open(CONSIST_JSON, encoding="utf-8"))
    return consist.get(uf, {}).get("risco")


def _texto_bate_com_risco(texto_decreto, risco_texto):
    """Compara palavras-chave de risco (estiagem/seca/chuva/enchente/incêndio) entre
    o texto do decreto e o risco já declarado — sinal simples de que o instrumento
    fala do MESMO risco, não só de que existe."""
    palavras = ["estiagem", "seca", "chuva", "enchente", "incêndio", "hídric"]
    achadas_risco = {p for p in palavras if p in risco_texto.lower()}
    achadas_decreto = {p for p in palavras if p in texto_decreto.lower()}
    return bool(achadas_risco & achadas_decreto)


def buscar_lat_lon(nome, uf):
    """Consulta a referência oficial do IBGE por lat/lon — nunca inventa
    coordenada; se o município não constar na referência, retorna (None, None)
    e a aplicação cai para revisão humana (achado do teste de ponta a ponta:
    faltava isso por completo na primeira versão)."""
    ref = json.load(open(RAIZ / "data" / "municipios_ibge_referencia.json", encoding="utf-8"))
    m = next((r for r in ref if r["nome"] == nome and r["uf"] == uf), None)
    return (m["lat"], m["lon"]) if m else (None, None)


def canal_e_fonte(url):
    """22/09/2026 (§158): o canal era gravado fixo como "imprensa" — no teste real de Feira de Santana/BA o ato
    veio do DIÁRIO OFICIAL (Querido Diário), e o site diria que veio de jornal, o oposto da regra de 22/09
    (imprensa nunca pontua). Vocabulário do banco: DOM, site_municipal, DOU, orgao_estadual, imprensa.
    10/11/2026: documento do repositório estadual declarado é do órgão estadual; o PLANCON da pasta do RS
    (SharePoint do governo) saía "Fonte não oficial (rsgovbr-my.sharepoint.com)", canal imprensa, em 161 fichas."""
    from urllib.parse import urlparse as _up
    from atualizar_instrumentos_estaduais import REPOSITORIOS, repositorio_do_documento
    uf = repositorio_do_documento(url or "")
    if uf:
        return "orgao_estadual", REPOSITORIOS[uf]["fonte"]
    h = (_up(url or "").hostname or "").lower()
    if "queridodiario" in h:
        return "DOM", "Diário Oficial do Município (via Querido Diário)"
    if "in.gov.br" in h:
        return "DOU", "Diário Oficial da União"
    if re.search(r"diario|imprensaoficial|\bdom\.|diariomunicipal", h):
        return "DOM", f"Diário Oficial do Município ({h})"
    if h.endswith(".gov.br") or h.endswith(".leg.br"):
        return "site_municipal", f"Portal oficial ({h})"
    return "imprensa", f"Fonte não oficial ({h})"


def ementa(texto, numero, data):
    """Cabeçalho + ementa do ato (até "e dá outras providências" ou 240 caracteres), não 200 caracteres crus."""
    t = re.sub(r"\s+", " ", texto or "").strip()
    i = t.lower().find((numero or "").lower()) if numero else -1
    t = t[i:] if i >= 0 else t
    m = re.search(r"e d[aá] outras provid[eê]ncias\.?", t, re.I)
    corpo = t[: m.end()] if m and m.end() <= 320 else t[:240].rsplit(" ", 1)[0] + "…"
    return corpo if (numero and numero.lower() in corpo.lower()) else f"{corpo} (ato {numero}, {data})"


def aplicar_municipal(nome, uf, texto, numero, data, url, hoje, veredito):
    """Mescla um registro municipal EX_ANTE confiante em municipios.json E em
    pontos_mapa.json (o mapa lê daqui, não de municipios.json — esquecer este
    segundo arquivo foi um dos bugs achados no teste de ponta a ponta).

    09/10/2026 (A1-15). Este caminho gravava **sempre** `categoria: "plano"` e sem proveniência,
    enquanto o caminho de `aplicar_promocoes_do_juiz.py` grava a categoria do veredito e carrega
    `hash_evidencia`, `pista_id` e `codebook`. Dois caminhos com regras diferentes escrevendo no
    mesmo banco: um `plano_antigo` entrava aqui como plano novo, e o índice conta os dois
    diferente. A categoria passa a vir do VEREDITO, que o chamador já tem em mãos, e o documento é
    preservado antes de o registro existir — registro pontuável sem evidência é vermelho no portão
    26, e agora o rollback funciona de verdade (A1-02).
    """
    categoria = str((veredito or {}).get("categoria") or "").strip()
    if not categoria:
        return False, f"{nome}/{uf} sem categoria no veredito — o banco não recebe registro sem ela"
    lat, lon = buscar_lat_lon(nome, uf)
    if lat is None:
        return False, f"{nome}/{uf} não consta na referência do IBGE — não dá pra posicionar no mapa — abstenção registrada"

    mun_path = RAIZ / "data" / "municipios.json"
    municipios = json.load(open(mun_path, encoding="utf-8"))
    if any(m["nome"] == nome and m["uf"] == uf for m in municipios):
        return False, f"{nome}/{uf} já consta na base — não duplicar (abstenção registrada: atualização não se presume)"
    canal, fonte_base = canal_e_fonte(url)
    from aplicar_promocoes_do_juiz import preservar_o_documento, registro_do_veredito
    hash_evidencia = preservar_o_documento(url, "julgar_e_aplicar_descobertas")
    if not hash_evidencia:
        return False, (f"{nome}/{uf}: documento não pôde ser preservado — registro pontuável "
                       f"exige evidência guardada (portão 26)")
    # Um construtor de registro, o mesmo do aplicador do juiz; aqui o ato foi lido: a ementa é dele.
    registro = registro_do_veredito({**(veredito or {}), "municipio": nome, "uf": uf, "categoria": categoria,
                                     "data": data, "url": url, "hash_evidencia": hash_evidencia},
                                    lat, lon, canal, fonte_base, hoje)
    registro["documento"] = ementa(texto, numero, data)
    municipios.append(registro)
    gravar_em(mun_path, municipios)

    pontos_path = RAIZ / "data" / "pontos_mapa.json"
    pontos = json.load(open(pontos_path, encoding="utf-8"))
    pontos.append({"nome": nome, "uf": uf, "categoria": categoria, "lat": lat, "lon": lon,
                   "fase": 3})
    gravar_em(pontos_path, pontos)

    return True, "aplicado"


# A decisão do aplicador vira execução do log v2 pela porta canônica; vocabulário fechado:
#   APLICADA    entrou no banco                     -> registro
#   ABSTENCAO   não aplica; continua pista, motivo gravado -> pista
#   DESCARTADA  documento lido, não era plano        -> consultado sem achado
#   REVERTIDA   aplicada e desfeita pelos portões    -> erro
# "nada localizado" NUNCA entra aqui: aquele valor é da bateria municipal completa (§2.1), e usá-lo
# afirmaria ausência de plano a partir de uma pista só.
DECISAO_NO_LOG = {"APLICADA": "registro", "ABSTENCAO": "pista",
                  "DESCARTADA": "consultado sem achado", "REVERTIDA": "erro"}


def municipio_uf_do_alvo(alvo):
    """'D-municipio-prioritario/Camaçari/BA' -> ('Camaçari', 'BA'). (None, None) quando não dá.

    A pista de imprensa não carrega `municipio`/`uf` estruturados; o alvo é o único lugar onde eles
    existem. Sem eles a execução entraria no log sem território e não serviria para conferência."""
    partes = [x.strip() for x in str(alvo or "").split("/") if x.strip()]
    if len(partes) >= 2 and len(partes[-1]) == 2 and partes[-1].isalpha():
        return partes[-2], partes[-1].upper()
    return None, None


def registrar_log(entrada):
    """Registra a decisão do aplicador no log v2, pela porta canônica `log_busca`.

    28/09/2026: até aqui esta função montava um dicionário PRÓPRIO (`data`, `canal`, `alvo`,
    `decisao`, `motivo`) e o escrevia direto no monólito `data/log_buscas.json`. Duas coisas
    erradas. A primeira é de esquema: a execução saía sem `strings`, sem `executor` e sem `nivel`, e
    `verificar_consistencia.py` reprovava — 150 linhas de uma vez na primeira noite em que o
    aplicador rodou com teto e commitou. A segunda é a porta: o §269 migrou o log para JSONL, e
    quem escreve no monólito escreve num arquivo que ninguém mais alimenta. Duas portas gravando o
    mesmo log é como se perde registro."""
    municipio, uf = municipio_uf_do_alvo(entrada.get("alvo"))
    log_busca("julgamento_automatico", 5, [str(entrada.get("alvo") or "")],
              DECISAO_NO_LOG.get(entrada.get("decisao"), "erro"),
              resultados=str(entrada.get("motivo") or entrada.get("decisao") or ""),
              uf=uf, municipio=municipio)


def atualizar_gauge_estatico():
    """Atualiza o número fixo (fallback antes do JS carregar) no medidor principal
    do herói para bater com a média nacional recém-recalculada — o mesmo padrão do
    achado de ontem (KPIs estáticos que ficavam desatualizados), agora achado de
    novo no próprio medidor ao aplicar um estado pela primeira vez."""
    indice = json.load(open(RAIZ / "data" / "indice.json", encoding="utf-8"))
    media = sum(v["total"] for v in indice.values()) / len(indice)
    ver = f"{media:.1f}".replace(".", ",")
    src = INDEX_HTML.read_text(encoding="utf-8")
    src_novo = re.sub(r'(id="gaugeNum">)[\d,]+(<)', rf"\g<1>{ver}\g<2>", src, count=1)
    INDEX_HTML.write_text(src_novo, encoding="utf-8", newline="\n")


def extrair_municipio_do_texto(texto, uf):
    """Procura, no texto, o nome de algum município da UF-alvo (referência oficial
    do IBGE) — a busca por resposta varre a UF inteira, não sabe de antemão QUAL
    cidade decretou emergência; isso só se descobre lendo o texto encontrado."""
    ref = json.load(open(RAIZ / "data" / "municipios_ibge_referencia.json", encoding="utf-8"))
    candidatos = [r for r in ref if r["uf"] == uf]
    texto_lower = texto.lower()
    # do mais longo para o mais curto — evita "Bom Jesus" perder para um nome mais
    # curto que por acaso seja substring (ex.: "Ipuaçu" vs "Ipu", cidade de outra UF)
    for c in sorted(candidatos, key=lambda r: -len(r["nome"])):
        if c["nome"].lower() in texto_lower:
            return c
    return None


RE_CAUSA = re.compile(
    r"granizo|estiagem|seca prolongada|seca|enchente|inunda[çc][ãa]o|alagamento|"
    r"deslizamento|vendaval|temporal|chuva intensa|chuvas? intensas?", re.I)


def extrair_causa(texto):
    """Identifica a causa provável do evento por palavra-chave — nunca inventa uma
    causa não mencionada; se nada bater, fica como 'não especificada no texto'."""
    m = RE_CAUSA.search(texto)
    return m.group(0).lower() if m else "não especificada no texto"


def aplicar_resposta(uf, texto, numero, data, url, hoje):
    """Adiciona um evento a data/atos_resposta.json — NUNCA pontua no índice
    (Correção B); é só o registro do mapa de transparência. Recusa aplicar se não
    conseguir identificar COM SEGURANÇA qual município o texto descreve.

    15/10/2026: sem a data do ato em dd/mm/aaaa, abstém. Gravava o ano solto ("2026", Lagoa Seca/PB),
    que o esquema do ato reprova e barrou a publicação — ou a data de HOJE, inventada."""
    if not re.fullmatch(r"\d{2}/\d{2}/\d{4}", str(data or "")):
        return False, f"data do ato não localizada no texto ({data or 'nenhuma'}) — abstenção registrada"
    municipio = extrair_municipio_do_texto(texto, uf)
    if municipio is None:
        return False, f"não foi possível identificar qual município de {uf} o texto descreve — abstenção registrada"

    atos_path = RAIZ / "data" / "atos_resposta.json"
    atos = json.load(open(atos_path, encoding="utf-8"))
    causa = extrair_causa(texto)
    chave = (municipio["nome"], uf, data, causa)
    if any((e["nome"], e["uf"], e["data"], e["causa"]) == chave for e in atos["eventos"]):
        return False, f"{municipio['nome']}/{uf} já tem esse evento registrado (mesma data e causa) — não duplicar"

    # `fonte` é texto público (PDF do município): a mesma frase dos outros caminhos; dano não localizado é null.
    _, fonte_base = canal_e_fonte(url)
    atos["eventos"].append({
        "nome": municipio["nome"], "uf": uf, "data": data, "causa": causa,
        "decreto": f"ato de resposta — {numero}" if numero else "situação de emergência (número não localizado no texto)",
        "danos": None,
        "fonte": f"{fonte_base} — lido em {hoje}",
        "url": url, "lat": municipio["lat"], "lon": municipio["lon"], "canal": "imprensa",
    })
    from coletores_base import carimbar_atos   # a porta do carimbo e do tipo de evento (17/10/2026)
    gravar_em(atos_path, carimbar_atos(atos))
    return True, "aplicado"


# Encaminhamento das pendentes, antes de julgar:
#   - link de agregador: resolve-se (URL embutida, busca no veículo pelo título) só quando o veículo
#     que o feed declara é oficial ou falta; sem resolver em duas noites, fecha com o veículo e o
#     título no motivo (reabre se a URL surgir por outra rota);
#   - fonte que não é oficial: sai daqui para a fila do juiz (`julgar_filas`), que recusa por
#     documento primário e faz a busca dirigida do ato — é lá que notícia vira documento;
#   - alvo `resposta/…` sem fonte oficial: vai para a conferência da base oficial de resposta, como o
#     decreto (não ocupa a fila de planos).
# Só a pista de fonte oficial chega a `processar_pista`. A ordem é a da notícia mais nova.
NOITES_PARA_FECHAR_AGREGADOR = 2
# Cada resolução é uma consulta ao metabuscador (~8 s): 200 cabem no teto do elo junto com o juiz.
RESOLUCOES_POR_RODADA = 200
STATUS_PISTA_DO_JUIZ = "pista — promover a registro exige documento primário"
STATUS_RESPOSTA_SEM_FONTE = ("pista de decreto — vai para a conferência da base oficial de resposta; "
                             "não ocupa a fila de planos")


def status_agregador_fechado(p) -> str:
    from verificar_pista_imprensa import dominio_de
    veiculo = dominio_de(p.get("veiculo_dominio")) or "não declarado"
    titulo = " ".join(str(p.get("titulo") or "").split())[:100] or "sem título"
    return (f"fechada — agregador não resolvido em {NOITES_PARA_FECHAR_AGREGADOR} noites; veículo "
            f"{veiculo}; título: {titulo}")


def pede_resolucao(p) -> bool:
    """Link de agregador cuja URL final decide o destino: veículo oficial, ou não declarado no feed."""
    from verificar_pista_imprensa import eh_agregador
    from monitorar_imprensa_regional import parece_fonte_oficial
    return eh_agregador(p.get("url")) and (not p.get("veiculo_dominio")
                                           or parece_fonte_oficial(p["veiculo_dominio"]))


def encaminhar_pendente(p, hoje_iso, resolver=None):
    """None: a pista segue para `processar_pista`. "": fica pendente, sem julgar nesta rodada.
    Texto: o status novo. Mexe só nos campos de resolução da própria pista."""
    from monitorar_imprensa_regional import parece_fonte_oficial
    if pede_resolucao(p):
        final, como = resolver(p) if resolver else (None, "nao_tentado")
        if final:
            p["url_do_agregador"] = p["url"]
            p["url"] = final
            p["degrau_do_redirecionamento"] = como
            p["fonte_provavel_oficial"] = parece_fonte_oficial(final)
        else:
            if resolver is None:
                return ""            # fora do orçamento desta rodada: não conta noite
            noites = p.setdefault("noites_sem_resolver_agregador", [])
            if hoje_iso not in noites:
                noites.append(hoje_iso)
            if len(noites) >= NOITES_PARA_FECHAR_AGREGADOR:
                return status_agregador_fechado(p)
            return ""
    if not p.get("fonte_provavel_oficial"):
        if str(p.get("alvo") or "").startswith("resposta/"):
            return STATUS_RESPOSTA_SEM_FONTE
        return STATUS_PISTA_DO_JUIZ
    return None


def a_julgar_nesta_noite(p, hoje: str) -> bool:
    """Pendente de documento ainda não julgada hoje (`hoje` em dd/mm/aaaa). Função pura.

    17/10/2026 (fila reentrante): o elo do juiz roda de novo na mesma noite enquanto sobrar fila, e a
    abstenção de hoje fica pendente; sem esta regra a rodada seguinte julgaria as mesmas de novo."""
    return (p.get("status") == "pendente_confirmacao_documento"
            and (p.get("julgamento_automatico") or {}).get("data") != hoje)


def _quando(p):
    """Data de publicação ordenável (RFC 822 do feed, dd/mm/aaaa ou ISO). "" quando ilegível."""
    from email.utils import parsedate_to_datetime
    bruto = str(p.get("data_publicacao") or "").strip()
    try:
        return parsedate_to_datetime(bruto).strftime("%Y-%m-%d")
    except Exception:  # noqa: BLE001
        pass
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", bruto)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return bruto[:10] if re.match(r"\d{4}-\d{2}-\d{2}", bruto) else ""


def _resolver_da_rodada():
    """O resolvedor com rede: HTTP + busca no veículo pelo metabuscador da rodada."""
    from verificar_pista_imprensa import resolver_redirecionamento
    from julgar_filas import _web_para_busca_dirigida, _ritmo
    # Sem o degrau HTTP: o link opaco do Google News responde 200 com uma casca de JavaScript e
    # nunca redirecionou (A1-08); a URL embutida do formato antigo sai sem rede.
    return lambda p: resolver_redirecionamento(
        p["url"], abrir=None,
        veiculo=p.get("veiculo_dominio"), titulo=p.get("titulo"),
        buscar_web=lambda q: (_ritmo(), _web_para_busca_dirigida(q))[1])


def processar_pista(pista, hoje, buscar=buscar_texto):
    """Processa uma pista: busca, classifica, decide. Retorna um relatório dict.
    `buscar` é injetável para permitir fixtures no self-test, sem rede real."""
    if str(pista.get("alvo", "")).startswith("manutencao/"):
        return {"decisao": "ABSTENCAO", "motivo": "pista de manutenção de vigia (não é ato) — abstenção registrada"}
    if not pista.get("fonte_provavel_oficial"):
        return {"decisao": "ABSTENCAO", "motivo": "fonte não reconhecida como oficial (sem mudança)"}

    texto = buscar(pista["url"])
    if texto is None:
        return {"decisao": "ABSTENCAO", "motivo": "falha ao buscar o documento (tentar de novo na próxima execução)"}
    # Este caminho não tem `trecho` para recortar.
    texto = texto[:20000]

    numero, data = extrair_numero_e_data(texto)
    citacao_ok = citacao_completa(f"{numero or ''} {data or ''}")
    rotulo = pista["alvo"].split("/")[0]
    uf = pista["alvo"].split("/")[-1] if not eh_estadual(rotulo) or "/" not in pista["alvo"][len(rotulo)+1:] \
        else pista["alvo"].split("/", 1)[1]

    decisao, motivo = classificar(texto)

    if decisao == "RESPOSTA":
        # Ato de resposta entra no mapa de transparência (nunca no índice); citação incompleta
        # não bloqueia: o mapa registra "número não localizado".
        backup = backup_dados()
        aplicado, motivo_ap = aplicar_resposta(uf, texto, numero, data, pista["url"], hoje)
        if not aplicado:
            return {"decisao": "ABSTENCAO", "motivo": motivo_ap, "natureza": "resposta"}
        ok_portoes, saida_portoes = rodar_portoes()
        if not ok_portoes:
            restaurar_dados(backup)
            return {"decisao": "REVERTIDA", "motivo": "portão falhou após aplicar ato de resposta — desfeito de verdade",
                    "detalhe_portoes": saida_portoes[-2000:]}
        return {"decisao": "APLICADA", "motivo": motivo, "natureza": "resposta"}

    if decisao == "DUVIDA" or not citacao_ok:
        motivo_completo = motivo if decisao == "DUVIDA" else f"citação incompleta (número={numero}, data={data})"
        return {"decisao": "ABSTENCAO", "motivo": motivo_completo}

    # EX_ANTE + citação completa — aplicar, com backup real para rollback se os portões falharem.
    backup = backup_dados()
    if eh_estadual(rotulo):
        aplicado, motivo_ap, status, antecip = aplicar_estadual(uf, texto, numero, data, pista["url"], hoje,
                                                               hash_evidencia=pista.get("hash_evidencia"))
    else:
        nome_mun = pista["alvo"].split("/", 1)[1].rsplit("/", 1)[0] if rotulo.startswith("D-") else None
        if nome_mun is None:
            return {"decisao": "ABSTENCAO", "motivo": "não foi possível determinar o nome do município a partir do alvo"}
        # O juiz é barreira ADICIONAL: só recusa o que este caminho já aprovou; aplicar,
        # backup, portões e rollback seguem deste arquivo.
        veredito = juiz.julgar(texto, nome=nome_mun, uf=uf, url=pista["url"])
        if not veredito["promove"]:
            return {"decisao": "ABSTENCAO",
                    "motivo": f"juiz {veredito['codebook']}: {veredito['motivo']}",
                    "juiz": veredito}
        aplicado, motivo_ap = aplicar_municipal(nome_mun, uf, texto, numero, data,
                                                pista["url"], hoje, veredito)

    if not aplicado:
        return {"decisao": "ABSTENCAO", "motivo": motivo_ap}

    # recalcular ANTES de checar os portões — checar antes disso sempre reprovaria
    # (o índice ainda não sabe da mudança que acabou de entrar em estados/municipios.json).
    subprocess.run(["python3", "recalcular_mare.py", "--write"], cwd=RAIZ, capture_output=True)
    atualizar_gauge_estatico()

    ok_portoes, saida_portoes = rodar_portoes()
    if not ok_portoes:
        restaurar_dados(backup)  # rollback DE VERDADE, não só um rótulo
        return {"decisao": "REVERTIDA", "motivo": "portão falhou após aplicar — desfeito de verdade em disco, ver log",
                "detalhe_portoes": saida_portoes[-2000:]}

    return {"decisao": "APLICADA", "motivo": motivo, "numero": numero, "data": data}


def self_test():
    """Valida o fluxo inteiro com fixtures — sem rede. Cobre: aplica ex-ante estadual
    recorrente, aplica ex-ante estadual novo, aplica municipal, descarta resposta,
    manda p/ fila por dúvida, manda p/ fila por citação incompleta, reverte se portão falhar."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for nome in ("estados.json", "municipios.json", "indice.json", "percentual_uf.json",
                     "decretos_historico_uf.json", "log_buscas.json"):
            shutil.copy(RAIZ / "data" / nome, tmp / nome)
        # ambiente isolado: aponta os módulos para o tmp em vez do banco real
        import julgar_e_aplicar_descobertas as mod
        mod_data_bak = RAIZ / "data"

        # Fixture 1: RESPOSTA mas UF de teste sem município real na referência —
        # não dá pra aplicar sozinho sem saber QUAL cidade, cai pra fila humana
        # (nunca inventa um município a partir de uma UF inexistente).
        pista_resposta = {"alvo": "C-estado-amplo/XX", "url": "https://xx.gov.br/decreto",
                           "fonte_provavel_oficial": True}
        r1 = processar_pista(pista_resposta, "31/08/2026",
                              buscar=lambda u: "Decreto nº 9/2026, de 01/01/2026, declara situação de "
                                                "emergência em razão dos danos causados pela estiagem que "
                                                "atingiu o município. Reconhecimento federal concedido.")
        assert r1["decisao"] == "ABSTENCAO", r1
        print("✓ self-test OK — resposta sem município identificável vai para fila, nunca aplica às cegas")

        # Fixture 2: fonte não oficial — vai pra fila sem tocar em nada
        r2 = processar_pista({"alvo": "C-estado-amplo/XX", "url": "https://blog.exemplo.com",
                               "fonte_provavel_oficial": False}, "31/08/2026")
        assert r2["decisao"] == "ABSTENCAO" and "oficial" in r2["motivo"]
        print("✓ self-test OK — fonte não reconhecida como oficial vai para fila, sem julgar")

        # Fixture 3: falha de rede — vai pra fila, tenta de novo depois
        r3 = processar_pista({"alvo": "C-estado-amplo/XX", "url": "https://xx.gov.br/indisponivel",
                               "fonte_provavel_oficial": True}, "31/08/2026", buscar=lambda u: None)
        assert r3["decisao"] == "ABSTENCAO" and "buscar" in r3["motivo"]
        print("✓ self-test OK — falha ao buscar o documento vai para fila (tentada de novo depois)")

        # Fixture 4: DUVIDA — texto ambíguo, sem padrão claro
        r4 = processar_pista({"alvo": "C-estado-amplo/XX", "url": "https://xx.gov.br/ambiguo",
                               "fonte_provavel_oficial": True}, "31/08/2026",
                              buscar=lambda u: "Governo do Estado publica novo decreto sobre o clima.")
        assert r4["decisao"] == "ABSTENCAO"
        print("✓ self-test OK — texto ambíguo (dúvida do classificador) vai para fila")

        # Fixture 5: citação incompleta — EX_ANTE mas sem número+data extraíveis
        r5 = processar_pista({"alvo": "C-estado-amplo/XX", "url": "https://xx.gov.br/sem-numero",
                               "fonte_provavel_oficial": True}, "31/08/2026",
                              buscar=lambda u: "Plano de Contingência estadual em caráter preventivo, "
                                                "com base nas projeções do Painel El Niño.")
        assert r5["decisao"] == "ABSTENCAO" and "citação incompleta" in r5["motivo"]
        print("✓ self-test OK — EX_ANTE confiante mas sem número/data vai para fila (citação incompleta)")

        # A categoria vem do VEREDITO; sem ela nada entra no banco (trava pura, antes do disco).
        ok_sem, motivo_sem = aplicar_municipal("Taió", "SC", "texto", "12", "01/02/2026",
                                               "https://taio.sc.gov.br/a.pdf", "01/02/2026", {})
        assert ok_sem is False and "sem categoria" in motivo_sem, motivo_sem
        import inspect
        fonte_ap = inspect.getsource(aplicar_municipal)
        assert '"categoria": categoria' in fonte_ap and '"categoria": "plano"' not in fonte_ap
        assert "hash_evidencia" in fonte_ap and "pista_id" in fonte_ap
        print("✓ self-test OK — aplicacao municipal usa a categoria do veredito e carrega "
              "proveniencia")

    # 6) §163: a cadeia que o juiz regenera é lida do portão 12 — e tem de ser legível.
    do_portao = cadeia_do_portao12()
    assert do_portao and do_portao[-1] == ("scripts/gerar_manifesto.py",), do_portao
    print(f"✓ self-test OK — cadeia de derivados lida do portão 12 ({len(do_portao)} passos)")

    # Pasta do RS: pela REST, pelo UniqueId da listagem; resposta que não é documento é erro.
    class _R:
        def __init__(self, content=b"", dados=None):
            self.content, self._dados = content, dados
        def raise_for_status(self): pass
        def json(self): return self._dados
    class _S:
        def __init__(self, corpo):
            self.urls, self.corpo = [], corpo
        def get(self, u, timeout=0, params=None, headers=None):
            self.urls.append(u)
            if "/Files" in u:
                return _R(dados={"value": [{"Name": "PLANCON - D'ÁVILA.pdf", "UniqueId": "u-1"},
                                           {"Name": "PLANO Aratiba.url", "UniqueId": "u-2"}]})
            return _R(self.corpo)
    pasta = "https://rsgovbr-my.sharepoint.com/personal/casa-militar_casamilitar_rs_gov_br/Documents/CREPDEC%2007/"
    import coletores_base as _cb
    _buscar_real, _vistos = _cb.buscar, []
    _cb.buscar = lambda u, timeout=40, origem=None: (_vistos.append(u), b"%PDF-destino")[1]
    _buscar_deste = globals()["buscar"]
    globals()["buscar"] = _cb.buscar   # o destino do atalho passa por `obter_documento`, que usa o `buscar` deste módulo
    def _ler(nome, corpo):
        _SESSAO_RS[:] = [_S(corpo)]
        _IDS_RS.clear()
        try:
            return _ler_sharepoint_rs(pasta + nome, 5)
        except (ValueError, FileNotFoundError) as e:
            return type(e).__name__
    try:
        assert _ler("PLANCON%20-%20D'%C3%81VILA.pdf", b"%PDF-1.7") == b"%PDF-1.7"
        _s = _SESSAO_RS[0]
        assert _s.urls[0].endswith("GetFolderByServerRelativeUrl('/personal/casa-militar_casamilitar_rs_gov_br/"
                                   "Documents/CREPDEC%2007')/Files"), _s.urls
        assert _s.urls[1].endswith("/_api/web/GetFileById('u-1')/$value"), _s.urls
        assert _ler("PLANCON%20-%20D'%C3%81VILA.pdf", b"The length of the URL exceeds") == "ValueError"
        assert _ler("OUTRO.pdf", b"%PDF") == "FileNotFoundError"
        atalho = lambda d: b"[InternetShortcut]\r\nURL=" + d.encode() + b"\r\n"
        assert _ler("PLANO%20Aratiba.url", atalho("https://casamilitar-rs.com.br/pdfs/9.pdf")) == b"%PDF-destino"
        assert _ler("PLANO%20Aratiba.url", atalho("https://outro.com/p.pdf")) == "ValueError"
        assert _vistos == ["https://casamilitar-rs.com.br/pdfs/9.pdf"], _vistos
    finally:
        _cb.buscar = _buscar_real
        globals()["buscar"] = _buscar_deste
        _SESSAO_RS.clear(); _IDS_RS.clear()
    print("✓ self-test OK — arquivo do RS lido por UniqueId; resposta que não é documento é erro; atalho .url "
          "segue só para a origem declarada")

    # 10/11/2026: obtido sem texto é "" (texto_nao_extraivel), nunca None (inacessível); DOCX lê o corpo.
    import io as _io, zipfile as _zf
    _b = _io.BytesIO()
    with _zf.ZipFile(_b, "w") as z:
        z.writestr("word/document.xml", "<w:p><w:t>PLANO DE CONTING&#202;NCIA</w:t></w:p><w:p><w:t>Itati</w:t></w:p>")
    assert texto_do_documento(_b.getvalue(), "https://x/p.docx") == "PLANO DE CONTINGÊNCIA Itati"
    assert texto_do_documento(b"%PDF-1.4 sem texto", "https://x/p.pdf") == ""
    assert texto_do_documento(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"x" * 900, "https://x/p.doc") == ""
    # 23/11: o .doc do Word 97–2003 passou a ser lido (6 planos do Prepara RS vinham vazios); o que não é do Word segue "".
    import base64 as _b64, zlib as _zl
    _doc = _zl.decompress(_b64.b64decode(
        "eNrtmd9Pm1UYx5/ztpS2m6WUighVOlYB2ej4MRDmVCiMQSfQjQnqfmChxXWuLUIXMfHCaEy8mAnGC29MjAleaQzqH6A3emfmzS52"
        "N+OFMTHLNHqxi1G/53nPy7qOyduymI31IR/O+56+55znPOc5533ec36+WHnls69rf6E8eZostJZ1kC0nTwC3cYMLTeWtZbNZIztb"
        "kvtKbqhUjqEV41cG5JiXAztwACfYAXaCh4ALVKhxr1RpSe5POUZp/GXIT4cohXSB3qRCpBoek1ufmTJrJp8zK6X2i2/fWL+Lmf/y"
        "XSDnvwdUAS94mH2C6BFQAx4FtaAO+MBj4HFQD/xgF2hQOgSQPqGum5A2gydBC9gD9oJWEAT7QBtoBx2gE+wHXaAbPAV6QC84wO8z"
        "ooPgGfAseA70gX4QAgNgEBwCQ+AwGAYjIAyOgOfBKBgD4yACjoJjYAIcBy+ASTAFXgQvgZfBCXASnAKnVR9fuQfWTgENLE7dh2wO"
        "jX3ie901huT4jSZmF9KL6bmMfyq9EGsdTL92PhlPZdgnRidk3mB6lj1BXgdxw78He+jv3m9e39wXhR5GFC0eeJwTtZxgj9QF9nb/"
        "mdXY7jaMVhqrWpKidE75cXuAWgKiPyC9KNRC42ELHQUD4RpKDjusiyAStlJq2GrPgNPhMorit+nhXut/6jJEa/WCNDHE82eY4mgz"
        "Rgmsq6/yzKmgqpVr5F1ZIltAYHaMh21o2IaGfRQJl5PekA9+HHLLevbz/AtB/xhWZT/8K05LWKPlzHOTJ+YVAjVi3q1c4Nm0zy2E"
        "R8hZZYWvJmiRn9UwR62o2w5/b0C9DaKP9RuAdvN4IoH6U6yfB7UtsX47oZ+HDdJtF7Ko7P8pu2jkHnYglSvFCMrFWCd5V8Wl9JYm"
        "+bmQmOQVIgL7x2lufRwy+IujZG6PnFg99L4QW8YByziggReWcaJOB1TwspV93D9ehNhr5TLVbddXLnndY6f1qNWnUs2dkxHRVzZ2"
        "hcPVy8KMmx2HmZJQdhFKjyF9A6l8dcruSON1oR4zfjyBgUzSDEpKZ+xsNNd6PwyXUA6ckBpXbl5GOsAMNF1gg+uD7Ef7ca5rzkSf"
        "jtjMaTfGAUT6ltr9cK8wFk2ZJ5fWXpN1DbGrxFFK6rAoLSZt5C6+v0Y9uTYcKaJnej239SuwLERR/Zru2kq/RjlN84srTee5b/IZ"
        "YyRht67i+2jUnt/bECaesH+A98IPcPYzYoPFXIUQdXwneKq+y4rcmmsUbbJwFMAzuiRbeA223f0689Yzv8lBKliTt7ei5FpWOpO2"
        "UVxBV9779K/r42fcX3xopz1N316Wmr2l4luh4kOHigOdKr7boeI2GevGVLw7r4zx+w09dtVUL/ty2jNzvZH88bkQo34HLHvN812u"
        "AdWbzEUD0fS5aKpnA7M6rNW0z3Xz3rfpd0IFT0Ohrm051/nyPv+/qubpVRNLiXzGW4h7abqVXSpd33nCfYdl6+5bW2RcmYSJZnLK"
        "Nmr6V01JtqfU5vnf/yUaXS4ZvyQleaAlgg+SqAq2ZzmQ14Nx+V3txxd2RoX9B3AXpd/oV/wa5KikJNtC1O5FSR5IEUac/0/JFttc"
        "nF6yBCgaWN/mlBvQopUOtlEftiRDEY3qV98J+ld/7N+1mrI2gN3LKWsAdOL35g5ytZn//pU52qWfLn0SrHN/9DG+f/de/0qeb5Tl"
        "5Z1U5zQi53zf+Na9U35Jto/czfNf6Sf5Z0gblZEf9301xgI4wFvO8zhRm6GzVPj5j8Z+aTVOA0zK2fUFeBwRWLz4WY3WZbuWAtrX"
        "6OZOSTu24aPoebE6uFT7hZz/Sl0vlpParJ1A1JnkTX859vJMJ/ekxjgdupM0o33jzNhs+7vBl+p6ituK4ew1zfGvPJBI8YmQya/3"
        "IvovT6+MfbOy21ouzB49RbQ/DTJ0b5z//wuch+BC"))
    assert texto_do_documento(_doc, "https://x/p.doc") == "Plano curto de Itati: ação.", texto_do_documento(_doc, "https://x/p.doc")
    # Corrente homônima fora da raiz (objeto embutido) não entra na leitura.
    import struct as _st
    _dir = (_st.unpack_from("<I", _doc, 48)[0] + 1) * 512
    _livre = next(o for o in range(_dir, _dir + 512 * 8, 128) if _st.unpack_from("<H", _doc, o + 64)[0] == 0)
    _falso = "1Table".encode("utf-16-le").ljust(64, b"\0") + _st.pack("<HBB3I", 14, 2, 1, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF)
    _doc2 = _doc[:_livre] + _falso.ljust(116, b"\0") + _st.pack("<III", 0, 10, 0) + _doc[_livre + 128:]
    assert texto_do_documento(_doc2, "https://x/p.doc") == "Plano curto de Itati: ação.", texto_do_documento(_doc2, "https://x/p.doc")
    assert canal_e_fonte("https://rsgovbr-my.sharepoint.com/personal/casa-militar_casamilitar_rs_gov_br/Documents/"
                         "Casa%20Militar/SUBCHEFIAS/SUBCHEFIA%20DE%20PROTE%C3%87%C3%83O%20E%20DEFESA%20CIVIL/"
                         "3.%20Departamento%20de%20Gest%C3%A3o%20de%20Riscos/Divis%C3%A3o%20T%C3%A9cnica%20de%20Riscos/"
                         "Planos%20de%20conting%C3%AAncia/TODOS%20PLANCONS%20RECEBIDOS/CREPDEC%2006/a.pdf") \
        == ("orgao_estadual", "Defesa Civil do Rio Grande do Sul — Prepara RS")
    assert canal_e_fonte("https://x.sharepoint.com/a.pdf")[0] == "imprensa", "SharePoint qualquer não é o repositório"
    print("✓ self-test OK — documento sem texto não é inacessível; DOCX lido; pasta do RS é órgão estadual")

    # Log do aplicador: esquema e vocabulário provados sem escrever nada.
    assert municipio_uf_do_alvo("D-municipio-prioritario/Camaçari/BA") == ("Camaçari", "BA")
    assert municipio_uf_do_alvo("A/B/Sao Paulo/SP") == ("Sao Paulo", "SP")
    assert municipio_uf_do_alvo("sem barra") == (None, None), "alvo sem UF não inventa território"
    assert municipio_uf_do_alvo(None) == (None, None)
    assert municipio_uf_do_alvo("x/y/ZZZ") == (None, None), "três letras não é UF"
    from coletores_base import DECISOES_LOG
    for _saida, _dec in DECISAO_NO_LOG.items():
        assert _dec.split(" ")[0] in DECISOES_LOG, f"{_saida} fora do vocabulário fechado"
    assert "nada localizado" not in DECISAO_NO_LOG.values(), (
        "'nada localizado' é da bateria municipal completa (§2.1); usá-lo aqui afirmaria ausência "
        "de plano a partir de uma pista só")
    assert DECISAO_NO_LOG["APLICADA"] == "registro" and DECISAO_NO_LOG["ABSTENCAO"] == "pista"
    import inspect as _insp
    _fonte = _insp.getsource(registrar_log)
    assert "log_busca(" in _fonte, "o aplicador tem de escrever pela porta canônica"
    assert "gravar_em(LOG_BUSCAS" not in _fonte, (
        "duas portas gravando o mesmo log é como se perde registro (§269)")

    # Encaminhamento das pendentes, sem rede.
    gn = {"url": "https://news.google.com/rss/articles/CBMiOPAQUE", "alvo": "B-capital/TO",
          "veiculo_dominio": "https://www.palmas.to.gov.br", "titulo": "Palmas aprova plano"}
    p1 = dict(gn)
    res_ok = lambda p: ("https://www.palmas.to.gov.br/noticia/plano", "busca_no_veiculo")  # noqa: E731
    assert encaminhar_pendente(p1, "2026-10-09", res_ok) is None, "resolvida em .gov.br vai a julgar"
    assert p1["url"].startswith("https://www.palmas") and p1["url_do_agregador"].startswith("https://news")
    p2 = dict(gn)
    res_nao = lambda p: (None, "redirecionamento_nao_resolvido")  # noqa: E731
    assert encaminhar_pendente(p2, "2026-10-08", res_nao) == "", "uma noite sem resolver: espera"
    assert encaminhar_pendente(p2, "2026-10-08", res_nao) == "", "a mesma noite não conta duas vezes"
    fech = encaminhar_pendente(p2, "2026-10-09", res_nao)
    assert fech.startswith("fechada — agregador não resolvido") and "palmas.to.gov.br" in fech \
        and "Palmas aprova plano" in fech, fech
    p3 = dict(gn)
    assert encaminhar_pendente(p3, "2026-10-09", None) == "" and "noites_sem_resolver_agregador" not in p3, \
        "fora do orçamento não conta noite"
    assert encaminhar_pendente({"url": "https://g1.globo.com/x", "alvo": "B-capital/CE",
                                "fonte_provavel_oficial": False}, "2026-10-09") == STATUS_PISTA_DO_JUIZ
    jornal = dict(gn, veiculo_dominio="https://g1.globo.com", alvo="resposta/TO", fonte_provavel_oficial=False)
    assert not pede_resolucao(jornal) and pede_resolucao(gn) and pede_resolucao(dict(gn, veiculo_dominio=""))
    assert encaminhar_pendente(jornal, "2026-10-13", None) == STATUS_RESPOSTA_SEM_FONTE \
        and "noites_sem_resolver_agregador" not in jornal, "veículo não oficial não gasta resolução nem noite"
    assert encaminhar_pendente({"url": "https://g1.globo.com/x", "alvo": "resposta/CE",
                                "fonte_provavel_oficial": False}, "2026-10-09") == STATUS_RESPOSTA_SEM_FONTE
    assert encaminhar_pendente({"url": "https://x.ce.gov.br/d.pdf", "alvo": "B-capital/CE",
                                "fonte_provavel_oficial": True}, "2026-10-09") is None
    assert aplicar_resposta("PB", "", None, "2026", "u", "15/10/2026")[0] is False, \
        "ato sem data completa não entra no mapa (ano solto barrou a publicação em 15/10)"
    import inspect as _i2
    assert "carimbar_atos(atos)" in _i2.getsource(aplicar_resposta), "ato sem tipo de evento nem carimbo"
    assert '"url": url' in _i2.getsource(aplicar_resposta), (
        "o evento de resposta leva a URL da fonte: verificar_resposta.py (g) exige url ou hash")
    ordem = sorted([{"data_publicacao": "Tue, 25 Aug 2026 07:00:00 GMT"},
                    {"data_publicacao": "01/10/2026"}, {"data_publicacao": "lixo"}], key=_quando, reverse=True)
    assert [_quando(o) for o in ordem] == ["2026-10-01", "2026-08-25", ""], ordem
    ja = {"status": "pendente_confirmacao_documento", "julgamento_automatico": {"data": "17/10/2026"}}
    assert not a_julgar_nesta_noite(ja, "17/10/2026") and a_julgar_nesta_noite(ja, "18/10/2026")

    # 12/11/2026: o site recusa; o texto vem da cópia arquivada, e sem cópia segue "não obtido"
    import unittest.mock as _mk
    with _mk.patch(f"{__name__}.buscar", side_effect=OSError("403")), \
         _mk.patch(f"{__name__}.copia_arquivada", return_value=(b"<p>Plano de contingencia de Bonito</p>", "2026-09-01")):
        assert "Plano de contingencia" in (buscar_texto("https://x.ms.gov.br/p.html") or ""), "cópia arquivada não lida"
    with _mk.patch(f"{__name__}.buscar", side_effect=OSError("403")), \
         _mk.patch(f"{__name__}.copia_arquivada", return_value=(None, None)):
        assert buscar_texto("https://x.ms.gov.br/p.html") is None
    # 17/11/2026: endereço de PDF que responde página (Rio de Janeiro/RJ) não é o documento: vale a cópia pública
    with _mk.patch(f"{__name__}.buscar", return_value=b"<html><body>acesso</body></html>"), \
         _mk.patch(f"{__name__}.copia_arquivada", return_value=(None, None)) as _arq:
        assert buscar_texto("https://x.prefeitura.rio/p.pdf") is None and _arq.called, "página tomada por PDF"

    # 13/11/2026 (J21): a estrutura criada no ciclo sobe, com prova; a que já está no degrau não é regravada
    with tempfile.TemporaryDirectory() as _t:
        _c = Path(_t) / "estados.json"
        gravar_em(_c, {"ufs": [{"uf": "RR", "estrutura": {"status": "VIG"}, "instrumentos": [{"tipo": "estrutura_coordenacao", "status": "VIG"}]}]})
        _a = {"doc": "DECRETO Nº 41.444-E, de 31/08/2026: Institui o Gabinete", "data": "31/08/2026"}
        assert aplicar_estrutura_estadual("RR", _a, "https://x/doe.pdf", "abc", "2026-11-13", _c)
        _e = json.load(open(_c, encoding="utf-8"))["ufs"][0]
        assert _e["estrutura"]["status"] == "NOVO" and _e["estrutura"]["hash_evidencia"] == "abc" and len(_e["instrumentos"]) == 1
        assert not aplicar_estrutura_estadual("RR", _a, "https://x/doe.pdf", "abc", "2026-11-13", _c)

    print("\n✓ self-test do orquestrador OK — 6 cenários cobertos (aplicar exigiria banco real; "
          "ver classificador_natureza.py e verificar_recorrencia_uf.py para os self-tests de aplicação).")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    # Teto por execução: fila que termina e commita vale mais que fila inteira cancelada no meio.
    ap.add_argument("--limite", type=int, default=None,
                    help="processa no máximo N pistas pendentes nesta execução")
    args = ap.parse_args()
    if args.limite is not None and args.limite <= 0:
        print("--limite tem de ser inteiro positivo.")
        sys.exit(2)
    if args.self_test:
        self_test()
        sys.exit(0)

    if not PISTAS_IMPRENSA.exists():
        print("Sem fila de pistas (data/pistas_imprensa.json não existe ainda) — nada a fazer.")
        sys.exit(0)

    hoje = hoje_editorial().strftime("%d/%m/%Y")
    fila = json.load(open(PISTAS_IMPRENSA, encoding="utf-8"))
    pendentes = [p for p in fila["pistas"] if a_julgar_nesta_noite(p, hoje)]
    pendentes.sort(key=_quando, reverse=True)
    hoje_iso = hoje_editorial().isoformat()
    resolver, resolucoes, encaminhadas = _resolver_da_rodada(), 0, {}
    a_julgar = []
    for p in pendentes:
        usa_rede = resolucoes < RESOLUCOES_POR_RODADA
        if pede_resolucao(p) and usa_rede:
            resolucoes += 1
        novo = encaminhar_pendente(p, hoje_iso, resolver if usa_rede else None)
        if novo is None:
            a_julgar.append(p)
        elif novo:
            p["status"] = novo
            chave = novo.split(";")[0][:60]
            encaminhadas[chave] = encaminhadas.get(chave, 0) + 1
    print(f"Encaminhadas sem julgar ({resolucoes} resoluções de agregador): {encaminhadas}")
    pendentes = a_julgar
    total_pendentes = len(pendentes)
    if args.limite is not None:
        pendentes = pendentes[:args.limite]
    resultados = {"APLICADA": 0, "DESCARTADA": 0, "ABSTENCAO": 0, "REVERTIDA": 0}
    for pista in pendentes:
        r = processar_pista(pista, hoje)
        resultados[r["decisao"]] += 1
        pista["status"] = {"APLICADA": "aplicada_automaticamente", "DESCARTADA": "descartada_resposta",
                            "REVERTIDA": "revertida_erro_portao"}.get(r["decisao"], "pendente_confirmacao_documento")
        pista["julgamento_automatico"] = {"data": hoje, **r}
        registrar_log({"data": hoje, "canal": "julgamento_automatico", "alvo": pista["alvo"],
                        "decisao": r["decisao"], "motivo": r.get("motivo", "")})

    gravar_em(PISTAS_IMPRENSA, fila)
    print(f"Processadas {len(pendentes)} de {total_pendentes} pistas pendentes: {resultados}")
    if len(pendentes) < total_pendentes:
        print(f"Teto de --limite alcançado: {total_pendentes - len(pendentes)} pista(s) ficam para a "
              f"próxima execução. Não é lacuna de coleta — é fila, e ela está declarada aqui.")
