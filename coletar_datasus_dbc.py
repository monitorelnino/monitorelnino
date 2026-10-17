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
  python3 coletar_datasus_dbc.py --desfecho leptospirose
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
PAUSA = 2  # segundos entre conexões ao mesmo servidor


def _ftp(timeout: int = 60) -> ftplib.FTP:
    time.sleep(PAUSA)
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


# ---------------------------------------------------------------- desfechos
# Desfecho → sistema → arquivos → filtro → agregação. O período é o mês de início dos sintomas; o
# território, a UF de residência. Um caso sem UF de residência não é atribuído a UF nenhuma: entra
# na contagem declarada `sem_uf` da fonte, nunca em outra UF.
DESFECHOS = {
    "leptospirose": {
        "sistema": "SINAN", "prefixo": "LEPT", "rotulo": "Leptospirose, casos confirmados",
        "criterio": "CLASSI_FIN = 1 (confirmado)", "campos": ("CLASSI_FIN", "SG_UF", "DT_SIN_PRI", "DT_NOTIFIC"),
        "confirmado": lambda r: r.get("CLASSI_FIN") == "1",
        # Investigação do SINAN fecha em até 60 dias: os três últimos meses ainda crescem.
        "n_parciais": 3,
    },
}
ANO_INICIAL = 2019


def agregar(linhas, confirmado, uf_de: dict, ano_inicial: int = ANO_INICIAL) -> tuple:
    """({UF: {AAAA-MM: n}}, sem_uf, mês mais recente notificado). Função pura."""
    serie = {}; sem_uf = 0; ultimo_notif = ""
    for r in linhas:
        dn = r.get("DT_NOTIFIC") or ""
        if len(dn) == 8 and dn[:6] > ultimo_notif:
            ultimo_notif = dn[:6]
        if not confirmado(r):
            continue
        ds = r.get("DT_SIN_PRI") or ""
        if len(ds) != 8 or not ds.isdigit() or int(ds[:4]) < ano_inicial:
            continue
        uf = uf_de.get(r.get("SG_UF") or "")
        if not uf:
            sem_uf += 1; continue
        per = f"{ds[:4]}-{ds[4:6]}"
        serie.setdefault(uf, {}); serie[uf][per] = serie[uf].get(per, 0) + 1
    return serie, sem_uf, (f"{ultimo_notif[:4]}-{ultimo_notif[4:]}" if ultimo_notif else None)


def completar(serie: dict, ufs, ate: str, desde: str = f"{ANO_INICIAL}-01") -> dict:
    """Zero medido em todo mês coberto pelos arquivos lidos (até o último mês notificado); depois
    dele, nada: mês não coberto é lacuna, não zero. Função pura."""
    meses = []
    a, m = int(desde[:4]), int(desde[5:])
    while f"{a}-{m:02d}" <= ate:
        meses.append(f"{a}-{m:02d}"); m += 1
        if m == 13:
            a, m = a + 1, 1
    return {uf: {p: serie.get(uf, {}).get(p, 0) for p in meses} for uf in ufs}


def arquivos_do_sinan(prefixo: str, listar=None) -> list:
    """[(caminho, preliminar)] de 2019 em diante: FINAIS onde houver, PRELIM nos anos sem final."""
    listar = listar or listar_ftp
    finais = {n[-6:-4]: f"{SINAN}/FINAIS/{n}" for n, _ in listar(f"{SINAN}/FINAIS")
              if n.upper().startswith(prefixo + "BR") and n.lower().endswith(".dbc")}
    prelim = {n[-6:-4]: f"{SINAN}/PRELIM/{n}" for n, _ in listar(f"{SINAN}/PRELIM")
              if n.upper().startswith(prefixo + "BR") and n.lower().endswith(".dbc")}
    out = []
    for aa in sorted(set(finais) | set(prelim)):
        if int(aa) + 2000 < ANO_INICIAL:
            continue
        out.append((finais[aa], False) if aa in finais else (prelim[aa], True))
    return out


