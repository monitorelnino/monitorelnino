#!/usr/bin/env python3
"""Rotina de conferência das contribuições de leitores (Netlify Forms).

Puxa as submissões do formulário "contribuicao" pela API do Netlify e monta a
fila de verificação humana, aplicando a triagem automática de completude do
protocolo (Metodologia §6): checagem de campos, domínio do link, existência do
município na base IBGE e duplicidade contra o banco publicado.

A rotina NUNCA escreve no banco de dados público: a entrada de qualquer registro
é decisão humana, após verificação documental (regra de ouro). A fila é gravada
em fila_contribuicoes/ (fora do versionamento, por conter possíveis e-mails).

Requer: NETLIFY_AUTH_TOKEN e NETLIFY_SITE_ID no ambiente.
Uso: python verificar_contribuicoes.py [--limpar]

C5 (auditoria 29/08/2026): em execução LOCAL, use sempre --limpar — a fila
contém possíveis e-mails e a flag apaga fila_contribuicoes/ ao final da
triagem, fechando a janela de retenção de dado pessoal na máquina do editor
(no CI o diretório já morre com o runner efêmero). O painel do Netlify é a
fonte de verdade para contato; a fila local é descartável por desenho.
"""
import datetime, json, os, pathlib, sys, urllib.parse, urllib.request

RAIZ = pathlib.Path(__file__).parent
DOMINIOS_OFICIAIS = (".gov.br", "diariomunicipal.com.br", "doe.", "dom.", "in.gov.br")

def main() -> int:
    """Puxa as submissões do formulário via API do Netlify, aplica a triagem automática de completude e grava a fila de revisão humana (JSON + Markdown) fora do versionamento."""
    token = os.environ.get("NETLIFY_AUTH_TOKEN")
    site = os.environ.get("NETLIFY_SITE_ID")
    if not (token and site):
        print("[aviso] NETLIFY_AUTH_TOKEN/NETLIFY_SITE_ID ausentes; conferência de contribuições pulada.")
        return 0
    url = f"https://api.netlify.com/api/v1/sites/{site}/submissions?access_token={token}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MonitorElNinoBrasil/1.0"})
        subs = json.load(urllib.request.urlopen(req, timeout=30))
    except Exception as e:
        print(f"[aviso] falha ao consultar a API do Netlify: {e}")
        return 0

    ref = json.load(open(RAIZ / "data" / "municipios_ibge_referencia.json", encoding="utf-8"))
    ibge = {(m["nome"].casefold(), m["uf"]) for m in ref}
    banco = json.load(open(RAIZ / "data" / "municipios.json", encoding="utf-8"))
    ja = {(m["nome"].casefold(), m["uf"]): m["categoria"] for m in banco}

    destino = RAIZ / "fila_contribuicoes"
    destino.mkdir(exist_ok=True)
    hoje = datetime.date.today().isoformat()
    fila, incompletas = [], []
    for s in subs:
        d = s.get("data", {})
        if d.get("bot-field"):
            continue
        item = {
            "recebida_em": s.get("created_at", "")[:10],
            "municipio": (d.get("municipio") or "").strip(),
            "uf": (d.get("uf") or "").strip().upper(),
            "tipo": d.get("tipo", ""),
            "numero_data": d.get("numero_data", ""),
            "link": d.get("link_oficial", ""),
            "observacoes": d.get("observacoes", ""),
            "email_contato": d.get("email_contato", ""),
        }
        checks = {
            "campos_obrigatorios": bool(item["municipio"] and item["uf"] and item["link"]),
            "municipio_existe_ibge": (item["municipio"].casefold(), item["uf"]) in ibge,
            "dominio_aparenta_oficial": any(t in urllib.parse.urlparse(item["link"]).netloc.lower() + urllib.parse.urlparse(item["link"]).path.lower() for t in DOMINIOS_OFICIAIS),
            "ja_no_banco": ja.get((item["municipio"].casefold(), item["uf"])),
        }
        item["triagem"] = checks
        (fila if checks["campos_obrigatorios"] and checks["municipio_existe_ibge"] else incompletas).append(item)

    json.dump({"gerada_em": hoje, "fila": fila, "incompletas": incompletas},
              open(destino / f"fila_{hoje}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    md = [f"# Fila de conferência de contribuições · {hoje}",
          f"\n{len(fila)} para verificação humana · {len(incompletas)} incompletas\n"]
    for i, it in enumerate(fila, 1):
        t = it["triagem"]
        md.append(f"## {i}. {it['municipio']}/{it['uf']} · {it['tipo']} · recebida {it['recebida_em']}")
        md.append(f"- Link: {it['link']}")
        md.append(f"- Ato: {it['numero_data'] or '(não informado)'}")
        if it["observacoes"]: md.append(f"- Obs.: {it['observacoes']}")
        md.append(f"- Triagem: domínio oficial aparente: {'sim' if t['dominio_aparenta_oficial'] else 'NÃO (conferir com atenção)'}"
                  f" · já no banco: {t['ja_no_banco'] or 'não'}")
        md.append("- [ ] URL abre e é fonte oficial  [ ] Ato confere (nº/data)  [ ] Categoria correta  [ ] Entrar no banco com canal de origem\n")
    open(destino / f"fila_{hoje}.md", "w", encoding="utf-8").write("\n".join(md))
    print(f"✓ Fila de conferência: {len(fila)} item(ns) para verificação humana, {len(incompletas)} incompleto(s) → fila_contribuicoes/fila_{hoje}.md")
    if "--limpar" in sys.argv:
        import shutil
        shutil.rmtree(destino, ignore_errors=True)
        print("✓ --limpar: fila_contribuicoes/ removida ao final da triagem (LGPD; C5 da auditoria de 29/08/2026)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
