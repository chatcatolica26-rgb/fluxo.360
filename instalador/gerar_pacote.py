"""Monta o pacote de instalação do FLUXO360 (rode na raiz do projeto, em qualquer sistema).

    python instalador/gerar_pacote.py
    python instalador/gerar_pacote.py --versao 1.0.1 --sem-demo

Gera:
  dist/FLUXO360/                         pasta usada pelo Inno Setup (FLUXO360.iss)
  dist/FLUXO360-Instalador-<versão>.zip  versão sem Setup.exe: descompactar e abrir "Instalar FLUXO360.bat"

Leva só o necessário para o cliente: painel, código de análise, configurações, planta e (opcional)
a análise de demonstração. Não leva testes, dados do MOT20, preferências locais nem o app.py antigo.
"""
from __future__ import annotations

import argparse
import shutil
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
IGNORAR = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", "*.pt", ".DS_Store")

COPIAR = [  # (origem, destino) relativos à raiz
    ("src", "src"),
    ("dashboard", "dashboard"),
    ("configs", "configs"),
    ("data/planta", "data/planta"),
    ("instalador", "instalador"),
    ("tools/calibrar_camera.py", "tools/calibrar_camera.py"),
    ("tools/analise_demo_opencv.py", "tools/analise_demo_opencv.py"),
    ("tools/gerar_rastros.py", "tools/gerar_rastros.py"),
    ("tools/gerar_video_demo.py", "tools/gerar_video_demo.py"),
    ("instalador/LEIA-ME.txt", "LEIA-ME.txt"),
    ("Instalar FLUXO360.bat", "Instalar FLUXO360.bat"),
]
NAO_LEVAR_DO_INSTALADOR = {"gerar_pacote.py", "FLUXO360.iss", "GERAR_INSTALADOR.md", "perfil.txt",
                           "instalacao_ok.txt", "LEIA-ME.txt"}


def _copiar(origem: Path, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    if origem.is_dir():
        shutil.copytree(origem, destino, ignore=IGNORAR, dirs_exist_ok=True)
    else:
        shutil.copy2(origem, destino)


def _tamanho(p: Path) -> str:
    total = sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.is_dir() else p.stat().st_size
    return f"{total / 1e6:.1f} MB"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--versao", default="1.0.0")
    ap.add_argument("--demo", help="pasta com análises de demonstração (padrão: data/demo)")
    ap.add_argument("--sem-demo", action="store_true", help="não incluir análise de demonstração nem vídeo")
    ap.add_argument("--video", default="data/raw/shopping/praca_eventos.mp4")
    a = ap.parse_args()

    dist = RAIZ / "dist"
    pacote = dist / "FLUXO360"
    if pacote.exists():
        shutil.rmtree(pacote)
    for origem, destino in COPIAR:
        o = RAIZ / origem
        if not o.exists():
            raise SystemExit(f"Faltando no projeto: {origem}")
        _copiar(o, pacote / destino)
    for nome in NAO_LEVAR_DO_INSTALADOR:
        (pacote / "instalador" / nome).unlink(missing_ok=True)
    for pasta in ("data/processed/shopping", "data/raw/shopping", "data/acompanhamento"):
        (pacote / pasta).mkdir(parents=True, exist_ok=True)

    if not a.sem_demo:
        demo = Path(a.demo) if a.demo else RAIZ / "data/demo"
        if demo.is_dir() and any(demo.glob("**/run_info.json")):
            destino = pacote / "data/demo" / (demo.name if demo.name != "demo" else "")
            _copiar(demo, destino)
            print("Análise de demonstração:", demo, _tamanho(demo))
        else:
            print("Aviso: nenhuma análise de demonstração em data/demo (o painel abre sem a aba de vídeo real).")
        video = RAIZ / a.video
        if video.is_file():
            _copiar(video, pacote / a.video)
            print("Vídeo de exemplo:", video.name, _tamanho(video))

    (pacote / "instalador" / "versao.txt").write_text(a.versao, encoding="ascii")
    zip_path = dist / f"FLUXO360-Instalador-{a.versao}.zip"
    zip_path.unlink(missing_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for f in sorted(pacote.rglob("*")):
            if f.is_file():
                z.write(f, Path("FLUXO360") / f.relative_to(pacote))
    print(f"Pasta do pacote: {pacote} ({_tamanho(pacote)})")
    print(f"Zip para o cliente: {zip_path} ({_tamanho(zip_path)})")
    print("Para o Setup.exe: abra instalador/FLUXO360.iss no Inno Setup e compile.")


if __name__ == "__main__":
    main()
