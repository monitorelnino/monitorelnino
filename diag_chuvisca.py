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
# nomes das correntes e FIB
u16 = lambda b, o: struct.unpack_from("<H", b, o)[0]; u32 = lambda b, o: struct.unpack_from("<I", b, o)[0]
ss = 1 << u16(raw, 30)
print("DIAG nFAT", u32(raw, 44), "dir", u32(raw, 48), "corte", u32(raw, 56), "miniFAT", u32(raw, 60), u32(raw, 64), "DIFAT", u32(raw, 68), u32(raw, 72))
i = raw.find("WordDocument".encode("utf-16-le")); print("DIAG pos nome WordDocument", i)
for nome in ("WordDocument", "1Table", "0Table", "Root Entry", "Data", "ObjectPool", "EncryptedPackage", "EncryptionInfo"):
    k = raw.find(nome.encode("utf-16-le"))
    if k >= 0: print("DIAG entrada", nome, "inicio", u32(raw, k + 116), "tam", u32(raw, k + 120))
# texto bruto: quantas sequências legíveis longas há no arquivo
lat = re.findall(rb"[A-Za-z\xc0-\xff ,.;:()\-]{40,}", raw); w = re.findall(rb"(?:[A-Za-z\xc0-\xff ,.;:()\-]\x00){40,}", raw)
print("DIAG runs cp1252", len(lat), "utf16", len(w))
for b in lat[:3]: print("DIAG lat", b[:150].decode("cp1252", "ignore"))
for b in w[:3]: print("DIAG w", b[:300].decode("utf-16-le", "ignore"))
