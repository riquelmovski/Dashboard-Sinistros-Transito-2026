"""
Script: eda_teste.py
Descrição: Leitura e Análise Exploratória Inicial (EDA) dos dados de 
           sinistros de trânsito da PRF (datatran2026.csv).
Autor: Especialista em Análise de Dados
"""

from pathlib import Path
import pandas as pd

# ==============================================================================
# CONFIGURAÇÃO DE EXIBIÇÃO DO PANDAS (melhora a visualização no terminal)
# ==============================================================================
pd.set_option('display.max_columns', None)  # Mostra todas as colunas sem cortar
pd.set_option('display.width', 1000)        # Ajusta a largura no terminal


# ==============================================================================
# 1. CARREGAMENTO DO ARQUIVO CSV
# ==============================================================================
# Define o caminho do arquivo de forma flexível (funciona tanto da raiz quanto da pasta do app)
caminho_arquivo = Path('data/datatran2026.csv')
if not caminho_arquivo.exists():
    caminho_arquivo = Path('Projeto_transito/data/datatran2026.csv')

print("=" * 70)
print(f"1. CARREGANDO DADOS DE: {caminho_arquivo}")
print("=" * 70)

# Carrega o arquivo usando sep=';' e encoding='latin1'
# - sep=';': O arquivo da PRF utiliza ponto e vírgula como delimitador de campos.
# - encoding='latin1': Permite ler acentuações da língua portuguesa sem erro de decodificação.
df = pd.read_csv(caminho_arquivo, sep=';', encoding='latin1')
print("Arquivo carregado com sucesso!\n")


# ==============================================================================
# 2. TOTAL DE LINHAS E COLUNAS (DIMENSÕES DO DATAFRAME)
# ==============================================================================
print("=" * 70)
print("2. DIMENSÕES DO CONJUNTO DE DADOS (SHAPE)")
print("=" * 70)
linhas, colunas = df.shape
print(f"Total de Linhas (registros):  {linhas:,}".replace(',', '.'))
print(f"Total de Colunas (variáveis): {colunas}\n")


# ==============================================================================
# 3. LISTAGEM DE COLUNAS E TIPOS DE DADOS
# ==============================================================================
print("=" * 70)
print("3. COLUNAS E SEUS RESPECTIVOS TIPOS DE DADOS (DTYPES)")
print("=" * 70)
df_info_colunas = pd.DataFrame({
    'Nome da Coluna': df.columns,
    'Tipo de Dado': df.dtypes.astype(str).values
})
print(df_info_colunas.to_string(index=False))
print()


# ==============================================================================
# 4. CONVERSÃO DE COLUNAS NUMÉRICAS COM VÍRGULA DECIMAL PARA FLOAT
# ==============================================================================
print("=" * 70)
print("4. CONVERSÃO DAS COLUNAS: latitude, longitude e km")
print("=" * 70)
colunas_para_converter = ['latitude', 'longitude', 'km']

for col in colunas_para_converter:
    tipo_anterior = df[col].dtype
    # Passo A: Assegurar que seja string e substituir vírgula por ponto
    df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
    # Passo B: Converter para número decimal float
    # pd.to_numeric com errors='coerce' converte valores inválidos em NaN com segurança
    df[col] = pd.to_numeric(df[col], errors='coerce')
    print(f"Coluna: {col:<12} | Tipo anterior: {str(tipo_anterior):<10} -> Novo tipo: {str(df[col].dtype)}")

print("\nAmostra das colunas convertidas (5 primeiras linhas):")
print(df[colunas_para_converter].head())
print()


# ==============================================================================
# 5. VALORES NULOS / VAZIOS E EXIBIÇÃO DAS 5 PRIMEIRAS LINHAS
# ==============================================================================
print("=" * 70)
print("5. VERIFICAÇÃO DE VALORES NULOS / VAZIOS POR COLUNA")
print("=" * 70)
nulos_por_coluna = df.isnull().sum()
pct_nulos = (df.isnull().sum() / len(df)) * 100

df_nulos = pd.DataFrame({
    'Coluna': df.columns,
    'Total Nulos': nulos_por_coluna.values,
    'Percentual (%)': pct_nulos.round(2).values
})

# Destaque das colunas que possuem valores nulos
nulos_encontrados = df_nulos[df_nulos['Total Nulos'] > 0]
if not nulos_encontrados.empty:
    print("Colunas que apresentam valores ausentes:")
    print(nulos_encontrados.to_string(index=False))
else:
    print("Nenhuma coluna contém valores nulos!")

print("\n" + "=" * 70)
print("5.1. CINCO PRIMEIRAS LINHAS DO DATAFRAME FORMATADAS")
print("=" * 70)
print(df.head())
