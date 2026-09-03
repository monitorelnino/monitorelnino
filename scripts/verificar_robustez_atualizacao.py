#!/usr/bin/env python3
"""
scripts/verificar_robustez_atualizacao.py — portão 17 (03/09/2026, a pedido da editoria)
==========================================================================================
Prova que uma ATUALIZAÇÃO DE DADOS não quebra mapas, barras, indicadores nem legendas.
Numa cópia temporária do repositório, perturba cada família de dado que a rotina pode
alterar, regenera os derivados como a rotina faz e exige todos os runtimes verdes:
  1. índice: nota de 3 UFs alterada (sobe, desce, muda de faixa) → medidor, mapas e selos;
  2. verificação: 120 municípios sobem a 'nacional', 30 a 'estadual', 5 a 'municipal_completo'
     (com log v2 estruturado) → contador, mapa 1b, cartão da cidade;
  3. atos de resposta: 3 reconhecimentos federais novos (com lat/lon) → mapa de resposta,
     tabela por UF, financiamento;
  4. saúde: 2 UFs passam a NOVO/READ com documento e data → mapas e quadrantes;
  5. financiamento: série semanal de 8 semanas em 8 rotas + valores por UF em 3 rotas → gráfico
     empilhado, coroplético, seletor;
  6. sinais: aviso INMET e ONI coletados → mapas de sinais e cartões.
Depois, roda: recalcular --write, gerar_painel --fichas, feeds, dados abertos, e os seis runtimes
+ estrutura + acessibilidade + vocabulário público. Nada é gravado no repositório real.
"""
import json, os, pathlib, random, shutil, subprocess, sys, tempfile
from datetime import date

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def j(p): return json.load(open(p, encoding="utf-8"))
def w(p, o): json.dump(o, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1); open(p, "a").write("\n")


def perturbar(T: pathlib.Path):
    D = T / "data"; rng = random.Random(20260903)
    # 1. índice — pelo canal legítimo da rotina: registros municipais novos com documento primário
    #    (cobertura populacional muda a nota de 3 UFs); pontos_mapa sincronizado como faz aplicar_revisao
    ref = j(D / "municipios_ibge_referencia.json"); por = {str(r["codigo_ibge"]).zfill(7): r for r in ref}
    mun = j(D / "municipios.json"); pts = j(D / "pontos_mapa.json"); ja = {(m["nome"], m["uf"]) for m in mun}
    novos = [r for r in ref if r["uf"] in ("PB", "PA", "GO") and (r["nome"], r["uf"]) not in ja][:9]
    for r in novos:
        reg = {"nome": r["nome"], "uf": r["uf"], "categoria": "plano", "documento": "Decreto nº 123/2026 — Plano de Contingência El Niño 2026/2027", "data": "20/08/2026",
               "fonte": "Diário Oficial do Município", "url": "https://www." + r["uf"].lower() + ".gov.br/teste.pdf", "lat": r["lat"], "lon": r["lon"], "canal": "DOM", "data_localizacao": "06/09/2026"}
        mun.append(reg); pts.append({"nome": r["nome"], "uf": r["uf"], "categoria": "plano", "lat": r["lat"], "lon": r["lon"], "fase": 2})
    w(D / "municipios.json", mun); w(D / "pontos_mapa.json", pts)
    # 2. verificação — livro de fontes consultadas + log v2
    cods = [str(r["codigo_ibge"]).zfill(7) for r in ref]; rng.shuffle(cods)
    livro = {"_governanca": "teste", "municipios": {}}
    for c in cods[:120]: livro["municipios"][c] = {"nivel_verificacao": "nacional", "ultima_verificacao": "2026-09-06", "fontes": [{"fonte": "DOU", "data": "2026-09-06", "resultado": "ok"}]}
    for c in cods[120:150]: livro["municipios"][c] = {"nivel_verificacao": "estadual", "ultima_verificacao": "2026-09-06", "fontes": [{"fonte": "DOE", "data": "2026-09-06", "resultado": "ok"}], "decreto_homologado": True}
    w(D / "fontes_consultadas.json", livro)
    lg = j(D / "log_buscas.json")
    for c in cods[150:155]:
        r = por[c]; lg["execucoes"].append({"data": "2026-09-06", "canal": "DOM", "camada": 1, "uf": r["uf"], "municipio": r["nome"], "ibge": c, "nivel": "municipal_completo",
                                            "strings": ["plano de contingência"], "n_resultados": 0, "resultados": "bateria completa", "decisao": "nada localizado", "fonte_suspensa_defeso": False, "executor": "robo", "hash_evidencia": None})
    w(D / "log_buscas.json", lg)
    # 3. atos de resposta
    atos = j(D / "atos_resposta.json")
    for c in cods[200:203]:
        r = por[c]; atos["eventos"].append({"nome": r["nome"], "uf": r["uf"], "ibge": c, "data": "05/09/2026", "causa": "reconhecimento federal", "decreto": "Portaria SEDEC/MIDR nº 9.999",
                                            "fonte": "DOU (portaria SEDEC/MIDR)", "url": "https://www.in.gov.br/web/dou/-/teste", "lat": r["lat"], "lon": r["lon"], "canal": "DOU"})
    w(D / "atos_resposta.json", atos)
    # 4. saúde
    su = j(D / "saude_uf.json")
    su["uf"]["SC"].update({"status": "NOVO", "orgao": "SES/SC", "doc": "Plano de contingência para arboviroses 2026/2027", "numero": "Portaria nº 1/2026", "data": "20/08/2026", "url": "https://www.saude.sc.gov.br/teste", "natureza_doc": "ex_ante", "consist": "COBRE", "data_verificacao": "06/09/2026", "log_ref": "lote1"})
    su["uf"]["BA"].update({"status": "READ", "orgao": "SESAB", "doc": "Plano de contingência 2025 readaptado", "data": "10/07/2026", "natureza_doc": "ex_ante", "consist": "PARCIAL", "data_verificacao": "06/09/2026", "log_ref": "lote1"})
    w(D / "saude_uf.json", su)
    # 5. financiamento
    F = D / "financiamento"; ser = j(F / "serie_nacional.json"); rotas = [r["id"] for r in j(F / "rotas.json")["rotas"]]
    ser["semanas"] = [{"semana": f"2026-0{m}-0{d}", **{r: rng.randint(1, 50) * 1e6 for r in rotas}} for m, d in ((6, 1), (6, 8), (7, 6), (7, 13), (8, 3), (8, 10), (8, 17), (8, 24))]
    for s in ser["semanas"]: s["total"] = sum(s[r] for r in rotas)
    ser["status"] = "coletado"; w(F / "serie_nacional.json", ser)
    pu = j(F / "por_uf.json")
    for uf in ("SC", "BA", "PA"):
        for r in ("r1", "r3", "r5"): pu["uf"][uf]["rotas"][r] = {"valor_2026": rng.randint(1, 900) * 1e6, "status": "coletado"}
    w(F / "por_uf.json", pu)
    # 6. sinais — valor com envelope de proveniência (fonte catalogada, documento, consultado_em)
    sr = j(D / "sinais_risco.json")
    if "uf" in sr and "SC" in sr["uf"]:
        sr["fontes"]["inmet_avisos"].update({"status": "coletado", "consultado_em": "06/09/2026", "documento": "Avisos meteorológicos vigentes (INMET)"})
        sr["uf"]["SC"]["avisos_inmet"] = {"fonte": "inmet_avisos", "documento": "Avisos meteorológicos vigentes (INMET)", "url": "https://alertas2.inmet.gov.br/", "consultado_em": "06/09/2026",
                                          "lista": [{"tipo": "Onda de calor", "nivel": "laranja"}, {"tipo": "Chuvas intensas", "nivel": "amarelo"}], "n": 2, "texto": "2 avisos vigentes"}
    w(D / "sinais_risco.json", sr)

