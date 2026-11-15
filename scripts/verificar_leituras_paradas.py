#!/usr/bin/env python3
"""Leitura que parou sem ninguém ver: mede, toda noite, o que ficou sem ler, e avisa. Só leitura de `data/`.

Por que existe (15/11/2026): dois defeitos ficaram semanas no ar porque nada media a FILA, só o coletor.
1.624 pistas em domínio oficial sem veredito (o juiz baixava com 20 s de prazo e a falha saía como
"documento inacessível") e edições do diário do Amazonas marcadas "sem edição" para sempre. O coletor
rodava verde nos dois casos. Aqui se mede o resultado: diário de estado com rota de edição sem edição
lida, e documento oficial esperando o juiz além do prazo. Passou do limite, abre Issue no repositório
dos avisos (fecha sozinha quando volta). Não grava em `data/` e nunca reprova o elo.

USO
  python3 scripts/verificar_leituras_paradas.py            # mede e avisa
  python3 scripts/verificar_leituras_paradas.py --autoteste
"""
import datetime
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

DIAS_SEM_EDICAO = 10        # diário com rota de edição: a mais recente lida não pode ser mais velha que isto
DIAS_NA_FILA = 14           # documento em domínio oficial: prazo para ter veredito do juiz
TETO_NA_FILA = 150          # quantos podem estar além do prazo (a fila anda um lote por noite)
TETO_DA_SAUDE = 60          # pistas de saúde estadual sem veredito além do prazo (a rodada é semanal)
TITULO = "Leitura parada"


def _data(s):
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.datetime.strptime(str(s or "")[:10], fmt).date()
        except ValueError:
            continue
    return None


def diarios_parados(registros: dict, hoje: datetime.date, limite: int = DIAS_SEM_EDICAO) -> list:
    """UFs com rota de edição por data cuja edição lida mais recente passou do limite. Função pura.
    `registros` é {uf: conteúdo de data/doe_edicoes/<uf>.json}."""
    fora = []
    for uf, reg in sorted((registros or {}).items()):
        if ((reg or {}).get("canal2") or {}).get("modo") != "padrao_por_data":
            continue
        lidas = sorted(k.split("#")[0] for k, e in ((reg or {}).get("edicoes") or {}).items()
                       if (e or {}).get("decisao") == "lida")
        dias = (hoje - datetime.date.fromisoformat(lidas[-1])).days if lidas else None
        if dias is None or dias > limite:
            fora.append(f"diário de {uf}: " + (f"última edição lida há {dias} dias ({lidas[-1]})" if lidas
                                                else "nenhuma edição lida"))
    return fora


def oficiais_sem_veredito(pistas: list, hoje: datetime.date, e_oficial, dias: int = DIAS_NA_FILA) -> int:
    """Quantas pistas em domínio oficial esperam o juiz, sem veredito, há mais de `dias`. Função pura."""
    n = 0
    for p in pistas or []:
        if not str(p.get("status") or "").startswith("pista — na fila") or p.get("juiz"):
            continue
        desde = _data(p.get("registrado_em") or p.get("data"))
        if desde and (hoje - desde).days > dias and e_oficial(p.get("url") or p.get("url_final")):
            n += 1
    return n


def saude_sem_veredito(pistas: list, hoje: datetime.date, dias: int = DIAS_NA_FILA) -> int:
    """Quantas pistas de saúde estadual esperam o juiz de saúde há mais de `dias`. Função pura. 15/11/2026:
    a rodada semanal saiu verde em 04 e 11/11 e o trabalho dela se perdeu (a fila não tinha regra de mesclagem); 474 de 882
    pistas ficaram sem veredito e nenhuma pista nova entrou em novembro."""
    return sum(1 for p in pistas or []
               if not p.get("juiz") and str(p.get("status") or "").startswith("pendente")
               and (_data(p.get("registrado_em")) or hoje) < hoje - datetime.timedelta(days=dias))


def problemas(registros: dict, pistas: list, hoje: datetime.date, e_oficial, saude: list = None) -> list:
    fora = diarios_parados(registros, hoje)
    s = saude_sem_veredito(saude, hoje)
    if s > TETO_DA_SAUDE:
        fora.append(f"{s} pista(s) de saúde estadual sem veredito do juiz há mais de {DIAS_NA_FILA} dias "
                    f"(teto {TETO_DA_SAUDE}): o trabalho da rodada de saúde estadual não está chegando à `main`")
    n = oficiais_sem_veredito(pistas, hoje, e_oficial)
    if n > TETO_NA_FILA:
        fora.append(f"{n} documento(s) em domínio oficial sem veredito do juiz há mais de {DIAS_NA_FILA} dias "
                    f"(teto {TETO_NA_FILA})")
    return fora


