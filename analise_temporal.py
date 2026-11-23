"""
Script: analise_temporal.py
Descrição: Análise temporal mensal dos sinistros da PRF (datatran2026.csv).
           - Conversão para datetime
           - Agrupamento mensal (Jan a Set/2026): Sinistros, Mortos e Feridos Graves
           - Cruzamento por Fase do Dia (Pleno dia, Plena Noite, Amanhecer, Anoitecer)
           - Explicação didática de groupby e agg
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
# 1. CONVERSÃO DE FORMATO PARA DATETIME E CRIAÇÃO DO CAMPO MENSAL
# ------------------------------------------------------------------------------
# pd.to_datetime converte a string no formato 'AAAA-MM-DD' em tipo datetime nativo
df['data_inversa'] = pd.to_datetime(df['data_inversa'])

# dt.to_period('M') agrupa as datas pelo período do mês (ex: 2026-01, 2026-02...)
df['ano_mes'] = df['data_inversa'].dt.to_period('M')

# Mapeamento opcional para exibir o nome dos meses em português
nomes_meses = {
    '2026-01': '01 - Janeiro',
    '2026-02': '02 - Fevereiro',
    '2026-03': '03 - Março',
    '2026-04': '04 - Abril',
    '2026-05': '05 - Maio',
    '2026-06': '06 - Junho',
    '2026-07': '07 - Julho',
    '2026-08': '08 - Agosto',
    '2026-09': '09 - Setembro'
}
df['mes_nome'] = df['ano_mes'].astype(str).map(nomes_meses)


# ------------------------------------------------------------------------------
# 2. EVOLUÇÃO MENSAL: TOTAL DE SINISTROS, MORTOS E FERIDOS GRAVES
# ------------------------------------------------------------------------------
# O método .groupby('mes_nome') particiona os dados em subgrupos (um para cada mês).
# O método .agg() aplica operações específicas para cada coluna:
#   - 'id': 'count' conta a quantidade de registros (sinistros) naquele mês.
#   - 'mortos': 'sum' soma o número total de óbitos no mês.
#   - 'feridos_graves': 'sum' soma as vítimas com lesões graves no mês.
evolucao_mensal = df.groupby('mes_nome').agg(
    total_sinistros=('id', 'count'),
    total_mortos=('mortos', 'sum'),
    total_feridos_graves=('feridos_graves', 'sum')
).reset_index()

# Cálculo do percentual de letalidade mês a mês
evolucao_mensal['letalidade (%)'] = (
    (evolucao_mensal['total_mortos'] / evolucao_mensal['total_sinistros']) * 100
).round(2)

print("=" * 80)
print("1. EVOLUÇÃO MENSAL DOS SINISTROS RODOVIÁRIOS (JANEIRO A SETEMBRO DE 2026)")
print("=" * 80)

# Formatação para impressão visual no terminal
tabela_mensal_impressao = evolucao_mensal.copy()
tabela_mensal_impressao.columns = ['Mês / Ano', 'Sinistros', 'Óbitos (Mortos)', 'Feridos Graves', 'Letalidade (%)']
tabela_mensal_impressao['Sinistros'] = tabela_mensal_impressao['Sinistros'].apply(lambda x: f"{x:,.0f}".replace(',', '.'))
tabela_mensal_impressao['Óbitos (Mortos)'] = tabela_mensal_impressao['Óbitos (Mortos)'].apply(lambda x: f"{x:,.0f}".replace(',', '.'))
tabela_mensal_impressao['Feridos Graves'] = tabela_mensal_impressao['Feridos Graves'].apply(lambda x: f"{x:,.0f}".replace(',', '.'))
tabela_mensal_impressao['Letalidade (%)'] = tabela_mensal_impressao['Letalidade (%)'].apply(lambda x: f"{x:.2f}%".replace('.', ','))

print(tabela_mensal_impressao.to_string(index=False))
print()


# ------------------------------------------------------------------------------
# 3. CRUZAMENTO DA INCIDÊNCIA POR FASE DO DIA (fase_dia)
# ------------------------------------------------------------------------------
# Aqui usamos .groupby() com múltiplas chaves: ['mes_nome', 'fase_dia']
# Isso agrupa os sinistros cruzando o mês com o momento do dia.
# Em seguida, .unstack() transforma as categorias de fase_dia em colunas da tabela.
print("=" * 80)
print("2. INCIDÊNCIA DE SINISTROS CRUZADA POR MÊS E FASE DO DIA")
print("=" * 80)

sinistros_fase_dia = (
    df.groupby(['mes_nome', 'fase_dia'])['id']
    .count()
    .unstack(fill_value=0)
)

# Reordenar colunas em ordem cronológica de um dia
ordem_fases = ['Amanhecer', 'Pleno dia', 'Anoitecer', 'Plena Noite']
sinistros_fase_dia = sinistros_fase_dia[[col for col in ordem_fases if col in sinistros_fase_dia.columns]]
sinistros_fase_dia['Total Mês'] = sinistros_fase_dia.sum(axis=1)

print(sinistros_fase_dia.to_string())
print()


# ------------------------------------------------------------------------------
# 4. APROFUNDAMENTO: MORTOS CRUZADOS POR MÊS E FASE DO DIA
# ------------------------------------------------------------------------------
print("=" * 80)
print("3. ÓBITOS (MORTOS) CRUZADOS POR MÊS E FASE DO DIA")
print("=" * 80)

mortos_fase_dia = (
    df.groupby(['mes_nome', 'fase_dia'])['mortos']
    .sum()
    .unstack(fill_value=0)
)
mortos_fase_dia = mortos_fase_dia[[col for col in ordem_fases if col in mortos_fase_dia.columns]]
mortos_fase_dia['Total Mortos'] = mortos_fase_dia.sum(axis=1)

print(mortos_fase_dia.to_string())
