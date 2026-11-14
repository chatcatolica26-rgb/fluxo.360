"""Recomendações do FLUXO360 para o lojista e a administração (dados simulados do painel)."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dashboard"))
import insights  # noqa: E402


def test_janela_de_pico_pega_horas_seguidas_perto_do_maximo():
    serie = pd.Series([10, 20, 90, 100, 85, 30, 10, 5, 5, 5, 5, 5])
    ini, fim, frac = insights.janela_de_pico(serie)
    assert (ini, fim) == (12, 14)
    assert abs(frac - 275 / 370) < 1e-9        # 90 + 100 + 85 de um total de 370


def test_lojista_tem_equipe_isca_e_vitrine():
    temas = [r["tema"] for r in insights.lojista("Corredor A")]
    assert temas[:3] == ["Equipe e caixas", "Produto isca", "Vitrine e ofertas"]


def test_corredor_frio_ganha_recomendacao_de_negociar_aquecimento():
    temas = [r["tema"] for r in insights.lojista("Corredor B")]
    assert "Negociar com o shopping" in temas


def test_pontos_mortos_sao_regioes_com_menos_de_2_porcento():
    mortos = insights.pontos_mortos()
    assert set(mortos.regiao) == {"Corredor B · final", "Corredor B · trecho central"}
    assert (mortos.participacao < 0.02).all()


def test_valor_do_ponto_tem_faixas_coerentes_com_o_fluxo():
    vp = insights.valor_do_ponto()
    assert vp.iloc[0]["Região"] == "Praça de Alimentação" and vp.iloc[0]["Faixa"] == "Premium"
    assert vp.iloc[-1]["Faixa"] == "Incentivo"
    assert vp["Multiplicador sugerido"].between(0.5, 2.0).all()


def test_administracao_cobre_os_temas_do_orientador():
    temas = {r["tema"] for r in insights.administracao()}
    assert {"Pontos mortos", "Aquecer pontos frios", "Quiosques", "Preço do espaço"} <= temas
