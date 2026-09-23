#!/usr/bin/env python3
"""
scripts/reavaliar_fontes_suspensas.py — reavalia as suspensões por defeso já registradas (§182)
================================================================================================
Por que existe. Até 23/09/2026 o detector de defeso (PR-N0 §1.5) rodava sobre o HTML cru e casava em
ATRIBUTO: `alt="banner periodo eleitoral"` de uma imagem marcou o portal de saúde do PI como
suspenso, com a página no ar e servindo conteúdo. O número de fontes suspensas é PUBLICADO (o PDF do
índice imprime "Fontes suspensas por defeso na última rodada: N"), então o falso positivo não fica
interno — sai no material público. O §182 restringiu a detecção ao texto DECLARATIVO da página
(texto visível, `<title>` e `<meta name="description">`); este script aplica a régua nova ao que já
estava registrado.

A REGRA QUE A PRIMEIRA VERSÃO DESTE SCRIPT ERRAVA. A evidência preservada é **truncada** nas
primeiras 20 mil letras do corpo servido. Numa página em que o aviso aparece depois desse corte —
foi o caso de `defesacivil.pr.gov.br` e `saude.pr.gov.br`, cujo aviso "conteúdo indisponível devido
ao período eleitoral" está mais adiante no HTML —, não achar o padrão na evidência **não é prova de
que a fonte voltou**: é inconclusivo. Reabrir por isso republicaria como no ar uma fonte suspensa.
Então:

  · casou na evidência                        → segue suspensa (procedência: evidência preservada);
  · não casou e a evidência está INTEIRA       → reaberta (procedência: evidência preservada);
  · não casou e a evidência está TRUNCADA      → inconclusivo: só decide com nova busca;
  · sem evidência em disco                     → inconclusivo: só decide com nova busca.

Inconclusivo NUNCA reabre sozinho. Com `--refazer-busca`, o script vai à fonte, decide pelo corpo
atual e grava a procedência da decisão. Falha de rede mantém o estado e fica registrada — o §170
vale aqui também: ausência de resposta não é prova de nada.

  python3 scripts/reavaliar_fontes_suspensas.py --dry-run
  python3 scripts/reavaliar_fontes_suspensas.py --refazer-busca
  python3 scripts/reavaliar_fontes_suspensas.py --autoteste
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from coletores_base import EVID, buscar, classificar_defeso, detectar_defeso, ler, gravar, hoje  # noqa: E402

ARQUIVO = "calendario/fontes_suspensas.json"
TETO_EVIDENCIA = 20000          # o mesmo corte que registrar_fonte_suspensa() aplica ao gravar
MARGEM_TRUNCAMENTO = 1000       # decodificar bytes→texto encurta: perto do teto, presumir truncada


def evidencia_de(registro: dict):
    """(texto, truncada) da evidência preservada no momento da detecção, ou (None, None)."""
    h = (registro.get("hash") or "")[:16]
    if not h:
        return None, None
    p = EVID / f"defeso_{h}.txt"
    if not p.exists():
        return None, None
    t = p.read_text(encoding="utf-8", errors="replace")
    return t, len(t) >= TETO_EVIDENCIA - MARGEM_TRUNCAMENTO


def reavaliar(fontes: dict, buscar_fn=None) -> dict:
    """Aplica a régua do §182. Muda `fontes` em memória; quem chama grava.
    Devolve {"mantidas": [...], "reabertas": [...], "inconclusivas": [...], "sem_resposta": [...]}."""
    r = {"mantidas": [], "reabertas": [], "inconclusivas": [], "sem_resposta": []}
    for url, reg in fontes.items():
        texto, truncada = evidencia_de(reg)
        padrao, escopo = classificar_defeso(texto) if texto else (None, None)
        if escopo != "sitio":
            padrao = None           # §182: só o sítio fora do ar fecha o canal do Monitor
        procedencia = "evidência preservada"
        if padrao is None and (texto is None or truncada):
            # inconclusivo pela evidência: só a fonte resolve
            if buscar_fn is None:
                reg["reavaliada_em"] = hoje()
                reg["reavaliacao"] = ("§182: inconclusivo pela evidência ("
                                      + ("truncada nas 20 mil primeiras letras" if texto else "ausente em disco")
                                      + "); estado mantido até nova busca")
                r["inconclusivas"].append(url)
                continue
            try:
                corpo = buscar_fn(url, timeout=30)
            except Exception as e:  # noqa: BLE001
                reg["reavaliada_em"] = hoje()
                reg["reavaliacao"] = (f"§182: nova busca não obteve resposta ({type(e).__name__}); "
                                      "estado mantido — ausência de resposta não é prova (§170)")
                r["sem_resposta"].append(url)
                continue
            padrao, escopo = classificar_defeso(corpo.decode("utf-8", "replace"))
            if escopo != "sitio":
                padrao = None
            procedencia = f"nova busca em {hoje()}"
        reg["reavaliada_em"] = hoje()
        reg["procedencia_da_reavaliacao"] = procedencia
        reg["escopo_declarado"] = escopo      # §182: sitio | noticias | None
        if padrao:
            reg["padrao"] = padrao
            reg["suspensa"] = True
            reg["reavaliacao"] = f"§182: continua declarando suspensão ({procedencia})"
            r["mantidas"].append(url)
        else:
            reg["suspensa"] = False
            reg["reavaliacao"] = (("§182: o sítio declara suspensão de NOTÍCIAS institucionais, não do "
                                   "conteúdo — o canal de documento segue aberto"
                                   if escopo == "noticias" else
                                   "§182: o padrão casava fora do texto declarativo (atributo de imagem, "
                                   "classe de CSS ou endereço de link) — a página não declara suspensão")
                                  + f" ({procedencia})")
            r["reabertas"].append(url)
    return r


def autoteste() -> int:
    """As quatro situações da régua, sem rede e sem tocar no arquivo do projeto."""
    import tempfile
    falhas = []
    AVISO = "<html><head><title>Suspensão Temporária | Período Eleitoral 2026</title></head></html>"
    SO_ALT = '<html><body><img alt="banner periodo eleitoral" src="/b.jpg"><p>Boletim publicado.</p></body></html>'
    global EVID
    real = EVID
    with tempfile.TemporaryDirectory() as d:
        try:
            EVID = Path(d)
            (EVID / ("defeso_" + "a" * 16 + ".txt")).write_text(AVISO, encoding="utf-8", newline="\n")
            (EVID / ("defeso_" + "b" * 16 + ".txt")).write_text(SO_ALT, encoding="utf-8", newline="\n")
            # evidência truncada: sem o padrão, mas no teto — inconclusiva por construção
            (EVID / ("defeso_" + "c" * 16 + ".txt")).write_text("x" * TETO_EVIDENCIA, encoding="utf-8", newline="\n")

            fontes = {"https://aviso.gov.br/": {"hash": "a" * 64, "suspensa": True},
                      "https://so-alt.gov.br/": {"hash": "b" * 64, "suspensa": True},
                      "https://truncada.gov.br/": {"hash": "c" * 64, "suspensa": True},
                      "https://sem-evidencia.gov.br/": {"hash": "d" * 64, "suspensa": True}}
            r = reavaliar(dict_copia := {k: dict(v) for k, v in fontes.items()})
            if r["mantidas"] != ["https://aviso.gov.br/"]:
                falhas.append(f"aviso no título tinha de ser mantido: {r['mantidas']}")
            if r["reabertas"] != ["https://so-alt.gov.br/"]:
                falhas.append(f"só o alt de imagem tinha de reabrir: {r['reabertas']}")
            if sorted(r["inconclusivas"]) != ["https://sem-evidencia.gov.br/", "https://truncada.gov.br/"]:
                falhas.append(f"truncada e sem evidência tinham de ficar inconclusivas: {r['inconclusivas']}")
            if dict_copia["https://truncada.gov.br/"]["suspensa"] is not True:
                falhas.append("inconclusivo NÃO pode reabrir sozinho — é o defeito que este teste tranca")

            # com nova busca: a fonte decide, nos dois sentidos, e falha de rede mantém o estado
            respostas = {"https://truncada.gov.br/": AVISO.encode(),
                         "https://sem-evidencia.gov.br/": SO_ALT.encode()}

            def buscar_fake(url, timeout=0):
                if url not in respostas:
                    raise TimeoutError("sem resposta")
                return respostas[url]

            f2 = {k: dict(v) for k, v in fontes.items()}
            r2 = reavaliar(f2, buscar_fn=buscar_fake)
            if "https://truncada.gov.br/" not in r2["mantidas"]:
                falhas.append("nova busca com aviso tinha de manter a suspensão")
            if "https://sem-evidencia.gov.br/" not in r2["reabertas"]:
                falhas.append("nova busca sem aviso tinha de reabrir")
            if f2["https://sem-evidencia.gov.br/"].get("procedencia_da_reavaliacao", "").startswith("evid"):
                falhas.append("a procedência da decisão por nova busca não foi registrada")

            f3 = {"https://muda.gov.br/": {"hash": "e" * 64, "suspensa": True}}
            r3 = reavaliar(f3, buscar_fn=buscar_fake)
            if r3["sem_resposta"] != ["https://muda.gov.br/"] or f3["https://muda.gov.br/"]["suspensa"] is not True:
                falhas.append("falha de rede tinha de manter o estado e ficar registrada")
        finally:
            EVID = real
    if falhas:
        print("✗ AUTOTESTE (reavaliação de defeso):"); [print("   ", f) for f in falhas]; return 1
    print("✓ AUTOTESTE OK — evidência decide quando dá; truncada e ausente não reabrem; nova busca "
          "decide com procedência; falha de rede mantém o estado.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    dry = "--dry-run" in sys.argv
    d = ler(ARQUIVO)
    if not d:
        print("nenhuma fonte suspensa registrada."); return 0
    r = reavaliar(d["fontes"], buscar_fn=(buscar if "--refazer-busca" in sys.argv else None))
    for url in r["reabertas"]:
        print(f"{'[dry-run] ' if dry else ''}reaberta: {url}")
    for url in r["inconclusivas"]:
        print(f"{'[dry-run] ' if dry else ''}inconclusiva (estado mantido): {url}")
    for url in r["sem_resposta"]:
        print(f"{'[dry-run] ' if dry else ''}sem resposta na nova busca (estado mantido): {url}")
    if not dry:
        gravar(ARQUIVO, d)
    print(f"\n{len(r['mantidas'])} mantida(s), {len(r['reabertas'])} reaberta(s), "
          f"{len(r['inconclusivas'])} inconclusiva(s), {len(r['sem_resposta'])} sem resposta.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