def avisar(achados: list, gh=None) -> str:
    from scripts import avisos
    return avisos.avisar(TITULO, "\n".join(f"- {x}" for x in achados), "Leituras em dia. Fechada.", gh or avisos._gh)


def autoteste() -> int:
    from scripts._casos import ok_de
    falhas, casos = [], []
    ok = ok_de(falhas, casos)
    hoje = datetime.date(2026, 11, 15)
    rota = {"canal2": {"modo": "padrao_por_data"}}
    ok("diário com rota e edição lida há mais de dez dias é parado; em dia, não; por busca, não se mede aqui",
       diarios_parados({"RN": dict(rota, edicoes={"2026-11-03": {"decisao": "lida"}, "2026-11-06": {"decisao": "vazio"}}),
                        "PA": dict(rota, edicoes={"2026-11-12#2": {"decisao": "lida"}}),
                        "SP": {"canal2": {"modo": "busca_no_diario"}, "edicoes": {}}}, hoje)
       == ["diário de RN: última edição lida há 12 dias (2026-11-03)"])
    ok("rota de edição sem nenhuma edição lida é parado",
       diarios_parados({"AM": dict(rota, edicoes={"2026-11-10": {"decisao": "sem_edicao_na_data"}})}, hoje)
       == ["diário de AM: nenhuma edição lida"])
    fila = {"status": "pista — na fila, aguardando busca dirigida e juiz", "registrado_em": "2026-10-14",
            "url": "https://x.rj.gov.br/p.pdf"}
    oficial = lambda u: ".gov.br" in str(u)
    ok("conta só o oficial, na fila, sem veredito e além do prazo",
       oficiais_sem_veredito([fila, dict(fila, juiz={"promove": False}), dict(fila, registrado_em="2026-11-10"),
                              dict(fila, url="https://g1.globo.com/x"), dict(fila, status="fechada — x")], hoje, oficial) == 1)
    ok("abaixo do teto a fila não é achado; acima, é",
       problemas({}, [fila] * TETO_NA_FILA, hoje, oficial) == []
       and "sem veredito" in problemas({}, [fila] * (TETO_NA_FILA + 1), hoje, oficial)[0])
    ps = lambda reg, juiz=None: {"status": "pendente_confirmacao_documento", "registrado_em": reg, **({"juiz": juiz} if juiz else {})}
    ok("fila de saúde: conta a pendente sem veredito além do prazo; julgada e recente não; acima do teto é achado",
       saude_sem_veredito([ps("21/10/2026"), ps("21/10/2026", {"promove": False}), ps("10/11/2026")], hoje) == 1
       and "saúde estadual" in problemas({}, [], hoje, oficial, [ps("21/10/2026")] * (TETO_DA_SAUDE + 1))[0]
       and problemas({}, [], hoje, oficial, [ps("21/10/2026")] * TETO_DA_SAUDE) == [])
    def gh_com(abertas):
        return lambda args, entrada=None: type("R", (), {"returncode": 0, "stdout": json.dumps(abertas)})()
    aberta = [{"title": TITULO, "number": 9}]
    ok("achado abre a Issue uma vez; sem achado, fecha; sem nada a fazer, não mexe",
       (avisar(["x"], gh_com([])), avisar(["x"], gh_com(aberta)), avisar([], gh_com(aberta)), avisar([], gh_com([])))
       == ("aberta", "sem mudança", "fechada", "sem mudança"))
    ok("garantia estrutural: roda no fim da corrente, no elo da triagem",
       "scripts/verificar_leituras_paradas.py" in (RAIZ / ".github/workflows/noturno_triagem.yml").read_text(encoding="utf-8"))
    ok("garantia estrutural: não grava em data/",
       "gravar" not in pathlib.Path(__file__).read_text(encoding="utf-8").split("def autoteste")[0].replace("Não grava", ""))
    print(f"✗ AUTOTESTE: {len(falhas)} falha(s)." if falhas else f"✓ AUTOTESTE OK — {len(casos)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    from coletores_base import hoje_editorial
    from julgar_filas import url_em_dominio_oficial
    registros = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted((RAIZ / "data" / "doe_edicoes").glob("*.json"))}
    fila = json.loads((RAIZ / "data" / "pistas_imprensa.json").read_text(encoding="utf-8"))
    saude = json.loads((RAIZ / "data" / "pistas_imprensa_saude.json").read_text(encoding="utf-8")).get("pistas")
    achados = problemas(registros, fila.get("pistas") if isinstance(fila, dict) else fila, hoje_editorial(), url_em_dominio_oficial, saude)
    for x in achados:
        print(f"::warning::{x}")
    try:
        print(f"leituras paradas: {len(achados)} achado(s) · Issue: {avisar(achados)}")
    except Exception as e:  # noqa: BLE001 — o aviso é do GitHub; a medida já está no log
        print(f"::warning::aviso não enviado: {type(e).__name__}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
