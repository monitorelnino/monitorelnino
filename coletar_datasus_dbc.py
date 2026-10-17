#!/usr/bin/env python3
"""Desfechos do SUS pelo FTP do DATASUS: leitor `.dbc` e sondagem (janela E1, 17/10/2026).

HANDOVER_SUS_DESFECHOS_16-10-2026 §2.1. O DATASUS publica os microdados do SINAN, do SIH e do SIM
em `ftp.datasus.gov.br/dissemin/publicos/`, em `.dbc`: um DBF cujo corpo vem comprimido pelo
formato PKWARE DCL ("implode"). Ler esse formato destrava, de uma vez, os desfechos que o catálogo
marcava "não coletável por máquina".

O LEITOR É NOSSO, EM PYTHON PURO
--------------------------------
As bibliotecas que leem `.dbc` (`pyreaddbc`, `read.dbc`) são AGPL-3.0; licença de dependência é
decisão da editoria, e o formato é pequeno. `explodir` é a tradução, para Python, do `blast.c` de
Mark Adler (zlib/contrib/blast, licença zlib, que permite a tradução com o crédito mantido). O DBF
é lido com `struct`. Nenhuma dependência nova entra no `requirements.txt`.

MICRODADO NÃO SE GUARDA
-----------------------
O `.dbc` é lido em memória, agregado (UF × mês) e descartado; nenhuma linha individual entra no
repositório. O que se guarda é a contagem, com o nome e o hash do arquivo de origem.

USO
  python3 coletar_datasus_dbc.py --autoteste
  python3 coletar_datasus_dbc.py --sondar          # só mede e imprime; não escreve em data/
"""
import ftplib
import hashlib
import io
import struct
import sys
import time

from coletores_base import ua_de, rodar_autoteste

FTP_HOST = "ftp.datasus.gov.br"
SINAN = "/dissemin/publicos/SINAN/DADOS"
# FTP anônimo não tem User-Agent: a identificação do cliente vai na senha anônima, que o servidor
# registra. Mesma identidade do `ua_de`, sem disfarce.
SENHA_ANONIMA = "monitorelnino.com.br"


# ---------------------------------------------------------------- PKWARE DCL ("blast"), puro
# Tabelas do blast.c (Mark Adler, 2003/2012, licença zlib). Comprimidas: cada byte é
# (repetições - 1) << 4 | comprimento do código.
_LITLEN = bytes([
    11, 124, 8, 7, 28, 7, 188, 13, 76, 4, 10, 8, 12, 10, 12, 10, 8, 23, 8,
    9, 7, 6, 7, 8, 7, 6, 55, 8, 23, 24, 12, 11, 7, 9, 11, 12, 6, 7, 22, 5,
    7, 24, 6, 11, 9, 6, 7, 22, 7, 11, 38, 7, 9, 8, 25, 11, 8, 11, 9, 12,
    8, 12, 5, 38, 5, 38, 5, 11, 7, 5, 6, 21, 6, 10, 53, 8, 7, 24, 10, 27,
    44, 253, 253, 253, 252, 252, 252, 13, 12, 45, 12, 45, 12, 61, 12, 45,
    44, 173])
_LENLEN = bytes([2, 35, 36, 53, 38, 23])
_DISTLEN = bytes([2, 20, 53, 230, 247, 151, 248])
_BASE = (3, 2, 4, 5, 6, 7, 8, 9, 10, 12, 16, 24, 40, 72, 136, 264)
_EXTRA = (0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8)
_MAXBITS = 13


class DbcInvalido(ValueError):
    """Arquivo que não é `.dbc`/DBF legível. Nunca vira série: vira lacuna com o motivo."""


def _tabela(rep: bytes, n_simbolos: int) -> list:
    """Tabela de decodificação de 2**13 entradas: (símbolo, bits). Função pura.

    No formato, o código de Huffman canônico vem com os bits invertidos (0↔1) e do mais
    significativo para o menos, lido de um fluxo que anda do bit menos significativo de cada
    byte. A tabela já guarda o código como ele aparece no fluxo."""
    comp = []
    for b in rep:
        comp += [b & 15] * ((b >> 4) + 1)
    if len(comp) != n_simbolos:
        raise AssertionError("tabela do blast com tamanho errado")
    tabela = [None] * (1 << _MAXBITS)
    codigo = 0
    for L in range(1, _MAXBITS + 1):
        for s in range(n_simbolos):
            if comp[s] != L:
                continue
            inv = (~codigo) & ((1 << L) - 1)
            v = int(format(inv, f"0{L}b")[::-1], 2)
            for t in range(v, 1 << _MAXBITS, 1 << L):
                tabela[t] = (s, L)
            codigo += 1
        codigo <<= 1
    return tabela


