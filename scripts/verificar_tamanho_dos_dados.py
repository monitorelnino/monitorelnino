#!/usr/bin/env python3
"""
scripts/verificar_tamanho_dos_dados.py — arquivo versionado não incha sem ninguém ver
======================================================================================
Item 4 da conferência da central de 06/10/2026: "portão que reprova arquivo versionado > 50 MB e
crescimento de mais de 20% numa execução".

O QUE ACONTECEU
----------------
`data/pistas_imprensa.json` foi de **28 MB** para **187,53 MB** em meia hora, passou do limite de
100 MB do GitHub (GH001) e derrubou o push de **todo elo que grava esse arquivo**. A causa foi uma
união que, sem base comum, concatenava em vez de unir — e o arquivo dobrava a cada reaplicação:
28, 56, 112, 187.

Nada disso precisava ter chegado ao push. Um arquivo que dobra é visível na primeira duplicação, e
é isso que este portão vê.

AS DUAS RÉGUAS
---------------
  **Teto absoluto, 50 MB.** Metade do limite do GitHub, de propósito: o repositório tem de avisar
  antes de o GitHub recusar, porque quando o GitHub recusa a coleta da noite já está perdida.

  **Crescimento, 20% numa execução.** Dado que cresce por rotina cresce devagar — o log de buscas
  ganha alguns por cento por noite. Vinte por cento num passo é duplicação, não coleta.
  Exceção medida (central, 30/10/2026): arquivo JSON de registros que passa de 20% mas cujos
  registros únicos crescem ao menos tanto quanto os bytes, numa lista sem repetição, é leitura
  nova (backfill do juiz), não duplicação. Arquivo concatenado a si mesmo não passa: os únicos não
  crescem.

O que o portão NÃO cobra: o que está no `.gitignore`. `evidencias/` tem 4,1 GB e não é versionado;
cobrar tamanho dele seria cobrar o que o git não carrega.

USO
  python3 scripts/verificar_tamanho_dos_dados.py --autoteste
  python3 scripts/verificar_tamanho_dos_dados.py
  python3 scripts/verificar_tamanho_dos_dados.py --contra HEAD~1
"""
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent

TETO_MB = 50.0
CRESCIMENTO_MAXIMO = 0.20
# Abaixo deste tamanho, variação percentual não diz nada: um arquivo de 2 KB que vira 4 KB dobrou,
# e isso é rotina. A régua do crescimento só vale onde o tamanho já importa.
PISO_PARA_CRESCIMENTO_MB = 1.0


def mb(bytes_: int) -> float:
    """Bytes em MB, com uma casa. Função pura."""
    return round((bytes_ or 0) / 1048576, 1)


def acima_do_teto(tamanhos: dict, teto_mb: float = TETO_MB) -> list:
    """Os arquivos acima do teto. Função pura. `tamanhos` é {caminho: bytes}."""
    return sorted(f"{c}: {mb(b)} MB, acima do teto de {teto_mb} MB"
                  for c, b in (tamanhos or {}).items() if mb(b) > teto_mb)


def _listas(obj) -> dict:
    """{caminho: lista de registros} de um JSON: a lista da raiz ou as listas de topo do objeto."""
    if isinstance(obj, list):
        return {"": obj}
    if isinstance(obj, dict):
        return {k: v for k, v in obj.items() if isinstance(v, list)}
    return {}


def _unicos(lista) -> int:
    import json
    return len({json.dumps(x, sort_keys=True, ensure_ascii=False) for x in lista})


def novidade_real(antes_obj, agora_obj, taxa_bytes: float) -> bool:
    """Função pura. Há uma lista sem repetição cujos registros únicos cresceram ao menos `taxa_bytes`?"""
    antes_l = _listas(antes_obj)
    for nome, lista in _listas(agora_obj).items():
        base = _unicos(antes_l.get(nome) or [])
        unicos = _unicos(lista)
        if base and unicos == len(lista) and (unicos - base) / base >= taxa_bytes:
            return True
    return False


def cresceu_demais(antes: dict, agora: dict, limite: float = CRESCIMENTO_MAXIMO,
                   piso_mb: float = PISO_PARA_CRESCIMENTO_MB, legitimo=None) -> list:
    """Os arquivos que cresceram além do limite. Função pura.

    Arquivo novo não entra: ele não "cresceu", ele nasceu — e um arquivo novo grande é problema do
    teto, que já o pega. `legitimo(caminho, taxa)` (opcional) absolve o crescimento que traz
    registros únicos novos (ver `novidade_real`).
    """
    fora = []
    for caminho, depois in sorted((agora or {}).items()):
        antes_b = (antes or {}).get(caminho)
        if not antes_b or mb(antes_b) < piso_mb:
            continue
        if depois <= antes_b:
            continue
        taxa = (depois - antes_b) / antes_b
        if taxa > limite and not (legitimo and legitimo(caminho, taxa)):
            fora.append(f"{caminho}: {mb(antes_b)} MB → {mb(depois)} MB "
                        f"(+{round(taxa * 100)}% numa execução)")
    return fora


def _git(*args):
    return subprocess.run(["git", *args], cwd=str(RAIZ), capture_output=True, text=True,
                          timeout=120)


def tamanhos_em(revisao: str) -> dict:
    """{caminho: bytes} dos arquivos versionados naquela revisão. Lê o git; não escreve."""
    saida = _git("ls-tree", "-r", "-l", revisao).stdout or ""
    fora = {}
    for linha in saida.splitlines():
        partes = linha.split(None, 4)
        if len(partes) == 5 and partes[3].isdigit():
            fora[partes[4].strip()] = int(partes[3])
    return fora


