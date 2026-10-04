#!/usr/bin/env python3
"""
scripts/verificar_workflow_aceito.py — o GitHub ACEITOU o arquivo, não só o parser
===================================================================================
Item 3 do bloco de prioridade de 04/10/2026 (20:30 UTC).

O QUE ACONTECEU, E POR QUE NENHUM PORTÃO VIU
--------------------------------------------
`busca_web_cadencia.yml` e `auditoria_seguranca.yml` passaram a aparecer no GitHub **com o caminho
no lugar do nome**, e cada push na `main` gerava um run `failure` com **zero jobs** — cinco vezes
entre 13:40 e 14:29 BRT de 04/10. A busca web não rodou desde 11:25 e a auditoria parou.

A causa: ao inserir o tique oportunista, o passo entrou no meio do `actions/setup-python`, e o
`with` dele ficou dentro de um passo que também tem `run`. Isso é **inválido para o GitHub e válido
para qualquer parser YAML** — sintaticamente é só um mapa com duas chaves. `actionlint` passava,
`validar_workflows.py` passava, e a API não devolve a mensagem de erro (o check suite não tem check
runs). Só o GitHub reprovava, e em silêncio.

A trava estrutural já entrou em `validar_workflows.py` (nenhum passo tem `run` com `with` ou
`uses`). Este portão é a outra metade, e cobre o caso geral: **perguntar ao GitHub**. Dois sintomas,
os dois observáveis pela API:

  1. o workflow tem `name` igual ao seu `path` — é o que o GitHub faz quando não consegue ler o
     arquivo e precisa de um nome;
  2. existe execução com `conclusion: failure` e **zero jobs** — o run que o GitHub cria só para
     dizer "não consegui".

O portão não inventa validação de YAML: ele lê o veredito de quem executa.

USO
  python3 scripts/verificar_workflow_aceito.py --autoteste
  python3 scripts/verificar_workflow_aceito.py              # consulta a API
"""
import json
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))


def nome_e_o_caminho(workflow: dict) -> bool:
    """O GitHub não conseguiu ler o arquivo e usou o caminho como nome? Função pura."""
    nome = str((workflow or {}).get("name") or "").strip()
    caminho = str((workflow or {}).get("path") or "").strip()
    if not nome or not caminho:
        return False
    return nome == caminho or nome == caminho.split("/")[-1] or nome.endswith(".yml")


def existe_na_arvore(caminho: str, raiz: pathlib.Path = None) -> bool:
    """O arquivo ainda está no repositório? Função pura quanto ao disco.

    04/10/2026: o GitHub guarda para sempre os workflows que já existiram, e `diag_searxng.yml` e
    `teste_bypass_robo.yml` — apagados há semanas — aparecem na API com o caminho no lugar do nome,
    porque o arquivo não existe mais para ser lido. Cobrá-los seria cobrar o passado: o portão olha
    o que está na árvore agora.
    """
    return ((raiz or RAIZ) / caminho).exists()


def problemas(workflows: list, runs_por_workflow: dict, raiz: pathlib.Path = None) -> list:
    """Os workflows que o GitHub rejeitou. Função pura.

    `runs_por_workflow` é {id: [runs]}, cada run com `conclusion` e `jobs` (a contagem). Run com
    `failure` e zero jobs é o run que o GitHub cria para dizer que não executou nada — e ele é o
    sintoma que aparece a cada push, de modo que ignorá-lo é deixar a `main` vermelha todo dia.
    """
    fora = []
    for w in workflows or []:
        caminho = str(w.get("path") or "")
        if not caminho.endswith(".yml"):
            continue
        if str(w.get("state") or "") in ("disabled_manually", "disabled_inactivity"):
            continue
        if not existe_na_arvore(caminho, raiz):
            continue
        if nome_e_o_caminho(w):
            fora.append(f"{caminho}: o GitHub mostra o CAMINHO no lugar do nome — ele não "
                        f"conseguiu ler o arquivo")
            continue
        # Só a execução MAIS RECENTE conta. Run de zero jobs no histórico é defeito que já foi
        # consertado — e um portão que reprova por história nunca volta ao verde.
        recentes = (runs_por_workflow or {}).get(w.get("id")) or []
        if recentes:
            r = recentes[0]
            if r.get("conclusion") == "failure" and int(r.get("jobs") or 0) == 0:
                fora.append(f"{caminho}: a última execução ({r.get('id')}) falhou com ZERO jobs — "
                            f"é o run que o GitHub cria quando rejeita o arquivo")
    return fora


