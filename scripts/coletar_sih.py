#!/usr/bin/env python3
"""Internações do SUS (SIH/SUS, AIH reduzida `RD<UF><AAMM>.dbc`) — leitor e sondagem (janela E2).

O QUE ESTE ARQUIVO É HOJE (17/10/2026)
--------------------------------------
A segunda camada dos desfechos de saúde (HANDOVER_SUS_DESFECHOS §1, camada C) depende de ler o
`.dbc` do FTP do DATASUS: DBF comprimido pelo "implode" da PKWare (DCL). Este arquivo traz:

- `explodir`: o descompressor DCL, porte em Python do `blast.c` de Mark Adler (zlib/contrib, licença
  zlib). Nenhuma dependência nova: o leitor da Fiocruz (`pyreaddbc`) é AGPL, e licença é decisão da
  editoria; o `datasus-dbc` (MIT) só existe como fonte em Rust, que o executor teria de compilar.
- `ler_dbc` / `registros_dbf`: o DBF em fluxo, só com as colunas pedidas (o RD tem 113 colunas e o
  coletor precisa de quatro ou cinco).
- `--sondar`: mede e imprime, sem escrever série nem banco (o único rastro em `data/` é o da porta
  comum de rede, `robots_registro.json`, quando o robots pede que robôs não entrem): a lista do FTP (último mês publicado por UF,
  com a data do arquivo), um arquivo decodificado (colunas, registros, tempo) e a mesma célula no
  TabNet (internações do mês na UF), para bater o leitor contra a tabulação oficial.

O coletor (série por UF e mês por grupo de CID) só escreve quando a estrutura comum de arquivo da
janela E1 estiver na `main`: é ela que dá a série, a faixa habitual e os cortes do mapa. Até lá,
nada vai a `data/`.

TRAVAS
------
1. Estrutural: nunca escreve em `estados.json`, `saude_uf.json`, `municipios.json`, `indice.json`,
   `monitor_saude.json` (o autoteste lê o próprio fonte).
2. De campo: não produz pista nem registro promovível; o que sai é série agregada de peso zero.
3. De processo: a sondagem só imprime; a escrita, quando existir, é de arquivo próprio em
   `data/saude_desfechos/` com escritor único em `config/escritores.json`.

USO
  python3 scripts/coletar_sih.py --autoteste
  python3 scripts/coletar_sih.py --sondar [--uf AC] [--aamm 2607]
"""
from __future__ import annotations

import ftplib
import io
import pathlib
import re
import sys
import time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

FTP_HOST = "ftp.datasus.gov.br"
FTP_SIH = "/dissemin/publicos/SIHSUS/200801_/Dados"
TABNET = "http://tabnet.datasus.gov.br/cgi"
BANCO_PROIBIDO = ("estados.json", "saude_uf.json", "municipios.json", "indice.json",
                  "monitor_saude.json")
PAUSA = 2  # segundos entre pedidos ao mesmo servidor (§11); o Crawl-delay, quando houver, é da porta comum
UFS = ("AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO").split()

# ---------------------------------------------------------------------------------------------
# Descompressor DCL ("blast"). Tabelas e passos idênticos aos do blast.c (zlib/contrib/blast).
# ---------------------------------------------------------------------------------------------
_LITLEN = bytes((11, 124, 8, 7, 28, 7, 188, 13, 76, 4, 10, 8, 12, 10, 12, 10, 8, 23, 8, 9, 7, 6,
                 7, 8, 7, 6, 55, 8, 23, 24, 12, 11, 7, 9, 11, 12, 6, 7, 22, 5, 7, 24, 6, 11, 9, 6,
                 7, 22, 7, 11, 38, 7, 9, 8, 25, 11, 8, 11, 9, 12, 8, 12, 5, 38, 5, 38, 5, 11, 7, 5,
                 6, 21, 6, 10, 53, 8, 7, 24, 10, 27, 44, 253, 253, 253, 252, 252, 252, 13, 12, 45,
                 12, 45, 12, 61, 12, 45, 44, 173))
