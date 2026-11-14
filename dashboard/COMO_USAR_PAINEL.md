# Painel FLUXO360 (Streamlit)

Painel com as 6 telas da apresentação: Visão geral, Mapa de movimentação, Análise de ambientes,
Diagnósticos e oportunidades, Recomendações e Relatórios.

## Instalar (uma vez)
Na pasta do projeto, com o `.venv` ativo:
```powershell
uv pip install -r dashboard/requirements-dashboard.txt
```

## Abrir
```powershell
streamlit run dashboard/app.py
```
O navegador abre sozinho em http://localhost:8501. Não use o botão ▶ (Run Python File) do VS Code:
um painel Streamlit só aparece quando é aberto pelo comando `streamlit run`.

## De onde vêm os dados
- **Números das telas:** simulados, iguais aos da apresentação (arquivo `dashboard/dados_simulados.py`).
- **Aba "Vídeo real" do Mapa de movimentação:** resultados de `python -m src.experiments.run_shopping`,
  lidos de `data/processed/shopping/`. Aparecem sozinhos depois da primeira análise.
- **Acompanhamento dos planos (Recomendações):** salvo em `data/acompanhamento/planos.csv`.

O `app.py` antigo, na raiz do projeto, continua funcionando como antes.