_T_LIT = _tabela(_LITLEN, 256)
_T_LEN = _tabela(_LENLEN, 16)
_T_DIST = _tabela(_DISTLEN, 64)


def explodir(dados: bytes) -> bytes:
    """Descomprime um fluxo PKWARE DCL inteiro. Função pura (sem rede, sem disco)."""
    pos = 0; buf = 0; cnt = 0; n = len(dados)
    out = bytearray()

    def puxar(k):
        nonlocal pos, buf, cnt
        while cnt < k:
            if pos >= n:
                raise DbcInvalido("fluxo comprimido terminou antes do fim")
            buf |= dados[pos] << cnt; pos += 1; cnt += 8

    def bits(k):
        nonlocal buf, cnt
        puxar(k)
        v = buf & ((1 << k) - 1); buf >>= k; cnt -= k
        return v

    def decodificar(t):
        nonlocal pos, buf, cnt
        while cnt < _MAXBITS and pos < n:
            buf |= dados[pos] << cnt; pos += 1; cnt += 8
        e = t[buf & ((1 << _MAXBITS) - 1)]
        if e is None or e[1] > cnt:
            raise DbcInvalido("código de Huffman inválido")
        buf >>= e[1]; cnt -= e[1]
        return e[0]

    lit = bits(8)
    if lit > 1:
        raise DbcInvalido("cabeçalho do blast: literal inválido")
    dic = bits(8)
    if dic < 4 or dic > 6:
        raise DbcInvalido("cabeçalho do blast: dicionário inválido")
    while True:
        if bits(1):
            s = decodificar(_T_LEN)
            comp = _BASE[s] + bits(_EXTRA[s])
            if comp == 519:
                break
            k = 2 if comp == 2 else dic
            dist = (decodificar(_T_DIST) << k) + bits(k) + 1
            if dist > len(out):
                raise DbcInvalido("distância antes do início")
            ini = len(out) - dist
            if dist >= comp:
                out += out[ini:ini + comp]
            else:
                for i in range(comp):
                    out.append(out[ini + i])
        else:
            out.append(decodificar(_T_LIT) if lit else bits(8))
    return bytes(out)


# ---------------------------------------------------------------- DBF e DBC
def ler_dbf(dados: bytes, campos=None):
    """(descritores, gerador de linhas) de um DBF. `campos` restringe as colunas lidas. Função pura.

    Linha marcada como apagada (`*`) não entra. Texto em latin-1, sem espaços nas pontas; o tipo
    fica como texto: quem agrega decide o que é número."""
    if len(dados) < 32:
        raise DbcInvalido("DBF menor que o cabeçalho")
    n_reg, t_cab, t_reg = struct.unpack("<IHH", dados[4:12])
    desc = []; p = 32; desloc = 1
    while p + 32 <= t_cab and dados[p] != 0x0D:
        nome = dados[p:p + 11].split(b"\x00")[0].decode("latin-1").strip()
        tam = dados[p + 16]
        desc.append({"nome": nome, "tipo": chr(dados[p + 11]), "tamanho": tam, "inicio": desloc})
        desloc += tam; p += 32
    if not desc or desloc != t_reg:
        raise DbcInvalido("descritores do DBF não fecham com o tamanho do registro")
    if t_cab + n_reg * t_reg > len(dados):
        raise DbcInvalido("DBF truncado: menos bytes que os registros declarados")
    quer = [d for d in desc if campos is None or d["nome"] in campos]

    def linhas():
        for i in range(n_reg):
            r = t_cab + i * t_reg
            if dados[r] == 0x2A:  # '*': apagado
                continue
            yield {d["nome"]: dados[r + d["inicio"]:r + d["inicio"] + d["tamanho"]].decode("latin-1").strip()
                   for d in quer}
    return desc, linhas()


def dbc_para_dbf(dados: bytes) -> bytes:
    """`.dbc` → DBF: cabeçalho como está, 4 bytes de CRC pulados, corpo descomprimido. Função pura."""
    if len(dados) < 12:
        raise DbcInvalido("arquivo menor que o cabeçalho")
    t_cab = struct.unpack("<H", dados[8:10])[0]
    if t_cab < 32 or t_cab + 4 > len(dados):
        raise DbcInvalido(f"tamanho de cabeçalho implausível ({t_cab})")
    cab = bytearray(dados[:t_cab]); cab[-1] = 0x0D
    return bytes(cab) + explodir(dados[t_cab + 4:])


def ler_dbc(dados: bytes, campos=None):
    return ler_dbf(dbc_para_dbf(dados), campos)


# ---------------------------------------------------------------- FTP
def _ftp(timeout: int = 60) -> ftplib.FTP:
    f = ftplib.FTP(FTP_HOST, timeout=timeout)
    f.login("anonymous", SENHA_ANONIMA)
    return f


