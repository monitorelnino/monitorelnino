#!/usr/bin/env python3
"""Frescor: o dado coletado chegou ao site?

Itens 2, 3 e 4 do bloco "Frescor do site" (decisão da central, 28/09/2026, tarde). Uma peça
para os três, porque os três fazem a mesma pergunta em lugares diferentes: o resumo do job do
publicador, o vigia pós-deploy, e o mostrador na página.

O QUE ACONTECEU PARA ISTO EXISTIR
---------------------------------
Entre 25/09 e 28/09 o site ficou parado enquanto a coleta seguia rodando. O publicador falhava
duas vezes por dia no portão 12 e ninguém era avisado: cada execução era um quadrado vermelho
numa lista de Actions que ninguém olha de hora em hora. Defeito que se anuncia custa uma
correção; defeito silencioso custa três dias de dado.

**A regra: atraso é falha visível, nunca silêncio.**

GRANULARIDADE, DITA EM VOZ ALTA
-------------------------------
`data/meta.json` guarda `atualizado_em` como **data**, não instante (`28/09/2026`). Então o
limite de "24 h" da decisão é aplicado na granularidade que existe: reprova quando a diferença
passa de **um dia**. Um dia de diferença pode ser uma hora ou quarenta e sete, e por isso não
reprova — reprovar ali daria alarme falso toda manhã seguinte a uma noite que commitou tarde.
Dois dias é atraso de verdade: uma publicação inteira foi perdida.

USO
  python3 scripts/frescor.py --resumo
  python3 scripts/frescor.py --vigia --base https://monitorelnino.com.br [--limite-dias 1]
  python3 scripts/frescor.py --json
  python3 scripts/frescor.py --autoteste
"""
import datetime
import json
import os
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
META = RAIZ / "data" / "meta.json"
SAUDE = RAIZ / "data" / "saude_pipeline.json"
LIMITE_DIAS_PADRAO = 1


def data_br_para_iso(s):
    """'28/09/2026' -> date. Devolve None para vazio ou formato inesperado — nunca levanta:
    frescor é diagnóstico, e diagnóstico que quebra não diagnostica nada."""
    try:
        dd, mm, aa = str(s).strip().split("/")
        return datetime.date(int(aa), int(mm), int(dd))
    except Exception:  # noqa: BLE001
        return None


def data_iso(s):
    """'2026-09-28' ou '2026-09-28T09:18:39' -> date; None se não der."""
    try:
        return datetime.date.fromisoformat(str(s).strip()[:10])
    except Exception:  # noqa: BLE001
        return None


def atraso_em_dias(publicado, coletado):
    """Dias entre o último dado e o que o site declara. None quando falta uma das pontas.

    Negativo é possível e não é erro: o site pode declarar data mais nova que o último commit de
    dado, porque `atualizado_em` acompanha a publicação, não a coleta."""
    if publicado is None or coletado is None:
        return None
    return (coletado - publicado).days


def veredito(publicado, coletado, limite_dias=LIMITE_DIAS_PADRAO):
    """{'estado', 'atraso_dias', 'mensagem'} — o texto é o mesmo em toda superfície."""
    atraso = atraso_em_dias(publicado, coletado)
    if atraso is None:
        return {"estado": "indeterminado", "atraso_dias": None,
                "mensagem": "frescor indeterminado: falta a data de publicação ou a do último dado"}
    if atraso > limite_dias:
        return {"estado": "atrasado", "atraso_dias": atraso,
                "mensagem": (f"dado novo não publicado desde {publicado.strftime('%d/%m/%Y')} "
                             f"({atraso} dia(s) de atraso; último dado em "
                             f"{coletado.strftime('%d/%m/%Y')})")}
    return {"estado": "em_dia", "atraso_dias": atraso,
            "mensagem": (f"site em dia: publicado em {publicado.strftime('%d/%m/%Y')}, último dado "
                         f"em {coletado.strftime('%d/%m/%Y')}")}


def ultima_coleta_local():
    """A data mais recente entre as execuções do painel de saúde e o último commit de `data/`.

    As duas medem coisas diferentes e a mais nova é a que interessa: o painel vê script que rodou
    nesta máquina, o commit vê dado que chegou à `main` por qualquer caminho."""
    datas = []
    try:
        s = json.loads(SAUDE.read_text(encoding="utf-8"))
        datas += [d for d in (data_iso(s.get("atualizado_em")),) if d]
        datas += [d for d in (data_iso(e.get("data")) for e in (s.get("execucoes") or [])) if d]
    except Exception:  # noqa: BLE001
        pass
    d = data_do_ultimo_commit_de_dado()
    if d:
        datas.append(d)
    return max(datas) if datas else None


