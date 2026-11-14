"""Gera as bases (PNG) do Capim Dourado a partir da Planta Mix em PDF.

- versão "original": tudo como no PDF (útil para achar pontos de calibração)
- versão "limpa": sem textos, logos, cotas, hachuras, eixos e vagas (fundo do mapa de calor)
Escala tirada das cotas do próprio desenho.
"""
import re, subprocess, sys, pypdf
from pypdf.generic import DecodedStreamObject, NameObject

SRC = sys.argv[1] if len(sys.argv) > 1 else "planta.pdf"

PISOS = {
    # página (0-based), m por ponto PDF, px por metro, recorte em pontos PDF (x0, y0, x1, y1; y para baixo)
    "terreo":            dict(page=1, m_per_pt=0.3030, px_per_m=10, crop=(414, 54, 1999, 1260)),
    "praca_alimentacao": dict(page=2, m_per_pt=0.0558, px_per_m=40, crop=(290, 80, 2300, 1480)),
}

OCULTAR = re.compile(
    r"COTAS|DIMENS|HUMA|HATCH|HACH|EIXOS|^EIX$|\$EIX$|FO-Eixos|AUX|LOGOS|SIMB|CHAM|"
    r"CCY_pintura|CCY_vagas|CCY-VAGAS|^VGA$|TX|TEXTO|ANNO", re.I)

def limpar_pagina(writer, page):
    props = page["/Resources"].get("/Properties", {})
    nome = {k[1:]: str(v.get_object().get("/Name")) for k, v in props.items()}
    c = page.get_contents().get_data().decode("latin1")
    def bloco(m):
        if OCULTAR.search(nome.get(m.group(1), "")):
            return ""
        corpo = re.sub(r"\bBT\b.*?\bET\b", "", m.group(2), flags=re.S)   # textos
        corpo = re.sub(r"/I\d+ Do", "", corpo)                              # imagens/logos
        return f"/OC/{m.group(1)} BDC{corpo}EMC"
    c = re.sub(r"/OC/(oc\d+) BDC(.*?)EMC", bloco, c, flags=re.S)
    s = DecodedStreamObject(); s.set_data(c.encode("latin1"))
    page[NameObject("/Contents")] = writer._add_object(s)

def render(pdf, page, cfg, out):
    dpi = cfg["m_per_pt"] * cfg["px_per_m"] * 72
    k = dpi / 72
    x0, y0, x1, y1 = cfg["crop"]
    subprocess.run(["pdftoppm", "-png", "-singlefile", "-r", f"{dpi:.4f}",
                    "-f", str(page + 1), "-l", str(page + 1),
                    "-x", str(round(x0 * k)), "-y", str(round(y0 * k)),
                    "-W", str(round((x1 - x0) * k)), "-H", str(round((y1 - y0) * k)),
                    pdf, out], check=True)

w = pypdf.PdfWriter(clone_from=SRC)
for cfg in PISOS.values():
    limpar_pagina(w, w.pages[cfg["page"]])
w.write("_limpa.pdf")

for nome, cfg in PISOS.items():
    render(SRC, cfg["page"], cfg, f"{nome}_original")
    render("_limpa.pdf", cfg["page"], cfg, f"{nome}_limpa")
    print(nome, "ok")
