"""Gera o diagrama "Do vídeo à decisão": 3 imagens reais -> FLUXO360 -> benefícios.

    python tools/gerar_diagrama_impacto.py                     # usa a análise mais recente (data/processed ou data/demo)
    python tools/gerar_diagrama_impacto.py <pasta_da_analise>

Salva dashboard/assets/diagrama_impacto.png (1920x1080, pronto para slides).
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
FUNDO, TEXTO, CINZA, BORDA = (247, 248, 251), (17, 24, 39), (90, 99, 115), (214, 219, 228)
AZUL, VERDE, ROXO = (59, 130, 246), (52, 168, 120), (124, 92, 230)


def fonte(tam: int, negrito: bool = False):
    nomes = ["DejaVuSans-Bold.ttf", "arialbd.ttf", "segoeuib.ttf"] if negrito else ["DejaVuSans.ttf", "arial.ttf", "segoeui.ttf"]
    for n in nomes:
        for base in ("", "/usr/share/fonts/truetype/dejavu/", "C:/Windows/Fonts/"):
            try:
                return ImageFont.truetype(base + n, tam)
            except OSError:
                continue
    return ImageFont.load_default()


def encaixar(img: Image.Image, larg: int, alt: int) -> Image.Image:
    img = img.convert("RGB")
    k = min(larg / img.width, alt / img.height)
    return img.resize((int(img.width * k), int(img.height * k)), Image.LANCZOS)


def seta(d: ImageDraw.ImageDraw, x0, y0, x1, y1, cor=(70, 78, 92), larg=5):
    import math
    d.line([(x0, y0), (x1, y1)], fill=cor, width=larg)
    ang = math.atan2(y1 - y0, x1 - x0)
    tam = 20
    p1 = (x1 - tam * math.cos(ang - 0.45), y1 - tam * math.sin(ang - 0.45))
    p2 = (x1 - tam * math.cos(ang + 0.45), y1 - tam * math.sin(ang + 0.45))
    d.polygon([(x1, y1), p1, p2], fill=cor)


def caixa(d, x0, y0, x1, y1, fundo=(255, 255, 255), borda=BORDA, larg=2, raio=18):
    d.rounded_rectangle([x0, y0, x1, y1], radius=raio, fill=fundo, outline=borda, width=larg)


def lista(d, x, y, itens, tam=27, cor=TEXTO, espaco=50):
    for t in itens:
        d.text((x, y), "•", font=fonte(tam, True), fill=cor)
        d.text((x + 28, y), t, font=fonte(tam), fill=cor)
        y += espaco
    return y


def gerar(pasta: Path, destino: Path) -> Path:
    img = Image.new("RGB", (W, H), FUNDO)
    d = ImageDraw.Draw(img)
    d.text((60, 42), "Do vídeo à decisão", font=fonte(54, True), fill=TEXTO)
    d.text((60, 112), "O FLUXO360 transforma o movimento das pessoas em ações para o lojista e para a "
                      "administração do shopping", font=fonte(27), fill=CINZA)

    # 1) três imagens reais
    fontes = [("quadro_exemplo_deteccoes.png", "1. Pessoas identificadas", "cada pessoa vira um ponto no chão"),
              ("trajetorias_planta.png", "2. Rastreio dos caminhos", "por onde cada pessoa andou na planta"),
              ("mapa_permanencia_rastros.png", "3. Mapa de calor", "onde há mais movimento e permanência")]
    x0, y = 60, 185
    alt_card, larg_card, gap = 258, 700, 22
    centros = []
    for nome, titulo, sub in fontes:
        caixa(d, x0, y, x0 + larg_card, y + alt_card)
        arq = pasta / nome
        if not arq.is_file() and nome == "mapa_permanencia_rastros.png":
            arq = pasta / "mapa_permanencia_sobreposto.png"
        if arq.is_file():
            foto = Image.open(arq)
            if nome == "mapa_permanencia_rastros.png":          # tira a legenda de baixo
                foto = foto.crop((0, 0, foto.width, int(foto.height * 0.92)))
            foto = encaixar(foto, 330, alt_card - 28)
            img.paste(foto, (x0 + 14, y + (alt_card - foto.height) // 2))
        tx = x0 + 362
        d.text((tx, y + 70), titulo.split(". ")[0] + ".", font=fonte(40, True), fill=AZUL)
        palavras = titulo.split(". ")[1]
        d.text((tx, y + 120), palavras, font=fonte(24, True), fill=TEXTO)
        linhas, atual = [], ""
        for p in sub.split():
            if len(atual + " " + p) > 24:
                linhas.append(atual)
                atual = p
            else:
                atual = (atual + " " + p).strip()
        linhas.append(atual)
        for k, l in enumerate(linhas):
            d.text((tx, y + 158 + 30 * k), l, font=fonte(21), fill=CINZA)
        centros.append(y + alt_card // 2)
        y += alt_card + gap

    # 2) a ferramenta
    fx0, fx1, fy0, fy1 = 860, 1210, 330, 760
    caixa(d, fx0, fy0, fx1, fy1, fundo=(235, 242, 255), borda=AZUL, larg=4, raio=26)
    icone = Path(__file__).resolve().parents[1] / "instalador" / "fluxo360.ico"
    if icone.is_file():
        ic = Image.open(icone).convert("RGBA").resize((130, 130), Image.LANCZOS)
        img.paste(ic, ((fx0 + fx1) // 2 - 65, fy0 + 34), ic)
    d.text(((fx0 + fx1) // 2, fy0 + 200), "FLUXO360", font=fonte(44, True), fill=TEXTO, anchor="mm")
    d.text(((fx0 + fx1) // 2, fy0 + 246), "inteligência de fluxo", font=fonte(24), fill=CINZA, anchor="mm")
    lista(d, fx0 + 30, fy0 + 290, ["quando as pessoas passam", "onde elas param", "para onde elas vão"],
          tam=20, cor=TEXTO, espaco=38)
    for cy in centros:
        seta(d, x0 + larg_card + 8, cy, fx0 - 12, (fy0 + fy1) // 2 + (cy - (fy0 + fy1) // 2) // 3)

    # 3) benefícios
    bx0, bx1 = 1290, 1870
    blocos = [
        ("Para o lojista", VERDE, (236, 248, 242), 185,
         ["Produto isca no lugar certo", "Equipe e caixas no horário de pico", "Vitrine e ofertas para quem passa",
          "Resultado medido: antes e depois"]),
        ("Para a administração", ROXO, (242, 238, 253), 585,
         ["Quiosques nos pontos de maior fluxo", "Preço do espaço pelo movimento", "Pontos mortos detectados",
          "Estratégias para aquecer pontos frios", "Limpeza e segurança na hora certa"]),
    ]
    for titulo, cor, fundo_b, by0, itens in blocos:
        by1 = by0 + 90 + 50 * len(itens)
        caixa(d, bx0, by0, bx1, by1, fundo=fundo_b, borda=cor, larg=4, raio=22)
        d.text((bx0 + 34, by0 + 26), titulo, font=fonte(36, True), fill=cor)
        lista(d, bx0 + 30, by0 + 88, itens, tam=25)
        seta(d, fx1 + 10, (fy0 + fy1) // 2 + (by0 + by1) // 2 // 8 - 70, bx0 - 14, (by0 + by1) // 2, cor=cor)

    d.text((60, H - 46), "Imagens: vídeo real da Praça de Eventos do Capim Dourado Shopping, projetado na planta "
                         "oficial (pessoas anonimizadas).", font=fonte(19), fill=CINZA)
    destino.parent.mkdir(parents=True, exist_ok=True)
    img.save(destino, optimize=True)
    return destino


if __name__ == "__main__":
    raiz = Path(__file__).resolve().parents[1]
    if len(sys.argv) > 1:
        alvo = Path(sys.argv[1])
    else:
        execs = sorted((raiz / "data/processed/shopping").glob("*/run_info.json")) or \
            sorted((raiz / "data/demo").glob("*/run_info.json"))
        if not execs:
            raise SystemExit("Nenhuma análise encontrada.")
        alvo = execs[-1].parent
    print("Diagrama:", gerar(alvo, raiz / "dashboard/assets/diagrama_impacto.png"))