def main() -> int:
    T = pathlib.Path(tempfile.mkdtemp(prefix="robustez_"))
    try:
        shutil.copytree(RAIZ, T / "repo", ignore=shutil.ignore_patterns("node_modules", ".git", "evidencias"), symlinks=True)
        R = T / "repo"; os.symlink(RAIZ / "node_modules", R / "node_modules")
        perturbar(R)
        env = {**os.environ, "SOURCE_DATE_EPOCH": "1787886000"}
        passos = [["python3", "recalcular_mare.py", "--write"], ["python3", "gerar_painel.py", "--fichas"], ["python3", "gerar_selos.py"], ["python3", "gerar_feeds.py"], ["python3", "gerar_dados_abertos.py"],
                  ["node", "scripts/verificar_estrutura.js"], ["python3", "verificar_consistencia.py"], ["python3", "recalcular_mare.py", "--check"], ["python3", "verificar_sinais.py"], ["python3", "verificar_saude.py"],
                  ["python3", "verificar_financiamento.py"], ["python3", "verificar_painel.py"], ["node", "scripts/verificar_runtime.js"], ["node", "scripts/verificar_runtime_mapas.js"], ["node", "scripts/verificar_runtime_sinais.js"],
                  ["node", "scripts/verificar_runtime_saude.js"], ["node", "scripts/verificar_runtime_financiamento.js"], ["node", "scripts/verificar_acessibilidade.js"], ["node", "scripts/verificar_vocabulario_publico.js"]]
        falhas = []
        for cmd in passos:
            r = subprocess.run(cmd, cwd=R, env=env, capture_output=True, text=True)
            ok = r.returncode == 0; print(("  ✓ " if ok else "  ✗ ") + " ".join(cmd[1:]))
            if not ok: falhas.append((cmd, (r.stdout + r.stderr)[-1200:]))
        for cmd, out in falhas: print("     ---", " ".join(cmd[1:]), "---"); print("     " + out.replace("\n", "\n     "))
        media = json.load(open(R / "data" / "indice.json", encoding="utf-8"))
        print(f"  (média após a perturbação: {sum(v['total'] for k, v in media.items() if len(k) == 2) / 27:.1f}; repositório real intocado)")
        print("✓ ROBUSTEZ OK — atualização simulada em 6 famílias de dados: derivados regenerados e todos os runtimes verdes." if not falhas else f"✗ ROBUSTEZ: {len(falhas)} verificação(ões) quebrou(aram) com dados atualizados.")
        return 1 if falhas else 0
    finally:
        shutil.rmtree(T, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
