import sys; sys.path[:0] = ["scripts", "."]
import time, urllib.parse, coletar_sisab as c
s = c.Sessao(timeout=600)
form = c.formulario(s.pedir(c.RELATORIO).decode("utf-8", "replace"))
url = urllib.parse.urljoin(c.RELATORIO, form["acao"])
comps = sorted(form["competencias"])[-3:]
campos = [(k, ("MUN.CO_MUNICIPIO_IBGE" if k == "selectLinha" else v)) for k, v in c.corpo_da_consulta(form, comps, c.DESFECHOS["diarreias"]["codigos"])]
t = time.time(); txt = s.pedir(url, campos).decode("latin-1"); print("SEG", round(time.time()-t), "BYTES", len(txt), "COMPS", comps)
ln = txt.splitlines(); print("LINHAS", len(ln))
for l in ln[:25]: print("L", l[:300])
for l in ln[-8:]: print("F", l[:300])
