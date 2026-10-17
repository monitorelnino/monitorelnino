#!/usr/bin/env python3
"""Internações do SUS por grupo de causa, UF e mês: SIH/SUS (AIH reduzida, arquivos RD do DATASUS).

Faixa E2 (HANDOVER_SUS_DESFECHOS_16-10-2026, camada C). Peso zero, como todo o MARÉ Saúde: conta
internações registradas; não atribui nenhuma ao El Niño.

O QUE A SÉRIE CONTA
-------------------
Internações aprovadas (AIH) por UF do HOSPITAL e mês de PROCESSAMENTO (competência `ANO_CMPT`/
`MES_CMPT`), como o TabNet "Internações" (que exclui a AIH de longa permanência, `IDENT` 5). O
diagnóstico é o principal (`DIAG_PRINC`). A competência é preliminar por meses: AIH reapresentada
entra depois, e o último mês publicado é sempre `parcial`.

ROTA
----
FTP público do DATASUS (anônimo, sem robots.txt por ser FTP; a senha anônima identifica o cliente).
Arquivo `.dbc` = DBF comprimido; descompressão por `datasus-dbc` (MIT) e leitura por `dbfread`
(MIT). `pyreaddbc` foi descartado por ser AGPL.

USO
  python3 coletar_sih.py --autoteste
  python3 coletar_sih.py --sondar          # só mede e imprime; não grava nada
"""
import datetime
import ftplib
import io
import pathlib
import re
import struct
import sys
import tempfile
import time

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

FTP_HOST = "ftp.datasus.gov.br"
FTP_DIR_RD = "/dissemin/publicos/SIHSUS/200801_/Dados"
FTP_SENHA = "monitorelnino.com.br"  # identificação do cliente no FTP anônimo
FTP_DIRS_SINAN = ["/dissemin/publicos/SINAN/DADOS/PRELIM", "/dissemin/publicos/SINAN/DADOS/FINAIS"]
TABNET_DEF = "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/niuf.def"
TABNET_TAB = "http://tabnet.datasus.gov.br/cgi/tabcgi.exe?sih/cnv/niuf.def"
UFS = ("AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO").split()
RE_RD = re.compile(r"^RD([A-Z]{2})(\d{2})(\d{2})\.DBC$", re.I)

# grupo -> faixas de CID-10 (inclusivas, por letra e dois dígitos), do mapa do handover §1.
GRUPOS = {
    "respiratorias": [("J00", "J22")],
    "cardio": [("I20", "I25"), ("I60", "I64")],
    "renal": [("N17", "N19")],
    "desidratacao": [("E86", "E86")],
    "fumaca": [("T59", "T59")],
    "calor": [("T67", "T67")],
}


# ============================================================================================
# Funções puras
# ============================================================================================
def grupo_do_cid(cid: str) -> list:
    """Grupos aos quais o CID principal pertence (pelos três primeiros caracteres). Função pura."""
    c = (cid or "").strip().upper()[:3]
    if not re.fullmatch(r"[A-Z]\d{2}", c):
        return []
    return [g for g, faixas in GRUPOS.items() if any(a <= c <= b for a, b in faixas)]


def agregar(registros) -> dict:
    """{'total'|grupo: {UF: {'AAAA-MM': n}}} a partir de registros RD (dicts). Função pura.

    Conta AIH que não são de longa permanência (IDENT != '5'). A UF vem de `UF_ZI` (dois primeiros
    dígitos IBGE do gestor) só quando o chamador não a fornece em `_UF`."""
    out = {}
    for r in registros:
        if str(r.get("IDENT") or "").strip() == "5":
            continue
        uf = r.get("_UF")
        ano, mes = str(r.get("ANO_CMPT") or "").strip(), str(r.get("MES_CMPT") or "").strip()
        if not uf or not (ano.isdigit() and mes.isdigit()):
            continue
        chave = f"{int(ano):04d}-{int(mes):02d}"
        for g in ["total"] + grupo_do_cid(r.get("DIAG_PRINC")):
            d = out.setdefault(g, {}).setdefault(uf, {})
            d[chave] = d.get(chave, 0) + 1
    # Mês lido sem caso do grupo é ZERO medido (o arquivo inteiro foi lido); mês sem arquivo não
    # aparece em lugar nenhum — essa é a ausência, e ela não vira zero.
    for uf, por_mes in out.get("total", {}).items():
        for g in GRUPOS:
            d = out.setdefault(g, {}).setdefault(uf, {})
            for chave in por_mes:
                d.setdefault(chave, 0)
    return out


