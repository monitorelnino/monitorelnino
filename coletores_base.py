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
import hashlib, json, os, pathlib, re, sys, urllib.error, urllib.parse, urllib.request
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


# ---------------------------------------------------------------------------------
# Detector de página de defeso eleitoral (PR-N0 §1.5, 06/09/2026). Sítios estaduais e
# municipais que respondem com aviso de "período eleitoral" NÃO são "nada localizado":
# são fonte suspensa (defeso). O detector roda dentro de buscar(); a marcação é registrada
# em data/calendario/fontes_suspensas.json e propagada ao log_busca() da mesma URL.
# ---------------------------------------------------------------------------------
import unicodedata as _ud

PADROES_DEFESO = [
    r"periodo eleitoral", r"conduta vedada", r"legislacao eleitoral", r"lei 9\.?504", r"lei n[oº.]* ?9\.?504",
    r"conteudo temporariamente indisponivel(?=[\s\S]{0,400}(eleic|9\.?504))",   # só com contexto eleitoral: manutenção não é defeso
    r"indisponivel[^.]{0,80}eleic", r"defeso eleitoral", r"restricoes eleitorais",
    r"suspens[ao][^.]{0,80}legislacao eleitoral", r"em razao d[ao] (periodo|calendario) eleitoral", r"vedacoes eleitorais",
    r"\(defeso\)", r"edicao (de )?defeso", r"versao (de )?defeso",   # §9 (07/09/2026): painéis em "edição de defeso" (ex.: Painel das Arboviroses do MS)
]
_RE_DEFESO = [re.compile(p) for p in PADROES_DEFESO]
_SUSPENSAS_SESSAO = {}   # url → padrão que casou (nesta execução)


def _plano(t: str) -> str:
    return "".join(c for c in _ud.normalize("NFD", str(t or "").lower()) if _ud.category(c) != "Mn")


def detectar_defeso(texto: str) -> str | None:
    """Padrão que casou (sem acento) ou None. Função pura; só corpos HTML/texto pequenos interessam."""
    if not texto:
        return None
    t = _plano(texto[:200000])
    for rx in _RE_DEFESO:
        m = rx.search(t)
        if m:
            return m.group(0)
    return None


def _dominio_publico(url: str) -> bool:
    """Sítio estadual/municipal (não API de dados): .gov.br, .leg.br, .jus.br ou domínio brasileiro de prefeitura."""
    h = (urllib.parse.urlparse(url).netloc or "").lower()
    if any(h.startswith(x) or x in h for x in ("api.", "apimsbr", "queridodiario", "dataserver", "geoserver", "gsc.cemaden", "info.dengue", "portaldatransparencia.gov.br", "repositorio.dados.gov.br", "transferegov", "s3.", "amazonaws")):
        return False
    return h.endswith((".gov.br", ".leg.br", ".jus.br", ".def.br", ".mp.br")) or "prefeitura" in h


def setor_da_url(url: str) -> str:
    """§9: setor da fonte suspensa pela URL — saude | financiamento | defesa_civil."""
    u = url.lower()
    if any(x in u for x in ("saude", "sus.gov", "arbovir", "dengue", "vigil", "epidem")): return "saude"
    if any(x in u for x in ("transparencia", "transferegov", "tesouro", "orcament")): return "financiamento"
    return "defesa_civil"


def registrar_fonte_suspensa(url: str, corpo: bytes, padrao: str) -> None:
    """Grava a detecção (hash + 500 primeiras letras) e a contagem por UF em data/calendario/fontes_suspensas.json."""
    import datetime as _dt
    h = hashlib.sha256(corpo).hexdigest()
    (DATA / "calendario").mkdir(parents=True, exist_ok=True)
    p = DATA / "calendario" / "fontes_suspensas.json"
    d = json.load(open(p, encoding="utf-8")) if p.exists() else {"_governanca": "Fontes oficiais que responderam com página de período eleitoral (detector de PR-N0 §1.5). Nunca 'nada localizado': fonte suspensa (defeso). A reabertura é o flag voltando a false, com data.", "fontes": {}}
    hoje = _dt.date.today().isoformat()
    f = d["fontes"].setdefault(url, {"primeira_deteccao": hoje, "ultima_deteccao": hoje, "padrao": padrao, "hash": h, "amostra": corpo[:2000].decode("utf-8", "replace")[:500], "suspensa": True, "setor": setor_da_url(url)})
    f.update({"ultima_deteccao": hoje, "padrao": padrao, "hash": h, "suspensa": True, "setor": f.get("setor") or setor_da_url(url)})
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1); open(p, "a").write("\n")
    (EVID).mkdir(parents=True, exist_ok=True)
    (EVID / f"defeso_{h[:16]}.txt").write_text(corpo[:20000].decode("utf-8", "replace"), encoding="utf-8")


def buscar(url: str, timeout: int = 40) -> bytes:
    """GET simples com User-Agent do projeto. Levanta a exceção — quem chama decide
    se vira lacuna declarada (regra 1) ou aborta. Em sítio público (não API), testa o corpo
    contra os padrões de página de defeso e registra a fonte como suspensa (PR-N0 §1.5)."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        corpo = r.read()
        ct = (r.headers.get("Content-Type") or "").lower()
    if _dominio_publico(url) and ("html" in ct or "text" in ct or corpo[:200].lstrip().lower().startswith(b"<!doctype") or b"<html" in corpo[:2000].lower()):
        pad = detectar_defeso(corpo[:200000].decode("utf-8", "replace")) or ("defeso" if "defeso" in url.lower() else None)
        if pad:
            _SUSPENSAS_SESSAO[url] = pad
            try:
                registrar_fonte_suspensa(url, corpo, pad)
            except Exception:  # noqa: BLE001
                pass
    return corpo


def fonte_esta_suspensa(urls) -> bool:
    """True se alguma URL desta execução casou o detector de defeso."""
    return any(u in _SUSPENSAS_SESSAO for u in (urls or []))


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
    assert decisao.split(" ")[0] in ("registro", "pista", "nada", "fonte", "erro", "acesso", "sem_cobertura_qd", "coberto_sem_mencao", "com_excerto"), decisao   # "acesso recusado" (§10.1), decisões do §1.2
    if decisao.startswith("nada localizado"):
        assert nivel == "municipal_completo", "regra §2.1: 'nada localizado' exige bateria municipal completa"
    lg = ler("log_buscas.json")
    assert lg and lg.get("formato_versao") == 2, "log_buscas.json precisa estar no esquema v2"
    lg["execucoes"].append({
        "data": hoje(), "canal": canal, "camada": camada, "uf": uf, "municipio": municipio,
        "ibge": ibge, "nivel": nivel, "strings": strings, "n_resultados": n_resultados,
        "resultados": resultados[:600], "decisao": decisao,
        "fonte_suspensa_defeso": bool(fonte_suspensa_defeso) or fonte_esta_suspensa(strings), "executor": EXECUTOR,
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
