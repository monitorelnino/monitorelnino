#!/usr/bin/env python3
"""
verificar_funil.py
==================
Portão do funil de coleta. Lê `data/funil/<AAAA-MM-DD>.json` (escrito por `funil.py`) e
reprova a rodada quando a contagem diz que a etapa não funcionou.

Handover `HANDOVER_juiz_automatico_e_busca_web_27-09-2026.md` (PR 1 item 3, PR 3) e
`HANDOVER_auditoria_funil_de_coleta_27-09-2026.md` (item B).

Invariantes:

  1. **Motor doente não conta como verificação.** Se `motor_sem_resposta + lacunas` passa de
     25% das consultas da busca web, a rodada não verificou a camada 4 — reprova. Era o defeito
     de 21-27/09: 5.263 de 11.412 consultas (46%) voltaram com zero resultado bruto e receberam
     `coberto_sem_mencao`, que é uma afirmação de ausência.

  2. **Etapa com histórico não devolve zero calada.** Se uma chave já devolveu mais de zero em
     alguma rodada anterior e devolve zero agora, alerta (não reprova): pode ser o dia, pode ser
     o coletor quebrado — quem lê decide, mas ninguém descobre por acidente.

  3. **Registro não excede o que foi classificado.** `promovidas > com_documento` na etapa do
     juiz é impossível: alguém promoveu sem documento primário. Reprova.

O portão é permissivo quanto à AUSÊNCIA do arquivo: rodada que não chamou a busca web não tem
o contador, e isso não é defeito. O que ele não perdoa é o contador que se contradiz.

USO
  python3 scripts/verificar_funil.py            # a rodada de hoje
  python3 scripts/verificar_funil.py --dia 2026-09-27
  python3 scripts/verificar_funil.py --autoteste
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

FUNIL = RAIZ / "data" / "funil"
TETO_MOTOR_SEM_RESPOSTA = 0.25


def ler_json(p: pathlib.Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def historico(exceto: pathlib.Path) -> dict:
    """Máximo já visto por (etapa, chave) nas outras rodadas — base do invariante 2."""
    maximos = {}
    if not FUNIL.exists():
        return maximos
    for p in sorted(FUNIL.glob("*.json")):
        if p == exceto:
            continue
        for etapa, contagens in (ler_json(p).get("etapas") or {}).items():
            for chave, valor in contagens.items():
                if isinstance(valor, int):
                    maximos[(etapa, chave)] = max(maximos.get((etapa, chave), 0), valor)
    return maximos


def conferir(doc: dict, maximos: dict) -> tuple:
    """Devolve (falhas, alertas). Função pura: o autoteste a exercita sem tocar em disco."""
    falhas, alertas = [], []
    etapas = doc.get("etapas") or {}

    bw = etapas.get("busca_web") or {}
    consultas = int(bw.get("consultas", 0) or 0)
    if consultas:
        doentes = int(bw.get("motor_sem_resposta", 0) or 0) + int(bw.get("lacunas", 0) or 0)
        fracao = doentes / consultas
        if fracao > TETO_MOTOR_SEM_RESPOSTA:
            falhas.append(f"busca web: {doentes}/{consultas} consultas sem resposta do motor "
                          f"({100 * fracao:.0f}%), acima do teto de {100 * TETO_MOTOR_SEM_RESPOSTA:.0f}% "
                          f"- a rodada nao conta como verificacao da camada 4")
        if int(bw.get("coberto_sem_mencao", 0) or 0) > consultas - doentes:
            falhas.append("busca web: mais municipios cobertos sem mencao do que consultas com resultado bruto")

    juiz = etapas.get("juiz") or {}
    if juiz:
        promovidas = int(juiz.get("promovidas", 0) or 0)
        com_doc = int(juiz.get("com_documento", 0) or 0)
        if promovidas > com_doc:
            falhas.append(f"juiz: {promovidas} promovidas contra {com_doc} pistas com documento "
                          f"primario - promocao sem documento e impossivel pela regra (Etapa 0)")

    for (etapa, chave), maximo in sorted(maximos.items()):
        if maximo > 0 and etapa in etapas and int((etapas[etapa] or {}).get(chave, 0) or 0) == 0:
            alertas.append(f"{etapa}.{chave}: ja devolveu ate {maximo} em rodada anterior, devolveu 0 agora")
    return falhas, alertas


def autoteste() -> int:
    casos = []

    # 1. o defeito de 21-27/09: 46% sem resposta reprova
    f, _ = conferir({"etapas": {"busca_web": {"consultas": 11412, "motor_sem_resposta": 5263}}}, {})
    casos.append(("46% sem resposta reprova", bool(f) and "camada 4" in f[0]))

    # 2. no teto exato não reprova (o teto é "acima de", não "a partir de")
    f, _ = conferir({"etapas": {"busca_web": {"consultas": 100, "motor_sem_resposta": 25}}}, {})
    casos.append(("exatamente 25% nao reprova", not f))
    f, _ = conferir({"etapas": {"busca_web": {"consultas": 100, "motor_sem_resposta": 26}}}, {})
    casos.append(("26% reprova", bool(f)))

    # 3. lacuna de rede conta junto com o motor mudo — as duas são a mesma doença
    f, _ = conferir({"etapas": {"busca_web": {"consultas": 100, "motor_sem_resposta": 20, "lacunas": 10}}}, {})
    casos.append(("lacuna soma com motor_sem_resposta", bool(f)))

    # 4. coberto além do que teve resultado bruto é contradição
    f, _ = conferir({"etapas": {"busca_web": {"consultas": 100, "motor_sem_resposta": 10,
                                              "coberto_sem_mencao": 95}}}, {})
    casos.append(("coberto acima do que teve resultado bruto reprova", bool(f)))

    # 5. promoção sem documento primário é impossível
    f, _ = conferir({"etapas": {"juiz": {"promovidas": 5, "com_documento": 3}}}, {})
    casos.append(("juiz: promovidas > com_documento reprova", bool(f)))
    f, _ = conferir({"etapas": {"juiz": {"promovidas": 3, "com_documento": 3}}}, {})
    casos.append(("juiz: promovidas == com_documento passa", not f))

    # 6. etapa que já produziu e hoje devolve zero é ALERTA, não falha
    f, a = conferir({"etapas": {"busca_web": {"consultas": 100, "pistas": 0}}},
                    {("busca_web", "pistas"): 12})
    casos.append(("zero com historico alerta e nao reprova", not f and len(a) == 1))

    # 7. etapa ausente não alerta (rodada que não chamou o coletor)
    f, a = conferir({"etapas": {}}, {("busca_web", "pistas"): 12})
    casos.append(("etapa ausente nao alerta", not f and not a))

    # 8. rodada vazia não reprova
    f, a = conferir({}, {})
    casos.append(("arquivo ausente ou vazio nao reprova", not f and not a))

    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        marca = "OK  " if ok else "FALHA"
        print(f"  {marca} {n}")
    if ruins:
        print(f"X AUTOTESTE DO FUNIL: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    dia = None
    if "--dia" in sys.argv:
        dia = sys.argv[sys.argv.index("--dia") + 1]
    if dia is None:
        from coletores_base import hoje_editorial
        dia = hoje_editorial().strftime("%Y-%m-%d")
    p = FUNIL / f"{dia}.json"
    if not p.exists():
        print(f"✓ FUNIL OK — sem contador para {dia} (a rodada não chamou as etapas instrumentadas).")
        return 0
    doc = ler_json(p)
    falhas, alertas = conferir(doc, historico(p))
    for a in alertas:
        print(f"  ! {a}")
    if falhas:
        print("✗ FUNIL: a contagem da rodada se contradiz ou a etapa não funcionou:")
        for f in falhas:
            print(f"   - {f}")
        return 1
    etapas = ", ".join(f"{k} ({len(v)} contagens)" for k, v in sorted((doc.get("etapas") or {}).items()))
    print(f"✓ FUNIL OK — {dia}: {etapas or 'nenhuma etapa'}." + (f" {len(alertas)} alerta(s)." if alertas else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
