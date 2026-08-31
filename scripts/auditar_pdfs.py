#!/usr/bin/env python3
"""Auditoria completa dos relatórios em PDF do cidadão (estado e município).

Monta uma cópia de index.html com dados e jsPDF embutidos e o gerador exposto,
depois roda dois auditores em navegador real (Playwright):
  1. scripts/auditar_pdfs_geracao.js — 27 estados + todos os municípios do IBGE:
     exceções, 6 seções, texto ruim (undefined/NaN/campos vazios/decimal com
     ponto), caracteres que o helvetica do jsPDF não desenha, páginas, título.
  2. scripts/auditar_pdfs_conteudo.js — cada registro municipal, cada emergência
     e cada estado aparecem com categoria/documento/fonte/status/capital certos.

Criada em 31/08/2026 depois que a amostra de 30 PDFs achou um botão quebrado e
dois furos de conteúdo — a partir daí, a regra é auditar os 5.598, não 30.
Requer: node_modules com playwright, jspdf (npm i --no-save jspdf playwright).
Uso: python3 scripts/auditar_pdfs.py
"""
import json, re, subprocess, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
TESTE = Path("/tmp/index_pdf_test.html")


def montar_html_instrumentado():
    """Embute dados e jsPDF, expõe o gerador e captura o texto de cada PDF em memória."""
    html = (RAIZ / "index.html").read_text(encoding="utf-8")
    anc_ini, anc_fim = "async function __load(){", "  __init();\n}"
    i = html.find(anc_ini); j = html.find(anc_fim, i) + len(anc_fim)
    m = re.search(r"\[(BR_GEOJSON[^\]]*)\] = await Promise\.all\(\n\s*\[([^\]]*)\]", html, re.S)
    variaveis = [v.strip() for v in m.group(1).split(",")]
    arquivos = re.findall(r"'([^']+)'", m.group(2))
    partes = [f"{v} = " + json.dumps(json.load(open(DATA / f"{f}.json", encoding="utf-8")), ensure_ascii=False) + ";"
              for v, f in zip(variaveis, arquivos)]
    bloco = ("async function __load(){\n  " + " ".join(partes) + "\n  MUN_REF = {};\n"
             "  __ref.forEach(m => (MUN_REF[m.uf] = MUN_REF[m.uf] || []).push(m.nome));\n"
             "  __ref.forEach(m => {\n    const c = String(m.codigo_ibge).padStart(7, '0');\n"
             "    MUN_COD[m.uf + '|' + m.nome] = c;\n    MUN_LATLON[m.uf + '|' + m.nome] = [m.lon, m.lat];\n"
             "    POP_UF[m.uf] = (POP_UF[m.uf] || 0) + (POP_CENSO[c] || 0);\n  });\n"
             "  Object.values(MUN_REF).forEach(a => a.sort((x,y) => x.localeCompare(y)));\n  __init();\n}")
    html = html[:i] + bloco + html[j:]
    jspdf = (RAIZ / "node_modules/jspdf/dist/jspdf.umd.min.js").read_text(encoding="utf-8")
    html = re.sub(r'<script src="https://cdnjs\.cloudflare\.com/ajax/libs/jspdf/[^"]*"[^>]*>\s*</script>',
                  lambda _: f"<script>{jspdf}</script>", html, flags=re.S)
    html = html.replace("function __init(){\n", "function __init(){\nwindow.__gerar = (uf, m) => gerarRelatorioCidadao(uf, m);\n", 1)
    hook = """<script>
(function(){ const J = window.jspdf.jsPDF;
  function Wrapped(opts){ const d = new J(opts); const buf = []; const oT = d.text.bind(d);
    d.text = function(txt){ buf.push(Array.isArray(txt) ? txt.join('\\n') : String(txt)); return oT.apply(null, arguments); };
    d.save = function(name){ window.__out = { name, pages: d.internal.getNumberOfPages(), text: buf.join('\\n') }; }; return d; }
  Wrapped.API = J.API; window.jspdf.jsPDF = Wrapped;
  window.__larguraTitulo = (s) => { const d = new J({unit:'pt',format:'a4'}); d.setFont('helvetica','bold'); d.setFontSize(22); return d.getTextWidth(s); };
})();
</script>
</head>"""
    TESTE.write_text(html.replace("</head>", hook, 1), encoding="utf-8")


def main():
    """Monta o HTML instrumentado e roda as duas auditorias; falha se qualquer uma falhar."""
    montar_html_instrumentado()
    ok = True
    for js in ("auditar_pdfs_geracao.js", "auditar_pdfs_conteudo.js"):
        print(f"\n$ node scripts/{js}")
        r = subprocess.run(["node", f"scripts/{js}"], cwd=RAIZ, capture_output=True, text=True)
        print(r.stdout[-1500:])
        if r.returncode != 0 or "problemas: 0" not in r.stdout.replace("problemas de conteúdo: 0", "problemas: 0"):
            ok = False
    print("\n✓ AUDITORIA DOS PDFs OK" if ok else "\n✗ AUDITORIA DOS PDFs: há problemas acima")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