def ultimo_por_uf(nomes) -> dict:
    """{UF: 'AAAA-MM'} da competência mais recente publicada, a partir da listagem. Função pura."""
    out = {}
    for n in nomes:
        m = RE_RD.match(n.strip())
        if not m:
            continue
        uf, aa, mm = m.group(1).upper(), int(m.group(2)), int(m.group(3))
        chave = f"{2000 + aa:04d}-{mm:02d}"
        if chave > out.get(uf, ""):
            out[uf] = chave
    return out


def meses_de_atraso(competencia: str, hoje: datetime.date) -> int:
    """Meses entre a competência 'AAAA-MM' e o mês de hoje. Função pura."""
    a, m = int(competencia[:4]), int(competencia[5:7])
    return (hoje.year - a) * 12 + (hoje.month - m)


def ler_dbf(dbf: bytes):
    """Registros de um DBF (bytes) como dicts. Lê por arquivo temporário: `dbfread` só abre caminho."""
    from dbfread import DBF
    with tempfile.NamedTemporaryFile(suffix=".dbf") as t:
        t.write(dbf)
        t.flush()
        return list(DBF(t.name, encoding="latin-1", char_decode_errors="replace"))


def ler_dbc(dbc: bytes):
    """Registros de um `.dbc` do DATASUS."""
    import datasus_dbc
    return ler_dbf(datasus_dbc.decompress_bytes(dbc))


def celula_tabnet(html: str, rotulo: str):
    """Número que segue o rótulo na tabela do TabNet (texto sem marcação), ou None. Função pura.

    O TabNet nem sempre fecha `<td>`; ler o texto plano evita depender da marcação."""
    import html as _h
    plano = re.sub(r"\s+", " ", _h.unescape(re.sub(r"<[^>]+>", " ", html or "")))
    m = re.search(re.escape(rotulo) + r"\s+([\d.]+)(?!\d)", plano, re.I)
    return int(m.group(1).replace(".", "")) if m else None


def form_tabnet(html: str) -> dict:
    """{nome_do_select: [(valor, texto, selecionado)]} do formulário do TabNet. Função pura."""
    out = {}
    for nome, corpo in re.findall(r'<select[^>]*name="?([^"\s>]+)"?[^>]*>(.*?)</select>',
                                  html or "", re.S | re.I):
        ops = []
        for attrs, texto in re.findall(r"<option([^>]*)>([^<]*)", corpo, re.I):
            v = re.search(r'value="([^"]*)"', attrs, re.I)
            ops.append((v.group(1) if v else texto.strip(), texto.strip(), "selected" in attrs.lower()))
        out[nome] = ops
    return out


# ============================================================================================
# Sondagem (rede; só mede e imprime)
# ============================================================================================
def _ftp():
    f = ftplib.FTP(FTP_HOST, timeout=60)
    f.login("anonymous", FTP_SENHA)
    return f


