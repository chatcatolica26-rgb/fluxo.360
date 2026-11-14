"""Onde o painel está rodando: no computador (instalado/desenvolvimento) ou publicado na web.

Na web, todos os visitantes compartilham o mesmo servidor. Por isso, preferências e formulários
valem só para a visita de cada pessoa (ficam na sessão) e não são gravados em disco.
Detecção: variável FLUXO360_MODO_WEB=1 (ou "Secrets" do Streamlit Cloud) ou a pasta padrão
do Streamlit Community Cloud (/mount/src).
"""
import os
from pathlib import Path


def modo_web() -> bool:
    valor = os.environ.get("FLUXO360_MODO_WEB", "").strip().lower()
    if valor in ("1", "true", "sim"):
        return True
    if valor in ("0", "false", "nao", "não"):
        return False
    return Path.cwd().as_posix().startswith("/mount/src")