def listar_ftp(caminho: str, tentativas: int = 3) -> list:
    """[(nome, tamanho_em_bytes)] de um diretório do FTP. Erro de rede: três tentativas com espera."""
    for t in range(tentativas):
        try:
            with _ftp() as f:
                f.cwd(caminho)
                linhas = []
                f.retrlines("LIST", linhas.append)
            out = []
            for ln in linhas:
                partes = ln.split()
                if len(partes) >= 4 and partes[-2:] and partes[2].isdigit():   # formato DOS: data hora tam nome
                    out.append((partes[-1], int(partes[2])))
                elif len(partes) >= 9 and partes[4].isdigit():                  # formato Unix
                    out.append((partes[-1], int(partes[4])))
                elif partes:
                    out.append((partes[-1], None))
            return out
        except ftplib.error_perm:
            raise
        except (OSError, EOFError, ftplib.Error):
            if t == tentativas - 1:
                raise
            time.sleep(5 * (t + 1))
    return []


def baixar_ftp(caminho: str, tentativas: int = 3, teto: int = 400 << 20) -> bytes:
    """Conteúdo de um arquivo do FTP, em memória, com teto de tamanho."""
    for t in range(tentativas):
        try:
            buf = io.BytesIO()
            with _ftp(timeout=120) as f:
                def receber(b):
                    buf.write(b)
                    if buf.tell() > teto:
                        raise DbcInvalido(f"arquivo acima do teto de {teto >> 20} MB")
                f.retrbinary(f"RETR {caminho}", receber)
            return buf.getvalue()
        except (ftplib.error_perm, DbcInvalido):
            raise
        except (OSError, EOFError, ftplib.Error):
            if t == tentativas - 1:
                raise
            time.sleep(5 * (t + 1))
    return b""


# ---------------------------------------------------------------- sondagem
def sondar() -> int:
    """Só mede e imprime (HANDOVER §2.1): diretórios, tamanhos, tempo, colunas, contagens."""
    import collections
    import json
    from coletores_base import buscar
    print(f"cliente: senha anônima '{SENHA_ANONIMA}' · {ua_de('sondagem DATASUS')}")
    for d in ("/dissemin/publicos", SINAN):
        try:
            print(f"[ftp] {d}: {[n for n, _ in listar_ftp(d)]}")
        except Exception as e:  # noqa: BLE001
            print(f"[ftp] {d}: FALHA {type(e).__name__}: {e}")
    alvo = None
    for sub in ("PRELIM", "FINAIS"):
        try:
            t0 = time.time(); itens = listar_ftp(f"{SINAN}/{sub}")
            lep = sorted(x for x in itens if x[0].upper().startswith(("LEPT", "HEPA", "DDA", "SURT")))
            print(f"[ftp] {SINAN}/{sub}: {len(itens)} arquivos em {time.time()-t0:.1f}s; "
                  f"prefixos {sorted(collections.Counter(n[:4].upper() for n, _ in itens).items())}")
            print(f"   LEPT/HEPA/DDA/SURT: {lep}")
            lepts = sorted(n for n, _ in lep if n.upper().startswith("LEPT"))
            if lepts and alvo is None and sub == "PRELIM":
                alvo = f"{SINAN}/{sub}/{lepts[-1]}"
            if lepts and sub == "FINAIS":
                alvo_final = f"{SINAN}/{sub}/{lepts[-1]}"
        except Exception as e:  # noqa: BLE001
            print(f"[ftp] {SINAN}/{sub}: FALHA {type(e).__name__}: {e}")
    for caminho in [x for x in (alvo, locals().get("alvo_final")) if x]:
        try:
            t0 = time.time(); bruto = baixar_ftp(caminho); t1 = time.time()
            desc, linhas = ler_dbc(bruto); t2 = time.time()
            L = list(linhas)
            print(f"[dbc] {caminho}: {len(bruto)} B, sha256 {hashlib.sha256(bruto).hexdigest()[:16]}, "
                  f"baixar {t1-t0:.1f}s, decodificar {t2-t1:.1f}s, {len(L)} registros")
            print(f"   colunas: {[d['nome'] for d in desc]}")
            for col in ("CLASSI_FIN", "NU_ANO", "SG_UF_NOT", "SG_UF", "EVOLUCAO", "CRITERIO", "TP_NOT", "ID_AGRAVO"):
                if L and col in L[0]:
                    print(f"   {col}: {sorted(collections.Counter(x[col] for x in L).items())[:40]}")
            conf = [x for x in L if x.get("CLASSI_FIN") == "1"]
            por_uf = collections.Counter(x.get("SG_UF") for x in conf)
            por_mes = collections.Counter((x.get("DT_SIN_PRI") or "")[:6] for x in conf)
            print(f"   confirmados (CLASSI_FIN=1) por UF de residência: {sorted(por_uf.items())}")
            print(f"   confirmados por mês de início de sintomas: {sorted(por_mes.items())}")
            print(f"   exemplo DT_SIN_PRI/DT_NOTIFIC/SEM_PRI: {[(x.get('DT_SIN_PRI'), x.get('DT_NOTIFIC'), x.get('SEM_PRI')) for x in L[:3]]}")
        except Exception as e:  # noqa: BLE001
            print(f"[dbc] {caminho}: FALHA {type(e).__name__}: {e}")
    base = "https://opendatasus.saude.gov.br/api/3/action/package_search?rows=50&q="
    for termo in ("malária", "diarreia", "leptospirose", "síndrome gripal", "SIH", "SIM 2026", "SINAN", "doenças diarreicas"):
        try:
            r = json.loads(buscar(base + termo.replace(" ", "+"), timeout=60))
            res = r.get("result", {}).get("results", [])
            print(f"[opendatasus] '{termo}': {r.get('result', {}).get('count')} → "
                  f"{[(p.get('name'), (p.get('metadata_modified') or '')[:10]) for p in res][:15]}")
        except Exception as e:  # noqa: BLE001
            print(f"[opendatasus] '{termo}': FALHA {type(e).__name__}: {e}")
    return 0