def sondar() -> int:
    from coletores_base import buscar, enviar
    hoje = datetime.date.today()
    print(f"== SIH/SUS · FTP {FTP_HOST}{FTP_DIR_RD} · {hoje}")
    t0 = time.time()
    try:
        f = _ftp()
        f.cwd(FTP_DIR_RD)
        nomes = f.nlst()
    except Exception as e:  # noqa: BLE001
        print(f"FTP: falhou ({type(e).__name__}: {e})")
        return 0
    print(f"listagem: {len(nomes)} nomes em {time.time() - t0:.1f}s")
    ult = ultimo_por_uf(nomes)
    for uf in UFS:
        c = ult.get(uf)
        print(f"  {uf}: {c or 'sem RD'}" + (f" · atraso {meses_de_atraso(c, hoje)} meses" if c else ""))
    if not ult:
        return 0
    comp = ult.get("AC") or max(ult.values())
    nome = f"RDAC{comp[2:4]}{comp[5:7]}.dbc"
    try:
        mdtm = f.sendcmd(f"MDTM {nome}")
    except Exception as e:  # noqa: BLE001
        mdtm = f"MDTM indisponível ({e})"
    buf = io.BytesIO()
    t0 = time.time()
    f.retrbinary(f"RETR {nome}", buf.write)
    for d in FTP_DIRS_SINAN:  # hepatite A (SINAN HEPA): onde está e até que ano
        try:
            f.cwd(d)
            hepa = sorted(n for n in f.nlst() if n.upper().startswith("HEPA"))
            print(f"SINAN {d}: HEPA {hepa[-4:]} ({len(hepa)} arquivos)")
            for n in hepa[-1:]:
                print(f"  {n}: {f.sendcmd(f'MDTM {n}')} · {f.size(n)} bytes")
        except Exception as e:  # noqa: BLE001
            print(f"SINAN {d}: falhou ({type(e).__name__}: {e})")
    f.quit()
    dbc = buf.getvalue()
    print(f"baixado {nome}: {len(dbc)} bytes em {time.time() - t0:.1f}s · {mdtm}")
    regs = ler_dbc(dbc)
    print(f"registros: {len(regs)} · colunas: {list(regs[0].keys()) if regs else []}")
    idents = {}
    for r in regs:
        idents[str(r.get("IDENT"))] = idents.get(str(r.get("IDENT")), 0) + 1
    print(f"IDENT: {idents}")
    for r in regs:
        r["_UF"] = "AC"
    ag = agregar(regs)
    for g in ag:
        print(f"  {g}: {ag[g].get('AC')}")
    # TabNet: uma célula (Acre, internações, competência do arquivo)
    try:
        form = form_tabnet(buscar(TABNET_DEF, timeout=60).decode("latin-1"))
        print(f"TabNet: selects {list(form)}")
        aamm = f"{comp[2:4]}{comp[5:7]}"
        arq = [v for v, _t, _s in form.get("Arquivos", []) if aamm in v]
        print(f"  Arquivos com {aamm}: {arq} (primeiros: {[v for v, _t, _s in form.get('Arquivos', [])][:4]})")
        linha = next((v for v, t, _s in form.get("Linha", []) if "Unidade da Federa" in t), None)
        incr = next((v for v, t, _s in form.get("Incremento", []) if t.startswith("Interna")), None)
        dados = {}
        for nome_s, ops in form.items():
            sel = [v for v, _t, s in ops if s] or ([ops[0][0]] if ops else [])
            dados[nome_s.encode("latin-1")] = (sel[0] if sel else "").encode("latin-1")
        dados.update({b"Linha": (linha or "").encode("latin-1"),
                      b"Coluna": "--Não-Ativa--".encode("latin-1"),
                      b"Incremento": (incr or "").encode("latin-1"),
                      b"Arquivos": (arq[0] if arq else "").encode("latin-1"),
                      b"formato": b"table", b"mostre": b"Mostra"})
        html = enviar(TABNET_TAB, dados, timeout=90).decode("latin-1")
        tab = celula_tabnet(html, "Acre")
        print(f"TabNet Acre {comp}: {tab} · arquivo decodificado: {ag.get('total', {}).get('AC', {}).get(comp)}"
              f" · bate: {tab == ag.get('total', {}).get('AC', {}).get(comp)}")
        if tab is None:
            plano = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
            i = plano.find("Acre")
            print("  trecho:", plano[max(i - 200, 0):i + 400] if i >= 0 else plano[-800:])
    except Exception as e:  # noqa: BLE001
        print(f"TabNet: falhou ({type(e).__name__}: {str(e)[:200]})")
    return 0


# ============================================================================================
# Autoteste (sem rede, sem escrita)
# ============================================================================================
def _dbf_de(campos, linhas) -> bytes:
    """DBF mínimo (dBase III, só campos C) para o autoteste."""
    larg = [w for _n, w in campos]
    tam_reg = 1 + sum(larg)
    cab = struct.pack("<BBBBIHH20x", 3, 126, 10, 17, len(linhas), 32 + 32 * len(campos) + 1, tam_reg)
    for n, w in campos:
        cab += struct.pack("<11sc4xBB14x", n.encode(), b"C", w, 0)
    cab += b"\r"
    corpo = b"".join(b" " + b"".join(str(v).encode("latin-1").ljust(w)[:w] for v, w in zip(l, larg))
                     for l in linhas)
    return cab + corpo + b"\x1a"