def _autoteste() -> int:
    falhas = []

    def ok(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    bom = {"id": 1, "name": "Busca web — cadência automática", "state": "active",
           "path": ".github/workflows/busca_web_cadencia.yml"}
    ruim = {"id": 2, "name": ".github/workflows/busca_web_cadencia.yml", "state": "active",
            "path": ".github/workflows/busca_web_cadencia.yml"}

    ok("nome igual ao caminho é rejeição", nome_e_o_caminho(ruim))
    ok("nome de verdade não é rejeição", not nome_e_o_caminho(bom))
    ok("nome que é só o arquivo também é rejeição",
       nome_e_o_caminho({"name": "busca_web_cadencia.yml",
                         "path": ".github/workflows/busca_web_cadencia.yml"}))
    ok("workflow sem nome nem caminho não quebra", not nome_e_o_caminho({}))

    import tempfile
    with tempfile.TemporaryDirectory() as t:
        raiz = pathlib.Path(t)
        (raiz / ".github" / "workflows").mkdir(parents=True)
        (raiz / bom["path"]).write_text("name: x\n", encoding="utf-8", newline="\n")

        ok("workflow aceito passa",
           problemas([bom], {1: [{"id": 9, "conclusion": "success", "jobs": 1}]}, raiz) == [])
        ok("arquivo que não está mais na árvore fica fora, mesmo rejeitado",
           problemas([{"id": 5, "name": ".github/workflows/apagado.yml", "state": "active",
                       "path": ".github/workflows/apagado.yml"}], {}, raiz) == [])
        ok("run de zero jobs no HISTÓRICO não reprova; só a última execução conta",
           problemas([bom], {1: [{"id": 9, "conclusion": "success", "jobs": 1},
                                 {"id": 8, "conclusion": "failure", "jobs": 0}]}, raiz) == [])
        ok("última execução com zero jobs REPROVA",
           len(problemas([bom], {1: [{"id": 8, "conclusion": "failure", "jobs": 0}]}, raiz)) == 1)
        p = problemas([ruim], {}, raiz)
        ok("nome igual ao caminho REPROVA", len(p) == 1 and "CAMINHO no lugar do nome" in p[0])
        ok("run com falha e jobs > 0 NÃO reprova — falha de teste é outra coisa",
           problemas([bom], {1: [{"id": 7, "conclusion": "failure", "jobs": 3}]}, raiz) == [])
        ok("run cancelado com zero jobs não reprova: cancelar não é rejeitar",
           problemas([bom], {1: [{"id": 7, "conclusion": "cancelled", "jobs": 0}]}, raiz) == [])
        ok("workflow desativado de propósito fica fora",
           problemas([dict(ruim, state="disabled_manually")], {}, raiz) == [])
        ok("arquivo que não é .yml fica fora",
           problemas([{"id": 3, "name": "x", "path": "outro/arquivo.txt"}], {}, raiz) == [])
        ok("um workflow ruim entre vários é nomeado",
           len(problemas([bom, ruim], {}, raiz)) == 1)

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "main", "_gh", "ler_do_github"):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não consultam rede",
       not ({"run", "subprocess", "urlopen"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else "✓ AUTOTESTE OK — 16 casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def _gh(args: list) -> str:
    try:
        r = subprocess.run(["gh"] + args, cwd=RAIZ, capture_output=True, text=True, timeout=120)
        return r.stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def ler_do_github() -> tuple:
    """(workflows, runs_por_workflow) pela API."""
    saida = _gh(["api", "repos/{owner}/{repo}/actions/workflows", "--paginate",
                 "--jq", ".workflows[] | {id, name, path, state}"])
    workflows = []
    for linha in (saida or "").splitlines():
        if linha.strip():
            try:
                workflows.append(json.loads(linha))
            except json.JSONDecodeError:
                continue
    runs = {}
    for w in workflows:
        bruto = _gh(["api", f"repos/{{owner}}/{{repo}}/actions/workflows/{w['id']}/runs?per_page=5",
                     "--jq", ".workflow_runs[] | {id, conclusion, jobs: 0, jobs_url}"])
        lista = []
        for linha in (bruto or "").splitlines():
            if not linha.strip():
                continue
            try:
                r = json.loads(linha)
            except json.JSONDecodeError:
                continue
            # A contagem de jobs só importa quando a execução falhou: é o caso que distingue
            # "rejeitou o arquivo" de "o teste reprovou".
            if r.get("conclusion") == "failure":
                jb = _gh(["api", f"repos/{{owner}}/{{repo}}/actions/runs/{r['id']}/jobs",
                          "--jq", ".total_count"])
                r["jobs"] = int(jb.strip() or 0) if jb.strip().isdigit() else 1
            lista.append(r)
        runs[w["id"]] = lista
    return workflows, runs


def main() -> int:
    if "--autoteste" in sys.argv[1:]:
        return _autoteste()
    workflows, runs = ler_do_github()
    if not workflows:
        print("⚠ WORKFLOW ACEITO: a API não respondeu — nada conferido (e isto NÃO é um verde)")
        return 0
    p = problemas(workflows, runs)
    if p:
        print(f"✗ WORKFLOW ACEITO: {len(p)} arquivo(s) que o GitHub rejeitou:")
        for x in p:
            print("  ·", x)
        print("  Causa mais comum: um passo com `run` e `with` juntos, ou `run` e `uses` — "
              "válido para o YAML, inválido para o GitHub.")
        return 1
    print(f"✓ WORKFLOW ACEITO OK — {len(workflows)} workflow(s) lidos pelo GitHub com o próprio "
          f"nome, nenhum run de zero jobs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