def coletar(nome: str, listar=None, baixar=None, ler_fn=None, gravar_fn=None, hoje: str = None) -> bool:
    """Lê os arquivos do SINAN do desfecho e grava o arquivo comum. Só regrava se algum arquivo mudou."""
    import desfechos_sus as ds
    from coletores_base import ler, gravar, data_da_edicao
    ler_fn = ler_fn or ler; gravar_fn = gravar_fn or gravar; baixar = baixar or baixar_ftp
    cfg = DESFECHOS[nome]
    anterior = ler_fn(ds.caminho(nome))
    arquivos = arquivos_do_sinan(cfg["prefixo"], listar)
    if not arquivos:
        print(f"{nome}: nenhum arquivo {cfg['prefixo']} no FTP; o arquivo anterior fica"); return False
    uf_de = ds.uf_por_codigo(ler_fn)
    serie = {}; sem_uf = 0; ate = None; lidos = []
    for caminho, prelim in arquivos:
        bruto = baixar(caminho)
        _, linhas = ler_dbc(bruto, cfg["campos"])
        s, su, ult = agregar(linhas, cfg["confirmado"], uf_de)
        if ult is None:
            raise DbcInvalido(f"{caminho}: nenhum registro com data de notificação; arquivo recusado")
        for uf, meses in s.items():
            for p, n in meses.items():
                serie.setdefault(uf, {}); serie[uf][p] = serie[uf].get(p, 0) + n
        sem_uf += su; ate = max(filter(None, (ate, ult)), default=None)
        lidos.append({"arquivo": caminho, "sha256": hashlib.sha256(bruto).hexdigest(), "preliminar": prelim})
    if len(uf_de) < 27:
        raise DbcInvalido("referência IBGE sem as 27 UFs; nada a montar")
    hashes = [a["sha256"] for a in lidos]
    if anterior and [a.get("sha256") for a in anterior.get("fonte", {}).get("arquivos", [])] == hashes:
        print(f"{nome}: arquivos do FTP iguais aos da última leitura; nada a regravar"); return False
    fonte = {"sistema": f"{cfg['sistema']} (Ministério da Saúde), microdados no FTP do DATASUS",
             "url": f"ftp://{FTP_HOST}{SINAN}/", "criterio": cfg["criterio"],
             "data_do_periodo": "início dos sintomas (DT_SIN_PRI)", "uf": "residência (SG_UF)",
             "sem_uf_de_residencia": sem_uf, "arquivos": lidos}
    obj = ds.montar(desfecho=nome, rotulo=cfg["rotulo"], unidade="casos", periodo="mes",
                    territorio="UF de residência", serie=completar(serie, sorted(set(uf_de.values())), ate),
                    fonte=fonte, cadencia="semanal; o DATASUS republica o arquivo preliminar sem data fixa",
                    coletado_em=hoje or data_da_edicao().isoformat(),
                    anos_preliminares=[2000 + int(c[-6:-4]) for c, p in arquivos if p],
                    n_parciais=cfg["n_parciais"], populacao=ds.populacao_por_uf(ler_fn), anterior=anterior)
    return ds.gravar_desfecho(obj, gravar_fn=gravar_fn)


def sondar() -> int:
    """Só mede e imprime: diretórios do SINAN e os arquivos de cada desfecho."""
    print(f"cliente: senha anônima '{SENHA_ANONIMA}' · {ua_de('sondagem DATASUS')}")
    for nome, cfg in DESFECHOS.items():
        try:
            print(f"[ftp] {nome}: {arquivos_do_sinan(cfg['prefixo'])}")
        except Exception as e:  # noqa: BLE001
            print(f"[ftp] {nome}: FALHA {type(e).__name__}: {e}")
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


