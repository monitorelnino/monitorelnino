import json
d = json.load(open('data/declarado_nacional.json'))
m = d['municipios']
com_icm = sum(1 for x in m.values() if 'icm_var8_plano_contingencia' in x)
print(f'municipios com icm_var8: {com_icm}')
sim = sum(1 for x in m.values() if x.get('icm_var8_plano_contingencia')=='sim')
nao = sum(1 for x in m.values() if x.get('icm_var8_plano_contingencia')=='nao')
print(f'sim={sim} nao={nao}')
