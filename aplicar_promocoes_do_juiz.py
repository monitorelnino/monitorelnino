#!/usr/bin/env python3
"""Aplica no banco as promoções do juiz automático — Etapa 7, com rede de proteção.

Item 1 do bloco das 19:50 de 28/09/2026 (decisão da central). Não é decisão nova: é a Etapa 7 do
handover do juiz, decidida pela editoria em 27/09 — o juiz promove quando **todos** os critérios
passam sobre o documento primário.

O QUE FALTAVA
-------------
O juiz gravava `promove: true` em `data/promocoes_automaticas.json` e **nada lia aquele campo**.
Quem aplicava no banco era `julgar_e_aplicar_descobertas.py`, que só olha pistas de imprensa com
status `pendente_confirmacao_documento`. O veredito do codebook morria no arquivo.

A SEQUÊNCIA, E O QUE A PROTEGE
------------------------------
  backup em memória → aplica → `recalcular_mare.py --write` → suíte de portões
  portão vermelho → restaura os bytes originais e devolve a pista com o erro escrito

A rede de proteção é a mesma de `julgar_e_aplicar_descobertas.py`, testada desde 31/08/2026: ela
guarda também `recalcular_mare.py` e as páginas que a aplicação estadual toca, porque reverter pela
metade é pior que não aplicar.

SÓ A VERSÃO EM VIGOR DO CODEBOOK
--------------------------------
Aplica apenas vereditos cujo `codebook` é o em vigor e que não estejam superados. Em 28/09/2026 a
regra frouxa de objeto ex-ante promoveu **quatro registros falsos de cinco** (§286); eles ficaram no
arquivo, marcados como superados, e esta trava é o que impede que voltem pelo caminho novo.

PROVENIÊNCIA
------------
Cada registro aplicado carrega `hash_evidencia`, `url`, `data`, `categoria`, o `pista_id` e a versão
do codebook. Os critérios com trecho ficam em `promocoes_automaticas.json`, ligados pelo `pista_id`
— é esse par que a auditoria amostral semanal lê. Errata humana reverte com uma linha: basta apagar
o registro do banco; a decisão continua no registro, dizendo o que foi feito e por quê.

USO
  python3 aplicar_promocoes_do_juiz.py                 # relatório, nada escrito
  python3 aplicar_promocoes_do_juiz.py --aplicar
  python3 aplicar_promocoes_do_juiz.py --autoteste
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

REGISTRO = RAIZ / "data" / "promocoes_automaticas.json"
MUNICIPIOS = RAIZ / "data" / "municipios.json"
PONTOS = RAIZ / "data" / "pontos_mapa.json"


def aplicaveis(decisoes: list, versao: str) -> list:
    """Vereditos que promovem, na versão em vigor, ainda não aplicados nem superados."""
    return [v for v in decisoes
            if v.get("promove") and v.get("codebook") == versao
            and not v.get("superada_por") and not v.get("aplicado_em")]


def ja_no_banco(municipios: list, nome: str, uf: str) -> bool:
    """Duplicar registro é pior que não aplicar: a revisão humana decide se é atualização."""
    n, u = str(nome or "").strip().lower(), str(uf or "").strip().upper()
    return any(str(m.get("nome", "")).strip().lower() == n
               and str(m.get("uf", "")).strip().upper() == u for m in municipios)


def registro_do_veredito(v: dict, lat, lon, canal: str, fonte_base: str, hoje: str) -> dict:
    """O registro do banco, com a proveniência que permite conferir a decisão depois.

    `categoria` vem do veredito — não é fixa. A versão anterior deste caminho, em
    `julgar_e_aplicar_descobertas.py`, gravava sempre "plano", e um `plano_antigo` entraria como
    plano novo, mudando o que o índice conta."""
    registro = {
        "nome": v["municipio"], "uf": v["uf"], "categoria": v["categoria"],
        "documento": documento_do_veredito(v),
        "data": v.get("data"),
        "fonte": f"{fonte_base} — ato lido e classificado pelo juiz automático em {hoje} "
                 f"(codebook {v.get('codebook')}); critérios em promocoes_automaticas.json",
        "url": v.get("url"), "lat": lat, "lon": lon, "canal": canal,
        "hash_evidencia": v.get("hash_evidencia"),
        "pista_id": v.get("pista_id"), "codebook": v.get("codebook"),
    }
    # DECISÃO DA EDITORIA, 03/10/2026: o plano publicado sem ato de aprovação localizado conta no
    # degrau da leitura, **com a marca visível na ficha**. A marca é do REGISTRO, e não do texto da
    # fonte: quem lê a ficha precisa saber que o documento é o plano publicado e que o ato que o
    # aprova não foi localizado — e a marca sai quando o ato aparecer, numa rodada seguinte.
    if v.get("sem_ato_de_aprovacao"):
        registro["sem_ato_de_aprovacao"] = True
        registro["marca_na_ficha"] = "sem ato de aprovação localizado"
        registro["fonte"] = (f"{fonte_base} — plano publicado em domínio oficial do ente, lido e "
                             f"classificado pelo juiz automático em {hoje} (codebook "
                             f"{v.get('codebook')}); ato de aprovação não localizado até o corte; "
                             "critérios em promocoes_automaticas.json")
    return registro


def documento_do_veredito(v: dict) -> str:
    """A ementa curta: o que o ato é, pelo critério que o reconheceu.

    Sai do trecho do objeto ex-ante (Etapa 4), que desde o §286 mostra o verbo e o instrumento
    juntos — é a frase que diz o que foi instituído."""
    objeto = ((v.get("criterios") or {}).get("4_natureza") or {}).get("objeto") or ""
    objeto = " ".join(str(objeto).split())
    if len(objeto) > 180:
        objeto = objeto[:177] + "…"
    return objeto or f"ato classificado como {v.get('categoria')} pelo juiz automático"


def autoteste() -> int:
    casos = []
    V = "1.1 (28/09/2026)"
    base = {"promove": True, "codebook": V, "municipio": "Serra", "uf": "ES",
            "categoria": "plano_antigo", "data": "30/12/2025", "url": "https://x.gov.br/a.pdf",
            "hash_evidencia": "h" * 64, "pista_id": "abc",
            "criterios": {"4_natureza": {"objeto": "Fica instituído o Plano Municipal de Proteção"}}}

    casos.append(("veredito da versão em vigor é aplicável", len(aplicaveis([base], V)) == 1))
    casos.append(("veredito de versão anterior NÃO é aplicável",
                  aplicaveis([dict(base, codebook="1.0 (27/09/2026)")], V) == []))
    casos.append(("veredito superado NÃO é aplicável",
                  aplicaveis([dict(base, superada_por={"codebook": V})], V) == []))
    casos.append(("veredito já aplicado NÃO volta",
                  aplicaveis([dict(base, aplicado_em="2026-09-28")], V) == []))
    casos.append(("recusa nunca é aplicável",
                  aplicaveis([dict(base, promove=False)], V) == []))

    mun = [{"nome": "Serra", "uf": "ES"}]
    casos.append(("município já no banco é reconhecido", ja_no_banco(mun, "serra", "es")))
    casos.append(("município ausente não é falso positivo", not ja_no_banco(mun, "Vitória", "ES")))

    r = registro_do_veredito(base, -20.1, -40.3, "DOM", "Diário oficial municipal", "28/09/2026")
    casos.append(("a categoria vem do veredito, não é fixa em 'plano'",
                  r["categoria"] == "plano_antigo"))
    casos.append(("o registro carrega hash, url e data",
                  r["hash_evidencia"] == "h" * 64 and r["url"].endswith("a.pdf")
                  and r["data"] == "30/12/2025"))
    casos.append(("o registro liga à decisão pelo pista_id e pelo codebook",
                  r["pista_id"] == "abc" and r["codebook"] == V))
    # 03/10/2026: a marca da decisão da editoria viaja do veredito para o registro, e é ela que a
    # ficha mostra. Registro sem a marca não pode ganhá-la por descuido, e com a marca não pode
    # perdê-la — os dois casos abaixo guardam as duas metades.
    r_marca = registro_do_veredito(dict(base, sem_ato_de_aprovacao=True), -1, -2, "c", "f", "01/01/2026")
    casos.append(("plano sem ato: o registro leva a marca para a ficha",
                  r_marca.get("sem_ato_de_aprovacao") is True
                  and r_marca.get("marca_na_ficha") == "sem ato de aprovação localizado"))
    casos.append(("plano sem ato: a fonte do registro diz que o ato não foi localizado",
                  "ato de aprovação não localizado até o corte" in r_marca["fonte"]))
    casos.append(("plano COM ato não ganha a marca",
                  "sem_ato_de_aprovacao" not in r and "marca_na_ficha" not in r))
    casos.append(("a fonte diz que foi o juiz, com a versão",
                  "juiz automático" in r["fonte"] and "1.1" in r["fonte"]))
    casos.append(("a ementa sai do objeto ex-ante",
                  r["documento"].startswith("Fica instituído o Plano Municipal")))
    sem_objeto = registro_do_veredito(dict(base, criterios={}), 0, 0, "DOM", "x", "28/09/2026")
    casos.append(("sem objeto, a ementa diz o que é sem inventar texto",
                  "classificado como plano_antigo" in sem_objeto["documento"]))

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
    from julgar_e_aplicar_descobertas import (backup_dados, buscar_lat_lon, canal_e_fonte,
                                              restaurar_dados, rodar_portoes)

    doc = json.loads(REGISTRO.read_text(encoding="utf-8"))
    decisoes = doc.get("decisoes") or []
    alvo = aplicaveis(decisoes, CODEBOOK_VERSAO)
    print(f"{len(alvo)} promoção(ões) na versão em vigor do codebook ({CODEBOOK_VERSAO}), "
          f"de {len(decisoes)} decisão(ões) no registro")
    for v in alvo:
        print(f"  {v['municipio']}/{v['uf']} · {v['categoria']} · {v.get('data')} · {v.get('url')}")
    if not alvo:
        print("nada a aplicar")
        return 0

    if "--aplicar" not in sys.argv:
        print("relatório apenas; nada escrito (use --aplicar)")
        return 0

    hoje = hoje_editorial()
    backup = backup_dados()
    municipios = json.loads(MUNICIPIOS.read_text(encoding="utf-8"))
    pontos = json.loads(PONTOS.read_text(encoding="utf-8"))
    aplicados, recusados = [], []

    for v in alvo:
        if not v.get("ibge") and not v.get("municipio"):
            recusados.append((v, "veredito sem território — não dá para posicionar"))
            continue
        if ja_no_banco(municipios, v["municipio"], v["uf"]):
            recusados.append((v, "já consta no banco — a revisão humana decide se é atualização"))
            continue
        lat, lon = buscar_lat_lon(v["municipio"], v["uf"])
        if lat is None:
            recusados.append((v, "não consta na referência do IBGE — sem posição no mapa"))
            continue
        canal, fonte_base = canal_e_fonte(v.get("url") or "")
        municipios.append(registro_do_veredito(v, lat, lon, canal, fonte_base,
                                               hoje.strftime("%d/%m/%Y")))
        pontos.append({"nome": v["municipio"], "uf": v["uf"], "categoria": v["categoria"],
                       "lat": lat, "lon": lon, "fase": 3})
        aplicados.append(v)

    for v, motivo in recusados:
        print(f"  não aplicado: {v['municipio']}/{v['uf']} — {motivo}")
        v["nao_aplicado"] = {"em": hoje.isoformat(), "motivo": motivo}

    if not aplicados:
        print("nenhuma promoção aplicável nesta passada; banco intacto")
        gravar_em(REGISTRO, doc)
        return 0

    gravar_em(MUNICIPIOS, municipios)
    gravar_em(PONTOS, pontos)
    print(f"{len(aplicados)} registro(s) escrito(s); rodando recálculo e portões antes de confirmar")

    ok = rodar_portoes()
    if not ok:
        restaurar_dados(backup)
        for v in aplicados:
            v["revertido_por_portao"] = {"em": hoje.isoformat(),
                                         "motivo": "portão vermelho depois da aplicação"}
        gravar_em(REGISTRO, doc)
        print("X portão vermelho — tudo restaurado em disco; as decisões guardam o erro")
        return 1

    for v in aplicados:
        v["aplicado_em"] = hoje.isoformat()
    gravar_em(REGISTRO, doc)
    print(f"OK {len(aplicados)} promoção(ões) aplicada(s) e confirmada(s) pelos portões")
    return 0


if __name__ == "__main__":
    sys.exit(main())
