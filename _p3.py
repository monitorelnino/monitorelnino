import pathlib
B = chr(92) + "b"
p = pathlib.Path("scripts/testar_cadencia_publicacao.py")
t = p.read_text(encoding="utf-8")
velho = '                      if re.search(r"" + d + r"s?", texto, re.IGNORECASE)}'
novo = '                      if re.search(r"%s" + d + r"s?%s" % (B, B), texto, re.IGNORECASE)}' % ()
novo = '                      if re.search("%s" + d + "s?%s" % (B, B), texto, re.IGNORECASE)}'
assert velho in t
p.write_text(t.replace(velho, novo), encoding="utf-8", newline="")
print(novo)
