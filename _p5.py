import pathlib
B = (chr(92) + "b").encode()
p = pathlib.Path("scripts/testar_cadencia_publicacao.py")
b = p.read_bytes()
velho = b'                      if re.search(r"" + d + r"s?", texto, re.IGNORECASE)}'
novo = b'                      if re.search("' + B + b'" + d + "s?' + B + b'", texto, re.IGNORECASE)}'
assert velho in b
p.write_bytes(b.replace(velho, novo))
print(novo.decode())
