#!/usr/bin/env python3
"""Rejulga, com a prova já preservada, as decisões gravadas por uma versão anterior do codebook.

28/09/2026. A primeira passada real do juiz promoveu **cinco** registros, e quatro eram falsos:

  Salto/SP, Apucarana/PR, Goiânia/GO   nenhuma ocorrência de termo de plano nos 20.000 caracteres
                                       julgados (Apucarana casou em "Comitê Gestor do Programa
                                       Sandbox"; Goiânia saiu com data de 21/08/1959)
  Alagoinhas/BA                        "Plano de Contingência / PGR" dentro de condicionante de
                                       licença ambiental — obrigação imposta a um licenciado
  Serra/ES                             verdadeiro: "Art. 1º Fica instituído o Plano Municipal de
                                       Proteção e Defesa Civil (PMPDEC)"

A causa está no `juiz.py` e foi consertada lá (Etapa 4 passou a exigir verbo E instrumento na mesma
vizinhança, codebook 1.1). Este script cuida do que já estava gravado.

O QUE ELE FAZ
-------------
Relê a evidência preservada de cada decisão (pelo `hash_evidencia`, do disco, **sem rede**), rejulga
com o codebook em vigor e acrescenta o veredito novo. A decisão antiga **não é apagada**: recebe
`superada_por` com a versão nova e a data, e continua no arquivo. O registro de decisões é o que
alimenta a auditoria amostral semanal — apagar o erro tiraria da auditoria exatamente o caso que ela
precisa ver.

Decisão sem evidência no disco não é rejulgada (não houve documento lido; são as recusas de Etapa 0)
— ela volta à fila pela própria troca de versão do codebook, que é o caminho normal.

USO
  python3 scripts/rejulgar_decisoes_do_juiz.py              # relatório, nada escrito
  python3 scripts/rejulgar_decisoes_do_juiz.py --escrever
  python3 scripts/rejulgar_decisoes_do_juiz.py --autoteste
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

REGISTRO = RAIZ / "data" / "promocoes_automaticas.json"
EVIDENCIAS = RAIZ / "evidencias"


def pendente_de_rejulgamento(v: dict, versao_atual: str) -> bool:
    """Decisão de versão anterior, ainda não superada."""
    return v.get("codebook") != versao_atual and not v.get("superada_por")


def marcar_superada(v: dict, versao_nova: str, data: str) -> dict:
    """A decisão antiga fica, dizendo por quem foi superada. Nada se apaga."""
    v["superada_por"] = {"codebook": versao_nova, "em": data}
    return v


def caminho_da_evidencia(hash_evidencia, pasta=None):
    pasta = pasta or EVIDENCIAS
    if not hash_evidencia:
        return None
    achados = sorted(pasta.glob(str(hash_evidencia) + ".*"))
    return achados[0] if achados else None


def autoteste() -> int:
    casos = []
    v_velha = {"codebook": "1.0 (27/09/2026)", "promove": True}
    casos.append(("decisão de versão anterior é rejulgada",
                  pendente_de_rejulgamento(v_velha, "1.1 (28/09/2026)")))
    casos.append(("decisão da versão em vigor não é rejulgada",
                  not pendente_de_rejulgamento({"codebook": "1.1 (28/09/2026)"}, "1.1 (28/09/2026)")))
    ja = dict(v_velha, superada_por={"codebook": "1.1 (28/09/2026)", "em": "2026-09-28"})
    casos.append(("decisão já superada não é rejulgada de novo",
                  not pendente_de_rejulgamento(ja, "1.1 (28/09/2026)")))

    antiga = {"codebook": "1.0 (27/09/2026)", "promove": True, "municipio": "Salto"}
    marcada = marcar_superada(dict(antiga), "1.1 (28/09/2026)", "2026-09-28")
    casos.append(("a decisão antiga permanece no arquivo, inteira",
                  marcada["promove"] is True and marcada["municipio"] == "Salto"))
    casos.append(("a decisão antiga diz por quem foi superada",
                  marcada["superada_por"]["codebook"] == "1.1 (28/09/2026)"))
    casos.append(("nada é apagado: a chave original do veredito continua lá",
                  "codebook" in marcada and marcada["codebook"] == "1.0 (27/09/2026)"))

    import tempfile
    with tempfile.TemporaryDirectory() as d:
        pasta = pathlib.Path(d)
        (pasta / ("a" * 64 + ".txt")).write_text("x", encoding="utf-8")  # escrita-nao-portavel-ok: arquivo de um caractere em diretório temporário do autoteste, nunca versionado
        casos.append(("acha a evidência pelo hash", caminho_da_evidencia("a" * 64, pasta) is not None))
        casos.append(("hash sem arquivo devolve None", caminho_da_evidencia("b" * 64, pasta) is None))
        casos.append(("hash vazio devolve None", caminho_da_evidencia(None, pasta) is None))

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

    from coletores_base import gravar_em, hoje_editorial
    from juiz import CODEBOOK_VERSAO
    from julgar_filas import julgar_uma

    doc = json.loads(REGISTRO.read_text(encoding="utf-8"))
    decisoes = doc.get("decisoes") or []
    fila = {p["id"]: p for p in json.loads(
        (RAIZ / "data" / "pistas_imprensa.json").read_text(encoding="utf-8")).get("pistas", [])
        if p.get("id")}

    novos, superadas, sem_prova = [], 0, 0
    viraram = {"promove_continua": 0, "promove_cai": 0, "recusa_continua": 0, "recusa_vira_promove": 0}
    hoje = hoje_editorial().isoformat()

    for v in decisoes:
        if not pendente_de_rejulgamento(v, CODEBOOK_VERSAO):
            continue
        arq = caminho_da_evidencia(v.get("hash_evidencia"))
        if arq is None:
            sem_prova += 1
            continue
        texto = arq.read_text(encoding="utf-8", errors="replace")
        pista = fila.get(v.get("pista_id"), {})
        # `buscar` devolve o texto do disco: rejulgar não toca a rede, e a decisão nova é sobre
        # exatamente a mesma prova que a antiga julgou.
        novo = julgar_uma({"id": v.get("pista_id"), "municipio": v.get("municipio"),
                           "uf": v.get("uf"), "ibge": v.get("ibge"), "url": v.get("url"),
                           "origem": v.get("origem"), "trecho": pista.get("trecho")},
                          lambda _u: texto)
        novo["hash_evidencia"] = v.get("hash_evidencia")
        novo["rejulgada_de"] = {"codebook": v.get("codebook"), "promovia": bool(v.get("promove"))}
        antes, agora = bool(v.get("promove")), bool(novo.get("promove"))
        virou = ("promove_continua" if antes and agora else
                   "promove_cai" if antes else
                   "recusa_vira_promove" if agora else "recusa_continua")
        viraram[virou] += 1
        marcar_superada(v, CODEBOOK_VERSAO, hoje)
        superadas += 1
        novos.append(novo)

    print(f"{superadas} decisão(ões) rejulgada(s) com a prova do disco; {sem_prova} sem evidência "
          f"(recusa de Etapa 0 — voltam à fila pela troca de versão do codebook)")
    for k, n in viraram.items():
        if n:
            print(f"  {k}: {n}")
    for novo in novos:
        if novo.get("rejulgada_de", {}).get("promovia") and not novo.get("promove"):
            print(f"  REVOGADA: {novo.get('municipio')}/{novo.get('uf')} — agora "
                  f"{novo.get('motivo')}")

    if "--escrever" not in sys.argv:
        print("relatório apenas; nada escrito (use --escrever)")
        return 0

    doc["decisoes"] = decisoes + novos
    gravar_em(REGISTRO, doc)   # §229
    print(f"OK data/{REGISTRO.name}: {len(decisoes)} decisão(ões) mantida(s) e {len(novos)} "
          f"acrescentada(s). Nada apagado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
