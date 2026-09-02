#!/usr/bin/env python3
"""
coletores_base.py
=================
Disciplina comum dos coletores da Pista A introduzidos na v2.2.4 (documento de
redesenho de 02/09/2026, §3.8, §4): S2iD/DOU, diários oficiais estaduais,
camada declarada nacional (MUNIC/ICM) e diários municipais.

Cinco regras herdadas de `coletar_sinais_risco.py` e da transferência conceitual:
1. **Nada inventado.** Fonte fora do ar, endpoint não confirmado ou parser sem
   correspondência → lacuna declarada (`registrar_lacuna`), nunca valor estimado.
2. **Descoberta ≠ registro.** O que os coletores acham vai para atos de resposta
   (peso zero) ou para filas de pista; promover pista a registro é humano.
3. **Log estruturado v2** (§3.1): toda consulta gera entrada com data, canal,
   camada, UF/município quando couber, strings, decisão, executor e hash.
4. **Preservação de evidência** (§3.8): todo documento citado ganha cópia em
   `evidencias/<sha256>.<ext>` (ou só o hash, com tentativa de snapshot no
   Wayback, se > 5 MB) e entrada em `data/evidencias.json`.
5. **Livro de fontes consultadas** (`data/fontes_consultadas.json`): por
   município IBGE, quais fontes foram consultadas, quando e com que resultado.
   É deste livro (mais o log) que `recalcular_mare.py` deriva o nível de
   verificação — os coletores nunca escrevem `verificacao_municipal.json`.
"""
import hashlib, json, os, pathlib, sys, urllib.error, urllib.request
from datetime import date, datetime

RAIZ = pathlib.Path(__file__).parent
DATA = RAIZ / "data"
EVID = RAIZ / "evidencias"
LIMITE_EVIDENCIA = 5 * 1024 * 1024  # bytes
UA = "MonitorElNinoBrasil/2.2.4 (+https://monitorelnino.com.br; coletor da Pista A)"
NIVEIS = ("nao_verificado", "nacional", "estadual", "municipal_completo")
EXECUTOR = "robo" if os.environ.get("GITHUB_ACTIONS") else "claude"


def hoje() -> str:
    return date.today().isoformat()


def ler(nome, padrao=None):
    p = DATA / nome
    if not p.exists():
        return padrao
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _indent_de(p) -> int:
    """Reusa a indentação do arquivo existente (diffs limpos nos commits do robô)."""
    try:
        with open(p, encoding="utf-8") as f:
            f.readline(); seg = f.readline()
        n = len(seg) - len(seg.lstrip(" "))
        return n if 0 < n <= 8 else 1
    except FileNotFoundError:
        return 1


def gravar(nome, obj):
    p = DATA / nome
    ind = _indent_de(p)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=ind)
        f.write("\n")