def _comprimir_so_literais(dados: bytes) -> bytes:
    """Codificador mínimo do formato (literais sem código + marca de fim), só para o autoteste."""
    bits = []
    def poe(v, k):
        bits.extend((v >> i) & 1 for i in range(k))
    poe(0, 8); poe(4, 8)
    for b in dados:
        poe(0, 1); poe(b, 8)
    v, L = next((t, e[1]) for t, e in enumerate(_T_LEN) if e == (15, e[1]) and t < (1 << e[1]))
    poe(1, 1); poe(v, L); poe(255, 8)
    bits += [0] * (-len(bits) % 8)
    return bytes(sum(bits[i + j] << j for j in range(8)) for i in range(0, len(bits), 8))


def _dbc_de_teste(linhas, campos) -> bytes:
    dbf = _dbf_de_teste(linhas, campos)
    t_cab = struct.unpack("<H", dbf[8:10])[0]
    return dbf[:t_cab] + b"\x00" * 4 + _comprimir_so_literais(dbf[t_cab:])


_CAMPOS_LEPT = (("CLASSI_FIN", 1), ("SG_UF", 2), ("DT_SIN_PRI", 8), ("DT_NOTIFIC", 8))


def _teste_dbc_ida_e_volta():
    d = _dbc_de_teste([(("1", "23", "20260105", "20260110"), False)], _CAMPOS_LEPT)
    return list(ler_dbc(d)[1]) == [{"CLASSI_FIN": "1", "SG_UF": "23", "DT_SIN_PRI": "20260105", "DT_NOTIFIC": "20260110"}]


def _teste_agregar():
    ls = [{"CLASSI_FIN": "1", "SG_UF": "23", "DT_SIN_PRI": "20260105", "DT_NOTIFIC": "20260110"},
          {"CLASSI_FIN": "1", "SG_UF": "23", "DT_SIN_PRI": "20260120", "DT_NOTIFIC": "20260301"},
          {"CLASSI_FIN": "2", "SG_UF": "23", "DT_SIN_PRI": "20260120", "DT_NOTIFIC": "20260401"},
          {"CLASSI_FIN": "1", "SG_UF": "", "DT_SIN_PRI": "20260120", "DT_NOTIFIC": "20260110"},
          {"CLASSI_FIN": "1", "SG_UF": "26", "DT_SIN_PRI": "20180120", "DT_NOTIFIC": "20180110"}]
    s, sem, ult = agregar(ls, DESFECHOS["leptospirose"]["confirmado"], {"23": "CE", "26": "PE"})
    return s == {"CE": {"2026-01": 2}} and sem == 1 and ult == "2026-04"


def _teste_completar_zero_e_lacuna():
    c = completar({"CE": {"2019-02": 3}}, ["CE", "PE"], ate="2019-03")
    return c == {"CE": {"2019-01": 0, "2019-02": 3, "2019-03": 0}, "PE": {"2019-01": 0, "2019-02": 0, "2019-03": 0}}


def _teste_finais_antes_de_prelim():
    lst = {f"{SINAN}/FINAIS": [("LEPTBR18.dbc", 1), ("LEPTBR24.dbc", 1)],
           f"{SINAN}/PRELIM": [("LEPTBR24.dbc", 1), ("LEPTBR25.dbc", 1), ("HEPABR25.dbc", 1)]}
    return arquivos_do_sinan("LEPT", listar=lambda c: lst[c]) == [
        (f"{SINAN}/FINAIS/LEPTBR24.dbc", False), (f"{SINAN}/PRELIM/LEPTBR25.dbc", True)]


