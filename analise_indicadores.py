"""
Script: analise_indicadores.py
Descrição: Continuação da Análise Exploratória (EDA) dos dados da PRF (datatran2026.csv).
           - Classificação dos acidentes (contagem e percentual)
           - Totais gerais de sinistros, óbitos, feridos graves e veículos
           - Agrupamento por rodovia (BR) e cálculo do Índice de Letalidade
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
# 1. CLASSIFICAÇÃO DOS ACIDENTES (CONTAGEM E PERCENTUAL)
# ------------------------------------------------------------------------------
print("=" * 70)
print("1. CLASSIFICAÇÃO DOS SINISTROS (DISTRIBUIÇÃO ABSOLUTA E RELATIVA)")
print("=" * 70)

contagem = df['classificacao_acidente'].value_counts(dropna=False)
percentual = df['classificacao_acidente'].value_counts(dropna=False, normalize=True) * 100

df_classificacao = pd.DataFrame({
    'Classificação': contagem.index.fillna('Não informado / Nulo'),
    'Total de Sinistros': contagem.values,
    'Percentual (%)': percentual.round(2).values
})

# Formatação visual para o terminal
df_classificacao_formatado = df_classificacao.copy()
df_classificacao_formatado['Total de Sinistros'] = df_classificacao_formatado['Total de Sinistros'].apply(lambda x: f"{x:,.0f}".replace(',', '.'))
df_classificacao_formatado['Percentual (%)'] = df_classificacao_formatado['Percentual (%)'].apply(lambda x: f"{x:.2f}%".replace('.', ','))

print(df_classificacao_formatado.to_string(index=False))
print()


# ------------------------------------------------------------------------------
# 2. TOTAIS GERAIS DE SINISTROS, ÓBITOS, FERIDOS GRAVES E VEÍCULOS
# ------------------------------------------------------------------------------
print("=" * 70)
print("2. TOTAIS GERAIS (MÉTRICAS NACIONAIS CONSOLIDADAS)")
print("=" * 70)

total_sinistros = len(df)
total_obitos = int(df['mortos'].sum())
total_feridos_graves = int(df['feridos_graves'].sum())
total_veiculos = int(df['veiculos'].sum())

print(f"Total de Sinistros Registrados: {total_sinistros:>10,}".replace(',', '.'))
print(f"Total de Óbitos (Mortos):        {total_obitos:>10,}".replace(',', '.'))
print(f"Total de Feridos Graves:         {total_feridos_graves:>10,}".replace(',', '.'))
print(f"Total de Veículos Envolvidos:    {total_veiculos:>10,}".replace(',', '.'))
print()


# ------------------------------------------------------------------------------
# 3. AGRUPAMENTO POR RODOVIA (BR), ÍNDICE DE LETALIDADE E TOP 10 BRs
# ------------------------------------------------------------------------------
print("=" * 70)
print("3. TOP 10 RODOVIAS FEDERAIS COM MAIOR NÚMERO DE SINISTROS E LETALIDADE")
print("=" * 70)

# Agrupamento por 'br'
df_rodovias = df.groupby('br').agg(
    sinistros=('id', 'count'),
    mortos=('mortos', 'sum'),
    feridos_graves=('feridos_graves', 'sum'),
    veiculos=('veiculos', 'sum')
).reset_index()

# Cálculo do Índice de Letalidade: (mortos / sinistros) * 100
df_rodovias['indice_letalidade'] = (df_rodovias['mortos'] / df_rodovias['sinistros']) * 100

# Ordenação decrescente pelo volume total de sinistros
df_top10 = df_rodovias.sort_values(by='sinistros', ascending=False).head(10).copy()

# Formatação das colunas para visualização executiva
df_top10['BR'] = df_top10['br'].apply(lambda x: f"BR-{str(x).zfill(3)}")
df_top10['Sinistros'] = df_top10['sinistros'].apply(lambda x: f"{x:,.0f}".replace(',', '.'))
df_top10['Óbitos'] = df_top10['mortos'].apply(lambda x: f"{x:,.0f}".replace(',', '.'))
df_top10['Feridos Graves'] = df_top10['feridos_graves'].apply(lambda x: f"{x:,.0f}".replace(',', '.'))
df_top10['Veículos'] = df_top10['veiculos'].apply(lambda x: f"{x:,.0f}".replace(',', '.'))
df_top10['Letalidade (%)'] = df_top10['indice_letalidade'].apply(lambda x: f"{x:.2f}%".replace('.', ','))

colunas_apresentacao = ['BR', 'Sinistros', 'Óbitos', 'Feridos Graves', 'Veículos', 'Letalidade (%)']
print(df_top10[colunas_apresentacao].to_string(index=False))