def buscar(url: str, timeout: int = 40) -> bytes:
    """GET simples com User-Agent do projeto. Levanta a exceção — quem chama decide
    se vira lacuna declarada (regra 1) ou aborta."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def preservar_evidencia(conteudo: bytes, url: str, ext: str, origem: str) -> str:
    """Guarda cópia da evidência e indexa em data/evidencias.json. Retorna o hash.
    Acima de 5 MB: só o hash + pedido de snapshot ao Wayback (best effort)."""
    h = sha256(conteudo)
    idx = ler("evidencias.json", {"_governanca": "Índice de evidências preservadas (§3.8, v2.2.4). "
                                   "Chave = sha256 do documento; nunca lido pelo cálculo do índice.",
                                   "itens": {}})
    if h in idx["itens"]:
        return h
    item = {"url": url, "origem": origem, "preservado_em": hoje(), "tamanho": len(conteudo),
            "arquivo": None, "wayback": None}
    if len(conteudo) <= LIMITE_EVIDENCIA:
        EVID.mkdir(exist_ok=True)
        destino = EVID / f"{h}.{ext.lstrip('.')}"
        if not destino.exists():
            destino.write_bytes(conteudo)
        item["arquivo"] = str(destino.relative_to(RAIZ))
    else:
        try:
            buscar("https://web.archive.org/save/" + url, timeout=60)
            item["wayback"] = "https://web.archive.org/web/*/" + url
        except Exception as e:  # noqa: BLE001
            item["wayback"] = f"tentativa falhou ({type(e).__name__})"
    idx["itens"][h] = item
    gravar("evidencias.json", idx)
    return h


def log_busca(canal: str, camada: int, strings: list, decisao: str, resultados: str = "",
              uf=None, municipio=None, ibge=None, nivel=None, n_resultados=None,
              fonte_suspensa_defeso: bool = False, hash_evidencia=None):
    """Acrescenta uma execução ao log v2. `decisao` no vocabulário fechado:
    registro | pista | nada localizado | fonte suspensa (defeso) | erro."""
    assert decisao.split(" ")[0] in ("registro", "pista", "nada", "fonte", "erro"), decisao
    if decisao.startswith("nada localizado"):
        assert nivel == "municipal_completo", "regra §2.1: 'nada localizado' exige bateria municipal completa"
    lg = ler("log_buscas.json")
    assert lg and lg.get("formato_versao") == 2, "log_buscas.json precisa estar no esquema v2"
    lg["execucoes"].append({
        "data": hoje(), "canal": canal, "camada": camada, "uf": uf, "municipio": municipio,
        "ibge": ibge, "nivel": nivel, "strings": strings, "n_resultados": n_resultados,
        "resultados": resultados[:600], "decisao": decisao,
        "fonte_suspensa_defeso": bool(fonte_suspensa_defeso), "executor": EXECUTOR,
        "hash_evidencia": hash_evidencia})
    gravar("log_buscas.json", lg)


def eh_suspensao_defeso(html: str) -> bool:
    """Heurística declarada (§3.1): aviso de período eleitoral, ou página institucional
    esvaziada. Só rotula; nunca infere conteúdo."""
    t = html.lower()
    return any(k in t for k in ("período eleitoral", "periodo eleitoral", "legislação eleitoral",
                                "lei 9.504", "lei nº 9.504", "vedação eleitoral", "defeso eleitoral"))


def registrar_lacuna(fonte: str, motivo: str, canal: str, camada: int, strings=None, **kw):
    """Fonte não coletada → entrada de log com decisão 'erro' (ou 'fonte suspensa (defeso)')."""
    dec = "fonte suspensa (defeso)" if kw.pop("suspensa", False) else "erro"
    log_busca(canal, camada, strings or [fonte], dec, resultados=f"{fonte}: {motivo}",
              fonte_suspensa_defeso=(dec.startswith("fonte")), **kw)
    print(f"  [lacuna declarada] {fonte}: {motivo}")


# ── livro de fontes consultadas (por município) ─────────────────────────────

def referencia_ibge():
    ref = ler("municipios_ibge_referencia.json")
    por_cod = {str(r["codigo_ibge"]).zfill(7): r for r in ref}
    por_nome = {(r["nome"], r["uf"]): str(r["codigo_ibge"]).zfill(7) for r in ref}
    return por_cod, por_nome


def marcar_fonte_consultada(ibges, fonte: str, nivel: str, resultado: str = "consultada"):
    """Registra que `fonte` foi consultada para cada município em `ibges`, com o nível
    que essa fonte confere (§2.2). Nunca rebaixa um nível já alcançado."""
    assert nivel in NIVEIS
    livro = ler("fontes_consultadas.json", {"_governanca": "Livro de fontes consultadas por município "
                                            "(v2.2.4). Insumo do nível de verificação derivado por "
                                            "recalcular_mare.py; nunca lido pelo cálculo da nota.",
                                            "municipios": {}})
    ordem = {n: i for i, n in enumerate(NIVEIS)}
    for cod in ibges:
        cod = str(cod).zfill(7)
        m = livro["municipios"].setdefault(cod, {"nivel_verificacao": "nao_verificado",
                                                  "ultima_verificacao": None, "fontes": []})
        m["fontes"].append({"fonte": fonte, "data": hoje(), "resultado": resultado})
        m["fontes"] = m["fontes"][-12:]
        if ordem[nivel] > ordem[m["nivel_verificacao"]]:
            m["nivel_verificacao"] = nivel
        m["ultima_verificacao"] = hoje()
    gravar("fontes_consultadas.json", livro)


def marcar_fato_municipal(ibge, campo: str, valor):
    """Fatos binários por município (§3.3): decreto_reconhecido, decreto_homologado,
    plano_declarado_munic, plano_declarado_icm."""
    assert campo in ("decreto_reconhecido", "decreto_homologado", "plano_declarado_munic", "plano_declarado_icm")
    livro = ler("fontes_consultadas.json", {"_governanca": "", "municipios": {}})
    m = livro["municipios"].setdefault(str(ibge).zfill(7), {"nivel_verificacao": "nao_verificado",
                                                             "ultima_verificacao": None, "fontes": []})
    m[campo] = valor
    gravar("fontes_consultadas.json", livro)


# ── autoteste ────────────────────────────────────────────────────────────────

def rodar_autoteste(testes: dict) -> int:
    """`testes` = {nome: callable→bool}. Imprime ✓/✗ e devolve o código de saída."""
    falhas = 0
    for nome, fn in testes.items():
        try:
            ok = bool(fn())
        except Exception as e:  # noqa: BLE001
            ok = False
            print(f"    ({type(e).__name__}: {e})")
        print(("  ✓ " if ok else "  ✗ ") + nome)
        falhas += (not ok)
    print("✓ AUTOTESTE OK" if not falhas else f"✗ AUTOTESTE: {falhas} falha(s)")
    return 1 if falhas else 0
