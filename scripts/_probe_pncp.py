import sys,urllib.parse,urllib.error
sys.path.insert(0,'.')
import coletores_base as cb
B="https://pncp.gov.br/api/search/"
V=[{"q":"plano de contingencia natal","tipos_documento":"edital","ordenacao":"-data","pagina":1,"tam_pagina":10,"status":"todos"},
{"q":"plano de contingencia natal","tipos_documento":"edital","pagina":1,"tam_pagina":10},
{"q":"plano de contingencia natal","pagina":1,"tam_pagina":10},
{"q":"plano de contingencia natal"},
{"q":"plano de contingencia natal","tipo_documento":"edital","ordenacao":"-data","pagina":1,"tam_pagina":10}]
for v in V:
    u=B+"?"+urllib.parse.urlencode(v)
    try:
        r=cb.buscar(u,timeout=30,origem="sondar_pncp_planos")
        print("OK",v.keys(),len(r),r[:300])
    except urllib.error.HTTPError as e:
        print("HTTP",e.code,list(v),e.read()[:300])
    except Exception as e:
        print("ERR",type(e).__name__,list(v),str(e)[:200])