def autoteste() -> int:
    casos = []
    casos.append(("J18 é respiratória", grupo_do_cid("J189") == ["respiratorias"]))
    casos.append(("I21 e I63 são cardio", grupo_do_cid("I219") == ["cardio"] == grupo_do_cid("I64")))
    casos.append(("I26 não é cardio deste recorte", grupo_do_cid("I26") == []))
    casos.append(("E86, T59, T67 e N18", [grupo_do_cid(c) for c in ("E86", "T590", "T671", "N189")]
                  == [["desidratacao"], ["fumaca"], ["calor"], ["renal"]]))
    casos.append(("CID ilegível não entra em grupo", grupo_do_cid("") == grupo_do_cid("9XX") == []))
    regs = [{"_UF": "AC", "ANO_CMPT": "2026", "MES_CMPT": "07", "IDENT": "1", "DIAG_PRINC": "J180"},
            {"_UF": "AC", "ANO_CMPT": "2026", "MES_CMPT": "07", "IDENT": "1", "DIAG_PRINC": "A09"},
            {"_UF": "AC", "ANO_CMPT": "2026", "MES_CMPT": "07", "IDENT": "5", "DIAG_PRINC": "J180"},
            {"_UF": "AC", "ANO_CMPT": "", "MES_CMPT": "07", "IDENT": "1", "DIAG_PRINC": "J180"}]
    ag = agregar(regs)
    casos.append(("total conta AIH não de longa permanência", ag["total"]["AC"] == {"2026-07": 2}))
    casos.append(("grupo conta só o seu CID", ag["respiratorias"]["AC"] == {"2026-07": 1}))
    casos.append(("competência ilegível não vira mês", "2026-00" not in ag["total"]["AC"]))
    casos.append(("mês lido sem caso do grupo é zero medido", ag["cardio"]["AC"] == {"2026-07": 0}))
    casos.append(("UF sem arquivo lido não aparece (ausência ≠ zero)", "RR" not in ag["cardio"]))
    ult = ultimo_por_uf(["RDAC2606.dbc", "RDAC2607.dbc", "RDSP2605.DBC", "LEIAME.txt", "RDBR2607.dbc"])
    casos.append(("última competência por UF", ult == {"AC": "2026-07", "SP": "2026-05", "BR": "2026-07"}))
    casos.append(("atraso em meses", meses_de_atraso("2026-07", datetime.date(2026, 10, 17)) == 3))
    dbf = _dbf_de([("ANO_CMPT", 4), ("MES_CMPT", 2), ("IDENT", 1), ("DIAG_PRINC", 4)],
                  [("2026", "07", "1", "J180"), ("2026", "07", "5", "I219")])
    try:
        lidos = ler_dbf(dbf)
        casos.append(("lê DBF", [r["DIAG_PRINC"] for r in lidos] == ["J180", "I219"]))
    except ImportError:
        casos.append(("lê DBF (dbfread ausente: requirements)", False))
    html = ("<table><tr><th>UF</th><th>Interna&ccedil;&otilde;es</th></tr><tr><td>.. Acre<td>3.456"
            "<tr><td>Total</td><td>9.999</td></tr></table>")
    casos.append(("célula do TabNet com separador de milhar", celula_tabnet(html, "Acre") == 3456))
    casos.append(("rótulo ausente é None, não zero", celula_tabnet(html, "Roraima") is None))
    form = form_tabnet('<select name="Arquivos"><option value="niuf2607.dbf" selected>Jul/2026'
                       '<option value="niuf2606.dbf">Jun/2026</select>')
    casos.append(("lê o formulário", form == {"Arquivos": [("niuf2607.dbf", "Jul/2026", True),
                                                           ("niuf2606.dbf", "Jun/2026", False)]}))
    fonte = pathlib.Path(__file__).read_text(encoding="utf-8").split("def autoteste")[0]
    proibidos = ("estados.json", "saude_uf.json", "municipios.json", "indice.json", "monitor_saude.json")
    casos.append(("trava estrutural: não escreve nos arquivos do índice",
                  not any(p in fonte for p in proibidos)))
    casos.append(("trava estrutural: a sondagem não grava", "gravar" not in fonte.split("def sondar")[1]))
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
    if "--sondar" in sys.argv:
        return sondar()
    print("coletar_sih: a série espera a estrutura comum de desfechos (E1); use --sondar ou --autoteste")
    return 0


if __name__ == "__main__":
    sys.exit(main())