def data_do_ultimo_commit_de_dado():
    """Data do commit mais recente que tocou `data/`. None fora de um repositório git."""
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cI", "--", "data/"],
                             cwd=RAIZ, capture_output=True, text=True, timeout=30)
        return data_iso(out.stdout.strip()) if out.returncode == 0 else None
    except Exception:  # noqa: BLE001
        return None


def publicado_local():
    try:
        return data_br_para_iso(json.loads(META.read_text(encoding="utf-8")).get("atualizado_em"))
    except Exception:  # noqa: BLE001
        return None


def publicado_no_site(base):
    """`atualizado_em` do `data/meta.json` servido pelo domínio. Senha vem do ambiente
    (`PREVIA_BASIC_AUTH`), nunca de arquivo — o regime do domínio é senha + noindex."""
    import base64
    import urllib.error
    import urllib.request
    url = base.rstrip("/") + "/data/meta.json"
    # §228: o cliente é um só, com o propósito declarado. String literal de User-Agent aqui
    # seria a vigésima segunda cópia a envelhecer — e o portão do cliente identificado pegou.
    sys.path.insert(0, str(RAIZ))
    from coletores_base import ua_de
    req = urllib.request.Request(url, headers={"User-Agent": ua_de("vigia de frescor do site")})
    senha = os.environ.get("PREVIA_BASIC_AUTH") or ""
    if senha:
        req.add_header("Authorization", "Basic " + base64.b64encode(senha.encode()).decode())
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return data_br_para_iso(json.load(r).get("atualizado_em")), None
    except urllib.error.HTTPError as e:
        return None, f"{url} devolveu HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return None, f"{url}: {type(e).__name__}"


def carimbar(publicado, coletado):
    """A data que `data/meta.json` deve declarar: a do último dado que chegou à `main`.

    28/09/2026. `meta.atualizado_em` só era carimbado por `atualizar.py`, a rotina semanal
    monolítica. O desacoplamento (§266, §267) moveu a coleta para os noturnos e a publicação para
    `publicar_dados.yml`, e **o carimbo ficou para trás**: o publicador publicava dado novo e o site
    seguia declarando a data da última rodada semanal. Foi por isso que o rodapé dizia 25/09 com
    dado de 28/09 no ar.

    A data vem do repositório, não do relógio: é a do commit mais recente que tocou `data/`. Assim
    ela **não avança quando nada foi coletado** — carimbar o dia de hoje numa rodada sem dado novo
    seria dizer que o site foi atualizado quando não foi, que é o mesmo erro visto do outro lado.

    Devolve None quando não há o que mudar."""
    if coletado is None or coletado == publicado:
        return None
    return coletado


def gravar_carimbo(nova_data) -> bool:
    """Escreve `atualizado_em` em data/meta.json. `corte` NUNCA é tocado: ele é decisão editorial
    sobre até quando o dado vale, e não tem relação com quando a rodada publicou."""
    sys.path.insert(0, str(RAIZ))
    from coletores_base import gravar_em   # §229: escrita atômica de data/
    doc = json.loads(META.read_text(encoding="utf-8"))
    doc["atualizado_em"] = nova_data.strftime("%d/%m/%Y")
    gravar_em(META, doc)
    return True


