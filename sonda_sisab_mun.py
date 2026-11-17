import sys; sys.path[:0] = ["scripts", "."]
import re,coletar_sisab as c
p=c.Sessao().pedir(c.RELATORIO).decode('utf-8','replace')
for m in re.finditer(r'<select[^>]*?(?:name|id)="([^"]+)"[^>]*>(.*?)</select>',p,re.S):
    ops=re.findall(r'<option value="([^"]*)"[^>]*>([^<]*)<',m.group(2))
    if len(ops)<80: print('SELECT',m.group(1),ops)
for m in re.finditer(r'<input[^>]*type="radio"[^>]*>',p): print('RADIO',m.group(0)[:200])
i=p.find('selectLinha'); print('CTX',re.sub(r'\s+',' ',p[i-1500:i+3000]))
