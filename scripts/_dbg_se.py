import json,sys
sys.path.insert(0,'.')
import julgar_saude as j, coletores_base as cb
url="https://saude.se.gov.br/wp-content/uploads/2026/07/Plano-de-Contingencia_2026-2027.pdf"
corpo=cb.buscar(url,timeout=150)
print("BYTES",len(corpo),corpo[:8],cb.sha256(corpo))
t=j.texto_do_documento(corpo,url)
print("TEXTO",len(t),repr(t[:600]))
tit="Plano de Contingência 2026-2027 (SES-SE)"
print("TITULO",j.titulo_do_documento(t,tit,url))
print("RISCO",j.risco_do_documento(j.titulo_do_documento(t,tit,url),t))
print("FAM",j.juiz.etapa5_familia_de_risco(t)[:2])
inst=j.o_que_institui(t); pt=('instrumento' in inst and j.juiz.RE_TIPO_E_NUMERO.search(t) is None)
v=j.julgar_camada_saude(t,'SE',url,pt,tit)
print("VEREDITO",v['promove'],v['motivo'])
for k,x in v['criterios'].items(): print(k,str(x)[:300])