def autoteste() -> int:
    casos = []
    d = datetime.date
    casos.append(("data brasileira é lida", data_br_para_iso("28/09/2026") == d(2026, 9, 28)))
    casos.append(("data ISO com hora é lida", data_iso("2026-09-28T09:18:39") == d(2026, 9, 28)))
    casos.append(("lixo não levanta, devolve None", data_br_para_iso("—") is None
                  and data_iso(None) is None))

    casos.append(("mesmo dia: sem atraso",
                  veredito(d(2026, 9, 28), d(2026, 9, 28))["estado"] == "em_dia"))
    casos.append(("um dia de diferença NÃO reprova (granularidade de data)",
                  veredito(d(2026, 9, 27), d(2026, 9, 28))["estado"] == "em_dia"))
    v = veredito(d(2026, 9, 25), d(2026, 9, 28))
    casos.append(("dois dias ou mais reprovam", v["estado"] == "atrasado" and v["atraso_dias"] == 3))
    casos.append(("a mensagem do atraso é a da decisão, com a data",
                  "dado novo não publicado desde 25/09/2026" in v["mensagem"]))
    casos.append(("o caso real de 25/09 contra 28/09 reprova", v["estado"] == "atrasado"))
    casos.append(("site mais novo que o commit de dado não é atraso",
                  veredito(d(2026, 9, 28), d(2026, 9, 25))["estado"] == "em_dia"))
    casos.append(("ponta faltando é indeterminado, nunca 'em dia'",
                  veredito(None, d(2026, 9, 28))["estado"] == "indeterminado"
                  and veredito(d(2026, 9, 28), None)["estado"] == "indeterminado"))
    casos.append(("limite maior tolera mais",
                  veredito(d(2026, 9, 25), d(2026, 9, 28), limite_dias=5)["estado"] == "em_dia"))
    casos.append(("o vigia nunca inventa data: indeterminado não vira em_dia",
                  veredito(None, None)["atraso_dias"] is None))

    casos.append(("carimbo: sem dado novo, nada muda",
                  carimbar(d(2026, 9, 28), d(2026, 9, 28)) is None))
    casos.append(("carimbo: dado novo avança a data",
                  carimbar(d(2026, 9, 25), d(2026, 9, 28)) == d(2026, 9, 28)))
    casos.append(("carimbo: sem data de coleta, nada muda (nunca carimba o relógio)",
                  carimbar(d(2026, 9, 25), None) is None))
    casos.append(("carimbo: a data vem do dado, não de hoje",
                  carimbar(None, d(2026, 9, 26)) == d(2026, 9, 26)))
    import inspect as _insp
    casos.append(("o carimbo nunca toca o corte dos dados",
                  "corte" not in _insp.getsource(gravar_carimbo).split('"""')[2]))

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

    limite = LIMITE_DIAS_PADRAO
    if "--limite-dias" in sys.argv:
        try:
            limite = int(sys.argv[sys.argv.index("--limite-dias") + 1])
        except (IndexError, ValueError):
            print("--limite-dias exige um inteiro.")
            return 2
        if limite < 0:
            print("--limite-dias não pode ser negativo.")
            return 2

    vigia = "--vigia" in sys.argv
    base = None
    if "--base" in sys.argv:
        try:
            base = sys.argv[sys.argv.index("--base") + 1]
        except IndexError:
            print("--base exige uma URL.")
            return 2

    coletado = ultima_coleta_local()
    erro = None
    if base:
        publicado, erro = publicado_no_site(base)
    else:
        publicado = publicado_local()

    v = veredito(publicado, coletado, limite)
    if erro:
        v["mensagem"] += f" · não foi possível ler o site: {erro}"

    if "--carimbar" in sys.argv:
        if base:
            print("--carimbar é local: ele escreve data/meta.json, não lê o site. Rode sem --base.")
            return 2
        nova = carimbar(publicado, coletado)
        if nova is None:
            print(f"OK CARIMBO — nada a mudar; data/meta.json já declara "
                  f"{publicado.strftime('%d/%m/%Y') if publicado else 'nada'} e não há dado mais novo")
            return 0
        gravar_carimbo(nova)
        print(f"OK CARIMBO — data/meta.json passa a declarar {nova.strftime('%d/%m/%Y')}, a data do "
              f"último dado que chegou à main")
        return 0

    if "--json" in sys.argv:
        print(json.dumps({"publicado_em": publicado.isoformat() if publicado else None,
                          "ultimo_dado_em": coletado.isoformat() if coletado else None,
                          "limite_dias": limite, **v}, ensure_ascii=False))
    else:
        marca = {"em_dia": "OK", "atrasado": "X", "indeterminado": "?"}[v["estado"]]
        print(f"{marca} FRESCOR — {v['mensagem']}")

    # Só o vigia reprova. Nos outros modos isto é diagnóstico, e diagnóstico não derruba o job que
    # o chamou para se descrever.
    if vigia and v["estado"] == "atrasado":
        print("::error::" + v["mensagem"])
        return 1
    if vigia and v["estado"] == "indeterminado":
        print("::warning::" + v["mensagem"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
