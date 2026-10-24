import json
p="data/promocoes_automaticas.json"
d=json.load(open(p,encoding="utf-8"))
n=0
def varrer(o):
    global n
    if isinstance(o,dict):
        m=o.get("nao_aplicado")
        if isinstance(m,dict) and str(m.get("motivo","")).startswith("documento não pôde ser preservado"):
            del o["nao_aplicado"]; n+=1
        for v in o.values(): varrer(v)
    elif isinstance(o,list):
        for v in o: varrer(v)
varrer(d)
json.dump(d,open(p,"w",encoding="utf-8"),ensure_ascii=False,indent=1)
print("marcas limpas:",n)