def _json_em(revisao: str, caminho: str):
    """O JSON do arquivo naquela revisão, ou None se não for JSON legível. Lê o git; não escreve."""
    import json
    try:
        return json.loads(_git("show", f"{revisao}:{caminho}").stdout)
    except ValueError:
        return None


def _autoteste() -> int:
    falhas, contados = [], []

    from _casos import ok_de
    ok = ok_de(falhas, contados)

    MB = 1048576
    ok("bytes viram MB com uma casa", mb(28 * MB) == 28.0)
    ok("zero é zero", mb(0) == 0.0)

    ok("o arquivo de 187 MB seria barrado",
       acima_do_teto({"data/pistas_imprensa.json": 187 * MB}) != [])
    ok("o arquivo de 28 MB passa", acima_do_teto({"data/pistas_imprensa.json": 28 * MB}) == [])
    ok("a mensagem diz o tamanho",
       "187.0 MB" in acima_do_teto({"x.json": 187 * MB})[0])
    ok("árvore vazia não acusa nada", acima_do_teto({}) == [])

    # A primeira duplicação: 28 → 56. É aqui que o portão tinha de pegar, e pega.
    ok("dobrar é barrado",
       cresceu_demais({"a.json": 28 * MB}, {"a.json": 56 * MB}) != [])
    ok("crescer 10% passa",
       cresceu_demais({"a.json": 28 * MB}, {"a.json": int(30.8 * MB)}) == [])
    ok("crescer 25% é barrado",
       cresceu_demais({"a.json": 28 * MB}, {"a.json": 35 * MB}) != [])
    ok("encolher nunca é barrado",
       cresceu_demais({"a.json": 28 * MB}, {"a.json": 10 * MB}) == [])
    ok("arquivo novo não conta como crescimento",
       cresceu_demais({}, {"novo.json": 60 * MB}) == [])
    ok("arquivo pequeno que dobra não conta",
       cresceu_demais({"a.json": 2000}, {"a.json": 9000}) == [])
    ok("a mensagem diz de quanto para quanto",
       "28.0 MB → 56.0 MB" in cresceu_demais({"a.json": 28 * MB}, {"a.json": 56 * MB})[0])
    ok("sem revisão anterior, nada é acusado", cresceu_demais({}, {}) == [])

    # Backfill legítimo: 4.951 → 9.221 registros únicos (+86%) com os bytes em +74% passa;
    # o mesmo arquivo concatenado a si mesmo (únicos parados) é barrado.
    reg = lambda a, b: [{"ibge": str(i), "criterios": "x" * 20} for i in range(a, b)]
    ok("registros únicos novos absolvem o crescimento",
       novidade_real({"decisoes": reg(0, 4951)}, {"decisoes": reg(0, 9221)}, 0.74))
    ok("arquivo concatenado a si mesmo não é novidade",
       not novidade_real({"decisoes": reg(0, 4951)}, {"decisoes": reg(0, 4951) * 2}, 0.74))
    ok("únicos que crescem menos que os bytes não absolvem",
       not novidade_real({"decisoes": reg(0, 4951)}, {"decisoes": reg(0, 6000)}, 0.74))
    ok("lista de raiz também conta", novidade_real(reg(0, 10), reg(0, 40), 0.5))
    ok("cresceu_demais respeita o veredito de legitimidade",
       cresceu_demais({"a.json": 28 * MB}, {"a.json": 56 * MB}, legitimo=lambda c, t: True) == [])

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "main", "_git", "tamanhos_em", "_json_em"):
            continue
        if getattr(obj, "__module__", None) not in (__name__, None):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não chamam git nem escrevem",
       not ({"subprocess", "write_text", "read_text"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main(argv: list) -> int:
    if "--autoteste" in argv:
        return _autoteste()
    if _autoteste() != 0:   # 16/10/2026: o autoteste roda antes da conferência, num comando só
        return 1
    agora = tamanhos_em("HEAD")
    if not agora:
        print("✗ TAMANHO DOS DADOS: não consegui ler a árvore do git")
        return 1
    problemas = acima_do_teto(agora)

    contra = argv[argv.index("--contra") + 1] if "--contra" in argv else "HEAD~1"
    antes = tamanhos_em(contra)
    if antes:
        def legitimo(caminho, taxa):
            return caminho.endswith(".json") and novidade_real(
                _json_em(contra, caminho), _json_em("HEAD", caminho), taxa)
        problemas += cresceu_demais(antes, agora, legitimo=legitimo)

    if problemas:
        print(f"✗ TAMANHO DOS DADOS: {len(problemas)} problema(s):")
        for x in problemas:
            print("   - " + x)
        print(f"   Teto de {TETO_MB} MB (metade do limite do GitHub) e crescimento de "
              f"{round(CRESCIMENTO_MAXIMO * 100)}% numa execução. Arquivo que dobra é duplicação, "
              f"não coleta — e quando o GitHub recusa, a coleta da noite já se perdeu.")
        return 1
    maior = max(agora.items(), key=lambda kv: kv[1]) if agora else ("—", 0)
    print(f"✓ TAMANHO DOS DADOS OK — {len(agora)} arquivo(s) versionado(s); o maior é "
          f"{maior[0]} com {mb(maior[1])} MB.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
