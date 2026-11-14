@echo off
title FLUXO360 - modo diagnostico
cd /d "%~dp0.."
echo Abrindo o painel com as mensagens visiveis.
echo Endereco: http://localhost:8360   (feche esta janela para encerrar)
echo.
".venv\Scripts\python.exe" -m streamlit run dashboard\app.py
pause
