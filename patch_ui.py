import re
p = "streamlit_app.py"
s = open(p, encoding="utf-8").read()

a = s.rfind("st.markdown(", 0, s.index("<style>"))
marker = "unsafe_allow_html=True,\n)"
b = s.index(marker, s.index("</style>")) + len(marker)
s = s[:a] + "from ui_theme import BRAND_HTML, apply_theme\n\napply_theme()" + s[b:]

s, n = re.subn(
    r'^(\s*)st\.markdown\(\'<div class="brand">.*$',
    lambda m: m.group(1) + "st.markdown(BRAND_HTML, unsafe_allow_html=True)",
    s, flags=re.M,
)
assert n == 1, "brand line not found"
open(p, "w", encoding="utf-8").write(s)
print("patched OK")
