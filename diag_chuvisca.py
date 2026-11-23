import sys, struct, traceback, re, collections
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
import julgar_e_aplicar_descobertas as j
U = ("https://rsgovbr-my.sharepoint.com/personal/casa-militar_casamilitar_rs_gov_br/Documents/Casa%20Militar/SUBCHEFIAS/"
     "SUBCHEFIA%20DE%20PROTE%C3%87%C3%83O%20E%20DEFESA%20CIVIL/3.%20Departamento%20de%20Gest%C3%A3o%20de%20Riscos/"
     "Divis%C3%A3o%20T%C3%A9cnica%20de%20Riscos/Planos%20de%20conting%C3%AAncia/TODOS%20PLANCONS%20RECEBIDOS/CREPDEC%2001/PLANCON%20-%20CHUVISCA.doc")
raw = j.obter_documento(U, 120, "diagnóstico Chuvisca")
print("DIAG bytes", len(raw), "magic", raw[:8].hex(), "versao", struct.unpack_from("<HH", raw, 24), "ss", 1 << struct.unpack_from("<H", raw, 30)[0])
try:
    t = j.texto_de_doc_binario(raw); print("DIAG texto", len(t), "letras", sum(c.isalpha() for c in t)); print("DIAG inicio", re.sub(r"\s+", " ", t)[:600])
except Exception:
    print("DIAG EXC", traceback.format_exc()[-900:])
import struct
u16 = lambda b, o: struct.unpack_from("<H", b, o)[0]; u32 = lambda b, o: struct.unpack_from("<I", b, o)[0]
ss = 512; setor = lambda i: raw[(i + 1) * ss:(i + 2) * ss]
difat = [x for x in struct.unpack_from("<109I", raw, 76) if x < 0xFFFFFFFA]
fat = [x for i in difat for x in struct.unpack("<128I", setor(i))]
def cadeia(s):
    out = []
    while s < 0xFFFFFFFA and len(out) < 20000: out.append(s); s = fat[s]
    return out
d = b"".join(setor(i) for i in cadeia(u32(raw, 48)))
print("DIAG dir setores", len(cadeia(u32(raw, 48))))
for o in range(0, len(d), 128):
    n = u16(d, o + 64)
    if n: print("DIAG ent", o // 128, repr(d[o:o + n - 2].decode("utf-16-le", "ignore")), "tipo", d[o + 66], "ini", u32(d, o + 116), "tam", u32(d, o + 120))
doc = b"".join(setor(i) for i in cadeia(0))
print("DIAG doc", len(doc), "wIdent", hex(u16(doc, 0)), "nFib", hex(u16(doc, 2)), "flags", hex(u16(doc, 10)), "fcMin", u32(doc, 24), "fcMac", u32(doc, 28), "ccpText", u32(doc, 0x4C), "fcClx", u32(doc, 0x1A2), "lcbClx", u32(doc, 0x1A6))
