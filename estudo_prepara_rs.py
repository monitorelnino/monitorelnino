"""Estudo de conteúdo dos planos do Prepara RS (23/11/2026, pedido da editoria; não vai à main).

Lê cada documento da pasta pública da Casa Militar/RS (a evidência guardada quando há; senão, pela porta do
juiz, com OCR e cópia pública) e grava, por plano, campos lidos por regra e trechos, em data/estudo_prepara_rs_<k>.json.
Uso: python3 estudo_prepara_rs.py <k> <n>   (fatia k de n)."""
import json, re, sys, pathlib, collections, unicodedata, time
sys.path.insert(0, "scripts")
import juiz
from julgar_e_aplicar_descobertas import obter_documento, com_ocr, texto_do_documento

RAIZ = pathlib.Path(".")
k, n = int(sys.argv[1]), int(sys.argv[2])


def norm(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


d = json.load(open("data/pistas_imprensa.json"))
L = d if isinstance(d, list) else next(v for v in d.values() if isinstance(v, list))
rs = sorted([p for p in L if "casa-militar_casamilitar_rs_gov_br" in str(p.get("url_final") or p.get("url"))],
            key=lambda p: str(p.get("id")))
rs = rs[k - 1::n]
mun = {(m["nome"], m["uf"]): m for m in json.load(open("data/municipios.json"))}

RISCOS = {
    "inundacao_enchente": r"inunda|enchente|cheia",
    "enxurrada": r"enxurrada",
    "alagamento": r"alagamento",
    "deslizamento_mov_massa": r"deslizamento|movimento[s]? de massa|escorregamento|desmoronamento|queda de (?:barreira|blocos)",
    "estiagem_seca": r"estiagem|\bseca\b",
    "vendaval_ciclone": r"vendaval|ciclone|ventos? fortes?|tempestade",
    "granizo": r"granizo",
    "tornado": r"tornado",
    "incendio": r"incendio|queimada",
    "frio_geada": r"geada|onda de frio|frio intenso",
    "rompimento_barragem": r"barragem",
    "produtos_perigosos": r"produtos? perigosos?",
}
ITENS = {
    "el_nino": r"el nino",
    "la_nina": r"la nina",
    "niveis_de_alerta": r"(?:observa[cç]ao|aten[cç]ao).{0,80}alerta.{0,80}alarme|niveis? de (?:alerta|acionamento|ativa[cç]ao)",
    "acionamento_ativacao": r"acionamento|ativa[cç]ao do plano|desmobiliza",
    "abrigos": r"abrigo",
    "pontos_de_apoio": r"pontos? de apoio|pontos? de encontro",
    "rotas_de_fuga": r"rotas? de fuga",
    "areas_de_risco_mapeadas": r"setoriza[cç]ao|areas? de risco|cprm|servico geologico|\bsgb\b|mapa de risco",
    "populacao_em_risco": r"(?:popula[cç]ao|pessoas|familias|moradores).{0,40}(?:em|na|nas) (?:areas? de )?risco",
    "monitoramento_alerta": r"cemaden|monitoramento|sms 40199|40199|defesa civil alerta|cell broadcast|sistema de alerta",
    "atribuicoes_responsabilidades": r"atribui[cç]oes|responsabilidades|matriz de",
    "recursos_inventario": r"recursos? (?:materiais|humanos|dispon)|inventario|viaturas?|equipamentos",
    "contatos": r"contatos?|telefones?|\(\d\d\)\s?\d{4}",
    "compdec_comdec": r"compdec|comdec|coordenadoria municipal de (?:protecao e )?defesa civil",
    "assinatura_prefeito": r"prefeit[oa] municipal|assinatura",
    "audiencia_publica": r"audiencia publica",
    "simulado_exercicio": r"simulado|exercicio simulado",
    "atualizacao_revisao": r"atualiza[cç]ao|revisao|versao",
    "lei_12608": r"12\.?608",
    "lei_12340": r"12\.?340",
    "cobrade": r"cobrade|\b1\.2\.1\.0\.0\b|\b1\.4\.1\.1\.0\b",
    "historico_desastres": r"historico|2023|2024.{0,40}(?:enchente|inunda|calamidade)|maio de 2024",
    "saude_vigilancia": r"vigilancia (?:em )?saude|secretaria (?:municipal )?de saude|leptospirose",
    "assistencia_social": r"assistencia social|cras|creas",
    "educacao_escolas": r"escolas?|secretaria (?:municipal )?de educa",
}

out = []
for p in rs:
    url = p.get("url_final") or p.get("url")
    pasta = re.search(r"CREPDEC%20(\d+)", url or "")
    reg = {"pista_id": p.get("id"), "municipio": p.get("municipio"), "crepdec": pasta.group(1) if pasta else None,
           "arquivo": re.sub(r"%20", " ", url.rsplit("/", 1)[-1])[:120], "url": url,
           "juiz": {kk: (p.get("juiz") or {}).get(kk) for kk in ("promove", "motivo", "categoria", "data")}}
    m = mun.get((p.get("municipio"), "RS"))
    reg["no_banco"] = {"categoria": m.get("categoria"), "data": m.get("data"), "marca": m.get("marca_na_ficha"),
                       "vigencia_encerrada": m.get("vigencia_declarada_encerrada")} if m else None
    t0 = time.time()
    try:
        raw = obter_documento(url, 90, "estudo Prepara RS")
        texto = com_ocr(raw, texto_do_documento(raw, url))
        reg["bytes"] = len(raw)
        reg["paginas"] = len(re.findall(rb"/Type\s*/Page[^s]", raw)) if raw[:5] == b"%PDF-" else None
    except Exception as e:
        reg["erro"] = f"{type(e).__name__}: {str(e)[:160]}"
        texto = ""
    reg["segundos"] = round(time.time() - t0, 1)
    t = re.sub(r"=== página \d+ ===", " ", texto or "")
    t = re.sub(r"\s+", " ", t).strip()
    tn = norm(t)
    reg["caracteres"] = len(t)
    reg["letras"] = sum(c.isalpha() for c in t)
    if t:
        tit = juiz.RE_TITULO_DE_PLANO.search(t[:4000])
        reg["titulo"] = t[max(0, tit.start() - 40): tit.end() + 140] if tit else None
        ano, susp = juiz.ano_do_plano(t)
        reg["ano_do_plano"] = ano
        reg["vigencia_declarada"] = juiz.vigencia_encerrada(t) or None
        per = juiz.RE_PERIODO_DO_PLANO.search(t[:3000])
        reg["periodo_na_capa"] = per.group(0) if per else None
        reg["riscos"] = {r: len(re.findall(rx, tn)) for r, rx in RISCOS.items()}
        reg["itens"] = {i: len(re.findall(rx, tn)) for i, rx in ITENS.items()}
        reg["gatilho_ciclo"] = bool(juiz.RE_GATILHO_CICLO.search(t))
        reg["minuta"] = bool(juiz.RE_MINUTA.search(t))
        trechos = {}
        for nome, rx in (("el_nino", r"el ni[nñ]o"), ("abrigo", r"abrigo"), ("niveis", r"n[ií]ve(?:l|is) de (?:alerta|acionamento|ativa)"),
                         ("estiagem", r"estiagem"), ("risco_populacao", r"(?:popula[cç][aã]o|fam[ií]lias|pessoas).{0,40}(?:em|na|nas) (?:[aá]reas? de )?risco"),
                         ("atualizacao", r"(?:atualizad[oa]|revis[aã]o|vers[aã]o)\s*(?:em|:)?\s*\S{0,12}\s*(?:19|20)\d\d")):
            mm = re.search(rx, t, re.I)
            if mm:
                trechos[nome] = t[max(0, mm.start() - 160): mm.end() + 220]
        reg["trechos"] = trechos
        reg["inicio"] = t[:2500]
        reg["sumario"] = (lambda i: t[i:i + 3000] if i >= 0 else None)(norm(t[:20000]).find("sumario"))
    out.append(reg)
    print(f"{len(out):3}/{len(rs)} {reg['municipio']}: {reg.get('caracteres')} car. {reg.get('erro') or ''}", flush=True)

json.dump(out, open(f"data/estudo_prepara_rs_{k}.json", "w"), ensure_ascii=False, indent=0)
c = collections.Counter("erro" if r.get("erro") else ("vazio" if not r.get("letras") else "lido") for r in out)
print("RESUMO", dict(c))