# ---------------------------------------------------------------- autoteste
def _dbf_de_teste(linhas, campos=(("UF", 2), ("MES", 2))) -> bytes:
    t_reg = 1 + sum(t for _, t in campos)
    t_cab = 32 + 32 * len(campos) + 1
    cab = struct.pack("<BBBBIHH20x", 3, 126, 10, 17, len(linhas), t_cab, t_reg)
    for nome, t in campos:
        cab += nome.encode().ljust(11, b"\x00") + b"C" + b"\x00" * 4 + bytes([t, 0]) + b"\x00" * 14
    cab += b"\x0D"
    corpo = b"".join((b"*" if apag else b" ") + b"".join(v.encode("latin-1").ljust(t) for v, (_, t) in zip(vals, campos))
                     for vals, apag in linhas)
    return cab + corpo + b"\x1A"


def _teste_vetor_do_blast():
    # Vetor de teste do próprio blast.c: 00 04 82 24 25 8f 80 7f → "AIAIAIAIAIAIA".
    return explodir(bytes.fromhex("00048224258f807f")) == b"AIAIAIAIAIAIA"


def _teste_dbf():
    d = _dbf_de_teste([(("CE", "03"), False), (("PE", "04"), True), (("RS", "05"), False)])
    desc, ls = ler_dbf(d)
    return [x["nome"] for x in desc] == ["UF", "MES"] and list(ls) == [{"UF": "CE", "MES": "03"}, {"UF": "RS", "MES": "05"}]


def _teste_dbf_truncado_recusa():
    d = _dbf_de_teste([(("CE", "03"), False)] * 3)[:-6]
    try:
        ler_dbf(d); return False
    except DbcInvalido:
        return True


def _teste_dbc_invalido_recusa():
    try:
        dbc_para_dbf(b"\x00" * 8 + struct.pack("<H", 5) + b"\x00" * 20); return False
    except DbcInvalido:
        return True


def _teste_funcoes_puras():
    """Trava estrutural: o leitor não abre rede nem disco (lê o bytecode)."""
    import dis
    proibidos = {"open", "urlopen", "FTP", "_ftp", "gravar", "buscar"}
    for fn in (explodir, ler_dbf, dbc_para_dbf, _tabela):
        nomes = {i.argval for i in dis.get_instructions(fn) if i.opname in ("LOAD_GLOBAL", "LOAD_ATTR", "LOAD_NAME")}
        if nomes & proibidos:
            return False
    return True


def _teste_fonte_nao_escreve_banco():
    """Trava estrutural: este coletor nunca escreve nos arquivos do índice."""
    fonte = open(__file__, encoding="utf-8").read()
    proibidos = ("estados.json", "saude_uf.json", "municipios.json", "indice.json", "monitor_saude.json")
    return not any(f'"{p}"' in fonte.split("def _teste_fonte_nao_escreve_banco")[0] for p in proibidos)


TESTES = {
    "blast: vetor de teste do blast.c": _teste_vetor_do_blast,
    "DBF: lê colunas, pula registro apagado": _teste_dbf,
    "DBF truncado é recusado, nunca lido pela metade": _teste_dbf_truncado_recusa,
    "DBC com cabeçalho implausível é recusado": _teste_dbc_invalido_recusa,
    "leitor é função pura (sem rede, sem disco)": _teste_funcoes_puras,
    "trava estrutural: não escreve nos arquivos do índice": _teste_fonte_nao_escreve_banco,
}


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        sys.exit(rodar_autoteste(TESTES))
    if "--sondar" in sys.argv:
        sys.exit(sondar())
    print(__doc__)