def _teste_coletar_offline_e_idempotente():
    """Ponta a ponta sem rede e sem disco: o par ler/gravar é falso; segunda leitura igual não regrava."""
    ufs = [("11", "RO"), ("12", "AC"), ("13", "AM"), ("14", "RR"), ("15", "PA"), ("16", "AP"), ("17", "TO"),
           ("21", "MA"), ("22", "PI"), ("23", "CE"), ("24", "RN"), ("25", "PB"), ("26", "PE"), ("27", "AL"),
           ("28", "SE"), ("29", "BA"), ("31", "MG"), ("32", "ES"), ("33", "RJ"), ("35", "SP"), ("41", "PR"),
           ("42", "SC"), ("43", "RS"), ("50", "MS"), ("51", "MT"), ("52", "GO"), ("53", "DF")]
    ref = [{"codigo_ibge": int(c + "00000"), "uf": u} for c, u in ufs]
    pop = {c + "00000": 100000 for c, _ in ufs}
    banco = {"municipios_ibge_referencia.json": ref, "populacao_censo2022.json": pop}
    escritos = []
    def gravar_falso(nome, obj, compacto=False):
        banco[nome] = obj; escritos.append(nome)
    lst = {f"{SINAN}/FINAIS": [("LEPTBR19.dbc", 1)], f"{SINAN}/PRELIM": [("LEPTBR26.dbc", 1)]}
    linhas = [(("1", c, f"2019{m:02d}10", f"2019{m:02d}12"), False) for c, _ in ufs for m in (1, 6, 12)]
    arqs = {f"{SINAN}/FINAIS/LEPTBR19.dbc": _dbc_de_teste(linhas, _CAMPOS_LEPT),
            f"{SINAN}/PRELIM/LEPTBR26.dbc": _dbc_de_teste([(("1", "23", "20260201", "20260305"), False)], _CAMPOS_LEPT)}
    kw = dict(listar=lambda c: lst[c], baixar=lambda c: arqs[c], ler_fn=banco.get, gravar_fn=gravar_falso, hoje="2026-10-17")
    ok1 = coletar("leptospirose", **kw)
    o = banco.get("saude_desfechos/leptospirose.json") or {}
    ok2 = coletar("leptospirose", **kw)
    return (ok1 and not ok2 and escritos == ["saude_desfechos/leptospirose.json"]
            and o["serie"]["CE"]["2026-02"] == 1 and o["serie"]["CE"]["2026-03"] == 0
            and "2026-04" not in o["serie"]["CE"] and o["serie"]["BR"]["2019-06"] == 27
            and o["anos_preliminares"] == [2026] and o["parcial"] == ["2026-01", "2026-02", "2026-03"])


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
    from desfechos_sus import fonte_cita_banco
    return not fonte_cita_banco(__file__)


def _teste_arquivo_vazio_recusa():
    lst = {f"{SINAN}/FINAIS": [("LEPTBR19.dbc", 1)], f"{SINAN}/PRELIM": []}
    vazio = _dbc_de_teste([], _CAMPOS_LEPT)
    try:
        coletar("leptospirose", listar=lambda c: lst[c], baixar=lambda c: vazio,
                ler_fn=lambda n: None, gravar_fn=lambda *a, **k: None, hoje="2026-10-17")
        return False
    except DbcInvalido:
        return True


TESTES = {
    "blast: vetor de teste do blast.c": _teste_vetor_do_blast,
    "DBC: ida e volta pelo formato": _teste_dbc_ida_e_volta,
    "agregação: confirmados, sem UF declarado à parte, antes de 2019 fora": _teste_agregar,
    "mês coberto sem caso é zero; mês não coberto não existe": _teste_completar_zero_e_lacuna,
    "ano com arquivo final não lê o preliminar": _teste_finais_antes_de_prelim,
    "coleta ponta a ponta offline; arquivo igual não regrava": _teste_coletar_offline_e_idempotente,
    "arquivo sem data de notificação é recusado, nunca vira zeros": _teste_arquivo_vazio_recusa,
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
    if "--desfecho" in sys.argv:
        nome = sys.argv[sys.argv.index("--desfecho") + 1]
        try:
            coletar(nome)
        except Exception as e:  # noqa: BLE001 — falha de fonte é lacuna; o arquivo anterior fica
            from coletores_base import registrar_lacuna
            registrar_lacuna(f"ftp://{FTP_HOST}{SINAN}/ ({nome})", f"{type(e).__name__}: {e}; o arquivo anterior fica",
                             canal="desfechos_sus", camada=3)
            sys.exit(1)
        sys.exit(0)
    print(__doc__)