_LENLEN = bytes((2, 35, 36, 53, 38, 23))
_DISTLEN = bytes((2, 20, 53, 230, 247, 151, 248))
_BASE = (3, 2, 4, 5, 6, 7, 8, 9, 10, 12, 16, 24, 40, 72, 136, 264)
_EXTRA = (0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8)


def _tabela(rep: bytes):
    """Tabela de consulta direta de um código de Huffman do DCL. Os comprimentos vêm em
    corrida compacta (nibble alto = repetições − 1, nibble baixo = comprimento); o código é
    canônico e lido bit a bit INVERTIDO, do bit mais significativo para o menos (blast.c,
    `decode`). A tabela indexa os próximos `k` bits como saem do fluxo (LSB primeiro)."""
    comp = []
    for b in rep:
        comp.extend([b & 15] * ((b >> 4) + 1))
    k = max(comp)
    ordem = sorted(range(len(comp)), key=lambda s: (comp[s], s))
    tab = [None] * (1 << k)
    codigo, ultimo = 0, 0
    for s in ordem:
        L = comp[s]
        if not L:
            continue
        codigo <<= (L - ultimo)
        ultimo = L
        padrao = 0
        for i in range(L):  # i-ésimo bit lido = complemento do bit (L-1-i) do código canônico
            padrao |= (1 - ((codigo >> (L - 1 - i)) & 1)) << i
        for ext in range(1 << (k - L)):
            tab[padrao | (ext << L)] = (s, L)
        codigo += 1
    return tab, k


_LIT, _LIT_K = _tabela(_LITLEN)
_LEN, _LEN_K = _tabela(_LENLEN)
_DIST, _DIST_K = _tabela(_DISTLEN)


