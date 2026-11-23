"""
Script: analise_infraestrutura_causas.py
Descrição: Análise de Infraestrutura Viária e Causas de Acidentes (datatran2026.csv).
           1. Severidade e letalidade por Tipo de Pista (Simples, Dupla, Múltipla)
           2. Comparação entre Top 10 causas por Volume vs Top 10 causas por Óbitos
"""

from pathlib import Path
import pandas as pd

# ------------------------------------------------------------------------------
# 0. CARREGAMENTO DOS DADOS
# ------------------------------------------------------------------------------
caminho_arquivo = Path('data/datatran2026.csv')
if not caminho_arquivo.exists():
    caminho_arquivo = Path('Projeto_transito/data/datatran2026.csv')

df = pd.read_csv(caminho_arquivo, sep=';', encoding='latin1')


# ------------------------------------------------------------------------------
# 1. INFRAESTRUTURA VIÁRIA: ANÁLISE POR TIPO DE PISTA
# ------------------------------------------------------------------------------
print("=" * 80)
print("1. GRAVIDADE E LETALIDADE POR TIPO DE PISTA")
print("=" * 80)

# Agrupamento por 'tipo_pista' com agregação de sinistros, mortos e feridos graves
pista_agrupada = df.groupby('tipo_pista').agg(
    sinistros=('id', 'count'),
    mortos=('mortos', 'sum'),
    feridos_graves=('feridos_graves', 'sum'),
    veiculos=('veiculos', 'sum')
).reset_index()

# Cálculo das métricas de proporção e severidade
total_sinistros_geral = len(df)
total_mortos_geral = df['mortos'].sum()

pista_agrupada['sinistros_share (%)'] = (pista_agrupada['sinistros'] / total_sinistros_geral * 100).round(2)
pista_agrupada['mortos_share (%)'] = (pista_agrupada['mortos'] / total_mortos_geral * 100).round(2)
pista_agrupada['taxa_letalidade (%)'] = (pista_agrupada['mortos'] / pista_agrupada['sinistros'] * 100).round(2)

# Ordenação pelo volume de sinistros
pista_agrupada = pista_agrupada.sort_values(by='sinistros', ascending=False)

# Exibição formatada
pista_formatada = pista_agrupada.copy()
pista_formatada.columns = [
    'Tipo de Pista', 'Sinistros', 'Óbitos (Mortos)', 'Feridos Graves', 'Veículos',
    '% dos Sinistros', '% dos Óbitos', 'Taxa de Letalidade (%)'
]
pista_formatada['Sinistros'] = pista_formatada['Sinistros'].apply(lambda x: f"{x:,.0f}".replace(',', '.'))
pista_formatada['Óbitos (Mortos)'] = pista_formatada['Óbitos (Mortos)'].apply(lambda x: f"{x:,.0f}".replace(',', '.'))
pista_formatada['Feridos Graves'] = pista_formatada['Feridos Graves'].apply(lambda x: f"{x:,.0f}".replace(',', '.'))
pista_formatada['Veículos'] = pista_formatada['Veículos'].apply(lambda x: f"{x:,.0f}".replace(',', '.'))
pista_formatada['% dos Sinistros'] = pista_formatada['% dos Sinistros'].apply(lambda x: f"{x:.2f}%".replace('.', ','))
pista_formatada['% dos Óbitos'] = pista_formatada['% dos Óbitos'].apply(lambda x: f"{x:.2f}%".replace('.', ','))
pista_formatada['Taxa de Letalidade (%)'] = pista_formatada['Taxa de Letalidade (%)'].apply(lambda x: f"{x:.2f}%".replace('.', ','))

print(pista_formatada.to_string(index=False))
print()


# ------------------------------------------------------------------------------
# 2. CAUSAS DE ACIDENTES: VOLUME VS LETALIDADE (ÓBITOS)
# ------------------------------------------------------------------------------
print("=" * 80)
print("2.1. TOP 10 CAUSAS COM MAIOR VOLUME DE OCORRÊNCIAS")
print("=" * 80)

causas_df = df.groupby('causa_acidente').agg(
    sinistros=('id', 'count'),
    mortos=('mortos', 'sum'),
    feridos_graves=('feridos_graves', 'sum')
).reset_index()

causas_df['letalidade (%)'] = (causas_df['mortos'] / causas_df['sinistros'] * 100).round(2)

# Top 10 por volume de ocorrências
top10_volume = causas_df.sort_values(by='sinistros', ascending=False).head(10).copy()
top10_volume['Rank'] = range(1, 11)
top10_volume_view = top10_volume[['Rank', 'causa_acidente', 'sinistros', 'mortos', 'letalidade (%)']].copy()
top10_volume_view.columns = ['#', 'Causa do Acidente', 'Sinistros', 'Óbitos', 'Letalidade (%)']
top10_volume_view['Sinistros'] = top10_volume_view['Sinistros'].apply(lambda x: f"{x:,.0f}".replace(',', '.'))
top10_volume_view['Óbitos'] = top10_volume_view['Óbitos'].apply(lambda x: f"{x:,.0f}".replace(',', '.'))
top10_volume_view['Letalidade (%)'] = top10_volume_view['Letalidade (%)'].apply(lambda x: f"{x:.2f}%".replace('.', ','))

print(top10_volume_view.to_string(index=False))
print()

print("=" * 80)
print("2.2. TOP 10 CAUSAS MAIS LETAIS (MAIOR QUANTIDADE DE ÓBITOS)")
print("=" * 80)

# Top 10 por número total de mortos
top10_mortos = causas_df.sort_values(by='mortos', ascending=False).head(10).copy()
top10_mortos['Rank'] = range(1, 11)
top10_mortos_view = top10_mortos[['Rank', 'causa_acidente', 'mortos', 'sinistros', 'letalidade (%)']].copy()
top10_mortos_view.columns = ['#', 'Causa do Acidente', 'Óbitos', 'Sinistros', 'Letalidade (%)']
top10_mortos_view['Óbitos'] = top10_mortos_view['Óbitos'].apply(lambda x: f"{x:,.0f}".replace(',', '.'))
top10_mortos_view['Sinistros'] = top10_mortos_view['Sinistros'].apply(lambda x: f"{x:,.0f}".replace(',', '.'))
top10_mortos_view['Letalidade (%)'] = top10_mortos_view['Letalidade (%)'].apply(lambda x: f"{x:.2f}%".replace('.', ','))

print(top10_mortos_view.to_string(index=False))