def explodir(dado: bytes) -> bytes:
    """Descomprime um fluxo PKWare DCL implode. Levanta ValueError em fluxo inválido."""
    n = len(dado)
    pos = 0
    buf = 0
    cnt = 0
    pad = 0
    out = bytearray()

    def encher(precisa):
        nonlocal buf, cnt, pos, pad
        while cnt < precisa:
            if pos < n:
                tira = dado[pos:pos + 8]
                buf |= int.from_bytes(tira, "little") << cnt
                cnt += 8 * len(tira)
                pos += len(tira)
            else:  # fim do fluxo: zeros; só um fluxo sem código de fim chega a consumi-los
                cnt += 64
                pad += 64
                if pad > 4096:
                    raise ValueError("fluxo DCL sem código de fim")

    encher(16)
    lit = buf & 0xFF
    dic = (buf >> 8) & 0xFF
    buf >>= 16
    cnt -= 16
    if lit > 1:
        raise ValueError("cabeçalho DCL: modo de literal inválido")
    if dic < 4 or dic > 6:
        raise ValueError("cabeçalho DCL: dicionário inválido")
    while True:
        if cnt < 40:
            encher(40)
        bit = buf & 1
        buf >>= 1
        cnt -= 1
        if bit:
            s, L = _LEN[buf & ((1 << _LEN_K) - 1)]
            buf >>= L
            cnt -= L
            e = _EXTRA[s]
            comp = _BASE[s] + (buf & ((1 << e) - 1))
            buf >>= e
            cnt -= e
            if comp == 519:
                return bytes(out)
            sb = 2 if comp == 2 else dic
            s, L = _DIST[buf & ((1 << _DIST_K) - 1)]
            buf >>= L
            cnt -= L
            dist = (s << sb) + (buf & ((1 << sb) - 1)) + 1
            buf >>= sb
            cnt -= sb
            ini = len(out) - dist
            if ini < 0:
                raise ValueError("fluxo DCL: distância antes do início")
            if dist >= comp:
                out += out[ini:ini + comp]
            else:
                pedaco = out[ini:]
                out += (pedaco * (comp // dist + 1))[:comp]
        else:
            if lit:
                s, L = _LIT[buf & ((1 << _LIT_K) - 1)]
                buf >>= L
                cnt -= L
                out.append(s)
            else:
                out.append(buf & 0xFF)
                buf >>= 8
                cnt -= 8


def dbc_para_dbf(bruto: bytes) -> bytes:
    """`.dbc` do DATASUS = cabeçalho DBF sem compressão + 4 bytes de verificação + DCL do resto."""
    if len(bruto) < 12:
        raise ValueError("dbc curto demais")
    hsize = int.from_bytes(bruto[8:10], "little")
    if hsize < 33 or hsize + 4 > len(bruto):
        raise ValueError("dbc: tamanho de cabeçalho inválido")
    return bruto[:hsize] + explodir(bruto[hsize + 4:])


def campos_dbf(dbf: bytes) -> list:
    """[(nome, tipo, deslocamento_no_registro, comprimento)]; o deslocamento conta o byte de
    exclusão que abre cada registro."""
    out, desl, i = [], 1, 32
    hsize = int.from_bytes(dbf[8:10], "little")
    while i + 32 <= hsize and dbf[i] != 0x0D:
        nome = dbf[i:i + 11].split(b"\0", 1)[0].decode("latin-1").strip()
        out.append((nome, chr(dbf[i + 11]), desl, dbf[i + 16]))
        desl += dbf[i + 16]
        i += 32
    return out


def registros_dbf(dbf: bytes, colunas=None):
    """Gera dicionários {coluna: texto} por registro não excluído, só com as colunas pedidas."""
    nreg = int.from_bytes(dbf[4:8], "little")
    hsize = int.from_bytes(dbf[8:10], "little")
    rlen = int.from_bytes(dbf[10:12], "little")
    campos = campos_dbf(dbf)
    if colunas is not None:
        faltam = set(colunas) - {c[0] for c in campos}
        if faltam:
            raise ValueError(f"dbf sem as colunas {sorted(faltam)}")
        campos = [c for c in campos if c[0] in set(colunas)]
    for r in range(nreg):
        ini = hsize + r * rlen
        reg = dbf[ini:ini + rlen]
        if len(reg) < rlen:
            break
        if reg[0:1] == b"*":
            continue
        yield {n: reg[d:d + c].decode("latin-1").strip() for n, _t, d, c in campos}


def ler_dbc(bruto: bytes, colunas=None):
    return registros_dbf(dbc_para_dbf(bruto), colunas)


# ---------------------------------------------------------------------------------------------
# Rede (só na sondagem e no coletor; o autoteste não chega aqui)
# ---------------------------------------------------------------------------------------------
def _ftp():
    from coletores_base import UA
    time.sleep(PAUSA)
    f = ftplib.FTP(FTP_HOST, timeout=60)
    # FTP anônimo não tem User-Agent: a identificação vai na senha anônima, como manda o costume.
    f.login("anonymous", re.sub(r"[^\x20-\x7e]", "", UA)[:120])
    return f


def listar_ftp(diretorio: str) -> list:
    """[(nome, tamanho, data 'AAAAMMDD')] do diretório."""
    f = _ftp()
    try:
        f.cwd(diretorio)
        try:
            itens = [(n, int(fa.get("size", 0) or 0), (fa.get("modify") or "")[:8])
                     for n, fa in f.mlsd(facts=["size", "modify"]) if fa.get("type") == "file"]
        except ftplib.error_perm:
            linhas = []
            f.retrlines("LIST", linhas.append)
            itens = []
            for ln in linhas:  # formato MS-DOS do servidor: 'MM-DD-YY  HH:MMAM  tamanho nome'
                m = re.match(r"(\d\d)-(\d\d)-(\d\d)\s+\S+\s+(\d+)\s+(\S+)$", ln.strip())
                if m:
                    itens.append((m.group(5), int(m.group(4)), f"20{m.group(3)}{m.group(1)}{m.group(2)}"))
        return itens
    finally:
        try:
            f.quit()
        except Exception:  # noqa: BLE001
            pass


def baixar_ftp(caminho: str) -> bytes:
    f = _ftp()
    try:
        b = io.BytesIO()
        f.retrbinary(f"RETR {caminho}", b.write)
        return b.getvalue()
    finally:
        try:
            f.quit()
        except Exception:  # noqa: BLE001
            pass


def ultimo_por_uf(itens: list, prefixo: str = "RD") -> dict:
    """{UF: (AAMM, tamanho, data_do_arquivo)} do arquivo mais novo de cada UF. Função pura."""
    out = {}
    for nome, tam, data in itens:
        m = re.fullmatch(prefixo + r"([A-Z]{2})(\d{4})\.DBC", nome.upper())
        if not m or m.group(1) not in UFS:
            continue
        uf, aamm = m.group(1), m.group(2)
        if uf not in out or aamm > out[uf][0]:
            out[uf] = (aamm, tam, data)
    return out


def contar_internacoes(registros) -> dict:
    """{'total': n, 'ident': {IDENT: n}, 'cap_J': n, 'competencias': {AAAAMM: n}}. Função pura."""
    total, ident, capj, comp = 0, {}, 0, {}
    for r in registros:
        total += 1
        ident[r.get("IDENT", "")] = ident.get(r.get("IDENT", ""), 0) + 1
        if r.get("DIAG_PRINC", "").startswith("J"):
            capj += 1
        k = r.get("ANO_CMPT", "") + r.get("MES_CMPT", "")
        comp[k] = comp.get(k, 0) + 1
    return {"total": total, "ident": ident, "cap_J": capj, "competencias": comp}


def _tabnet_celula(uf: str, aamm: str, recorte: str = "ni") -> str:
    """Pede ao TabNet a tabela 'internações por ano/mês de competência' da UF, só o arquivo do
    mês. O formulário é lido da própria página (nomes de campo e opções), nunca adivinhado."""
    import urllib.parse
    from coletores_base import buscar_uma_vez, detectar_muro_de_robo, ua_de
    import urllib.request
    # "ni" = por local de internação (o mesmo recorte do RD, que é o arquivo do hospital da UF);
    # "nr" = por local de residência.
    defn = f"sih/cnv/{recorte}{uf.lower()}.def"
    form = buscar_uma_vez(f"{TABNET}/deftohtm.exe?{defn}", timeout=60).decode("latin-1", "replace")
    campos, visto = [], {}
    for nome, corpo in re.findall(r'<select[^>]*name="?([^"\s>]+)"?[^>]*>(.*?)</select>', form, re.S | re.I):
        opcoes = re.findall(r'<option[^>]*value="([^"]*)"[^>]*>([^<]*)', corpo, re.I)
        sel = [v for v, _ in re.findall(r'<option[^>]*selected[^>]*value="([^"]*)"()', corpo, re.I)]
        rot = {v: t.strip() for v, t in opcoes}
        visto[nome] = list(rot.values())
        if nome == "Linha":
            esc = [v for v, t in rot.items() if "compet" in t.lower() or t.lower().startswith("ano")][:1]
        elif nome == "Coluna":
            esc = [v for v, t in rot.items() if "ativa" in t.lower()][:1]
        elif nome == "Incremento":
            esc = [v for v, t in rot.items() if t.lower().startswith("interna")][:1]
        elif nome == "Arquivos":
            esc = [v for v in rot if aamm in v][:1] or list(rot)[:1]  # TabNet pode estar atrás do FTP
        else:
            esc = sel or [v for v in rot if "TODAS" in v.upper()][:1]
        campos += [(nome, v) for v in esc]
    campos += [(n, v) for n, v in re.findall(r'<input[^>]*type="?hidden"?[^>]*name="([^"]+)"[^>]*value="([^"]*)"', form, re.I)]
    campos += [("formato", "table"), ("mostre", "Mostra")]
    corpo = urllib.parse.urlencode(campos, encoding="latin-1").encode()
    req = urllib.request.Request(f"{TABNET}/tabcgi.exe?{defn}", data=corpo,
                                 headers={"User-Agent": ua_de("sondagem SIH"),
                                          "Content-Type": "application/x-www-form-urlencoded"})
    time.sleep(PAUSA)
    with urllib.request.urlopen(req, timeout=90) as r:
        bruto = r.read()
    muro = detectar_muro_de_robo(bruto)
    if muro:  # recusa servida com 200 é recusa: não se lê como tabela
        raise RuntimeError(f"TabNet: muro de robô ({muro})")
    html = bruto.decode("latin-1", "replace")
    texto = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style).*?</\1>", "", html)))
    arq = visto.get("Arquivos", [])
    return (f"{defn} campos={campos}; "
            f"Linha={visto.get('Linha', [])[:12]}; Arquivos={arq[:2]}…{arq[-1:]} ({len(arq)}); "
            f"resposta {len(bruto)} bytes: {texto[:900]}")


def sondar(uf: str = "AC", aamm: str | None = None) -> int:
    print(f"[sih] FTP {FTP_HOST}{FTP_SIH}")
    t = time.time()
    itens = listar_ftp(FTP_SIH)
    ult = ultimo_por_uf(itens)
    print(f"[sih] {len(itens)} arquivos listados em {time.time() - t:.1f}s; RD por UF (último AAMM, bytes, data do arquivo):")
    for u in UFS:
        print(f"[sih]   {u} {ult.get(u)}")
    if uf not in ult:
        print(f"[sih] {uf}: nenhum RD listado")
        return 0
    aamm = aamm or ult[uf][0]
    nome = f"RD{uf}{aamm}.dbc"
    t = time.time()
    bruto = baixar_ftp(f"{FTP_SIH}/{nome}")
    t_baixa = time.time() - t
    t = time.time()
    dbf = dbc_para_dbf(bruto)
    t_dec = time.time() - t
    campos = campos_dbf(dbf)
    print(f"[sih] {nome}: {len(bruto)} bytes, baixado em {t_baixa:.1f}s; DBF {len(dbf)} bytes em "
          f"{t_dec:.1f}s ({len(dbf) / max(t_dec, 1e-6) / 1e6:.1f} MB/s); {len(campos)} colunas; "
          f"registros declarados {int.from_bytes(dbf[4:8], 'little')}")
    print(f"[sih] colunas: {' '.join(c[0] for c in campos)}")
    cont = contar_internacoes(registros_dbf(dbf, ["IDENT", "DIAG_PRINC", "ANO_CMPT", "MES_CMPT", "MUNIC_RES"]))
    print(f"[sih] contagem {nome}: {cont}")
    try:
        for rec in ("ni", "nr"):
            print(f"[sih] TabNet {rec} {uf} {aamm}: {_tabnet_celula(uf, aamm, rec)[:2500]}")
    except Exception as e:  # noqa: BLE001
        print(f"[sih] TabNet {uf} {aamm}: falhou ({type(e).__name__}: {str(e)[:200]})")
    return 0


# ---------------------------------------------------------------------------------------------
def _dbf_de_teste() -> bytes:
    """DBF mínimo (dBase III) com duas colunas e três registros, um excluído."""
    campos = [("DIAG_PRINC", "C", 4), ("IDENT", "C", 1)]
    rlen = 1 + sum(c[2] for c in campos)
    hsize = 32 + 32 * len(campos) + 1
    cab = bytearray(32)
    cab[0] = 3
    cab[4:8] = (3).to_bytes(4, "little")
    cab[8:10] = hsize.to_bytes(2, "little")
    cab[10:12] = rlen.to_bytes(2, "little")
    for nome, tipo, comp in campos:
        d = bytearray(32)
        d[0:len(nome)] = nome.encode()
        d[11] = ord(tipo)
        d[16] = comp
        cab += d
    cab += b"\x0d"
    regs = b" J180" + b"1" + b"*I219" + b"1" + b" A09 " + b"5"
    return bytes(cab) + regs


def autoteste() -> int:
    erros = []
    # 1. Vetor de teste do próprio blast.c (literais sem código, dicionário 4).
    if explodir(bytes((0x00, 0x04, 0x82, 0x24, 0x25, 0x8F, 0x80, 0x7F))) != b"AIAIAIAIAIAIA":
        erros.append("explodir: vetor do blast.c")
    # 2. Fluxo inválido levanta (cabeçalho e fluxo sem fim).
    for ruim in (bytes((2, 4, 0)), bytes((0, 9, 0)), bytes((0, 4)) + b"\x00" * 4):
        try:
            explodir(ruim)
            erros.append(f"explodir aceitou fluxo inválido {ruim!r}")
        except ValueError:
            pass
    # 3. Tabelas de Huffman completas (todo índice resolve) e do tamanho esperado.
    if None in _LIT or None in _LEN or None in _DIST or (_LIT_K, _LEN_K, _DIST_K) != (13, 7, 8):
        erros.append(f"tabelas DCL incompletas ({_LIT_K}, {_LEN_K}, {_DIST_K})")
    # 4. DBF: colunas, deslocamentos, registro excluído fora, coluna pedida que falta levanta.
    dbf = _dbf_de_teste()
    if [c[:2] for c in campos_dbf(dbf)] != [("DIAG_PRINC", "C"), ("IDENT", "C")]:
        erros.append("campos_dbf")
    regs = list(registros_dbf(dbf))
    if regs != [{"DIAG_PRINC": "J180", "IDENT": "1"}, {"DIAG_PRINC": "A09", "IDENT": "5"}]:
        erros.append(f"registros_dbf: {regs}")
    try:
        list(registros_dbf(dbf, ["NAO_EXISTE"]))
        erros.append("registros_dbf aceitou coluna ausente")
    except ValueError:
        pass
    # 5. dbc = cabeçalho + 4 bytes + DCL; o corpo descomprimido segue o cabeçalho.
    hsize = int.from_bytes(dbf[8:10], "little")
    falso = dbf[:hsize] + b"\0\0\0\0" + bytes((0x00, 0x04, 0x82, 0x24, 0x25, 0x8F, 0x80, 0x7F))
    if dbc_para_dbf(falso) != dbf[:hsize] + b"AIAIAIAIAIAIA":
        erros.append("dbc_para_dbf")
    # 6. Último arquivo por UF e contagem.
    ult = ultimo_por_uf([("RDAC2606.dbc", 10, "20260810"), ("RDAC2607.dbc", 11, "20260910"),
                         ("RJAC2607.dbc", 9, "20260910"), ("RDXX2607.dbc", 1, "")])
    if ult != {"AC": ("2607", 11, "20260910")}:
        erros.append(f"ultimo_por_uf: {ult}")
    c = contar_internacoes(regs)
    if (c["total"], c["cap_J"], c["ident"]) != (2, 1, {"1": 1, "5": 1}):
        erros.append(f"contar_internacoes: {c}")
    # 7. Trava estrutural: o fonte não escreve no banco.
    fonte = pathlib.Path(__file__).read_text(encoding="utf-8")
    corpo = fonte.split("BANCO_PROIBIDO = (", 1)[1].split(")", 1)[1]
    for arq in BANCO_PROIBIDO:
        if re.search(r"(gravar|gravar_em|open)\([^)]*" + re.escape(arq), corpo):
            erros.append(f"trava estrutural: escrita em {arq}")
    if re.search(r"\bgravar(_em|_lote|_pista)?\(", corpo.split("def autoteste", 1)[0]):
        erros.append("trava de processo: a sondagem não pode gravar")
    print("autoteste coletar_sih:", "OK" if not erros else "FALHOU")
    for e in erros:
        print("  -", e)
    return 1 if erros else 0


def main() -> int:
    a = sys.argv[1:]
    if "--autoteste" in a:
        return autoteste()
    if "--sondar" in a:
        uf = a[a.index("--uf") + 1].upper() if "--uf" in a else "AC"
        aamm = a[a.index("--aamm") + 1] if "--aamm" in a else None
        return sondar(uf, aamm)
    print("coletar_sih: só --sondar e --autoteste até a estrutura comum da E1 estar na main")
    return 2


if __name__ == "__main__":
    sys.exit(main())
