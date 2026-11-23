#!/usr/bin/env python3
"""
Arquivo: exportar_github_pages.py
Descrição: Script de automação para geração dos datasets estáticos (JSON) do Dashboard
           de Sinistros Rodoviários da PRF (2026), preparando a pasta docs/ para hospedagem
           gratuita e de alta performance no GitHub Pages.
"""

import os
import sys
import shutil
import json

# Auto-detecção e elevação para o ambiente virtual caso dependências não estejam no Python global
try:
    import pandas as pd
    import django
except ImportError:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidatos_venv = [
        os.path.join(base_dir, 'Projeto_transito', 'venv', 'bin', 'python'),
        os.path.join(base_dir, '.venv', 'bin', 'python'),
        os.path.join(base_dir, 'venv', 'bin', 'python'),
        os.path.join(base_dir, 'Projeto_transito', 'venv', 'Scripts', 'python.exe'),
        os.path.join(base_dir, 'venv', 'Scripts', 'python.exe'),
    ]
    executavel_encontrado = None
    for cand in candidatos_venv:
        if os.path.exists(cand):
            executavel_encontrado = cand
            break
            
    if executavel_encontrado and executavel_encontrado != sys.executable:
        print(f"[*] Redirecionando execução para o ambiente virtual: {executavel_encontrado}")
        os.execv(executavel_encontrado, [executavel_encontrado] + sys.argv)
    else:
        sys.exit("[!] Erro: Pandas e Django são necessários. Ative seu ambiente virtual (ex: source Projeto_transito/venv/bin/activate).")

# Inicialização do ambiente Django para reutilização das regras analíticas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJETO_DIR = os.path.join(BASE_DIR, 'Projeto_transito')

if os.path.exists(PROJETO_DIR):
    sys.path.insert(0, PROJETO_DIR)
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from dashboard.views import (
    DF_SINISTROS,
    gerar_insights,
    gerar_insights_rodovias,
    gerar_insights_causas,
    gerar_insights_temporal,
    TODOS_MUNICIPIOS,
    SIGLA_NOME_ESTADOS,
    REGIOES_BRASIL,
    LISTA_CLASSIFICACOES
)


def processar_recorte_dados(df, uf_nome='Todo o Brasil', uf_sigla=''):
    """
    Processa um recorte de dados (nacional ou estadual) gerando exatamente
    a mesma estrutura de KPIs, séries e agregações utilizada nas views do Django.
    """
    total_sinistros = len(df)
    total_mortos = int(df['mortos'].sum()) if total_sinistros > 0 else 0
    total_feridos_graves = int(df['feridos_graves'].sum()) if total_sinistros > 0 else 0
    total_feridos_leves = int(df['feridos_leves'].sum()) if total_sinistros > 0 else 0
    total_veiculos = int(df['veiculos'].sum()) if total_sinistros > 0 else 0
    total_pessoas = int(df['pessoas'].sum()) if total_sinistros > 0 else 0
    letalidade = (total_mortos / total_sinistros * 100) if total_sinistros > 0 else 0.0

    # 1. Evolução Mensal
    df_m = df.groupby(df['data_inversa'].dt.strftime('%Y-%m')).agg(
        sinistros=('id', 'count'),
        obitos=('mortos', 'sum')
    ).reset_index().rename(columns={'data_inversa': 'mes'})
    meses_pt = {
        '01': 'Jan', '02': 'Fev', '03': 'Mar', '04': 'Abr', '05': 'Mai',
        '06': 'Jun', '07': 'Jul', '08': 'Ago', '09': 'Set', '10': 'Out',
        '11': 'Nov', '12': 'Dez'
    }
    df_m['mes_label'] = df_m['mes'].apply(lambda x: meses_pt.get(x.split('-')[1], x))

    # 2. Ciclo Semanal
    ordem_dias = ['segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado', 'domingo']
    dias_abrev = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
    dias_map = dict(zip(ordem_dias, dias_abrev))
    df_d = df.groupby('dia_semana').agg(
        sinistros=('id', 'count'),
        obitos=('mortos', 'sum')
    ).reindex(ordem_dias).fillna(0).reset_index()
    df_d['dia_label'] = df_d['dia_semana'].map(dias_map)
    max_idx = int(df_d['sinistros'].idxmax()) if not df_d.empty else 0
    pico_dia = df_d.loc[max_idx, 'dia_semana'].capitalize() if not df_d.empty else 'Domingo'

    # 3. Tipo de Pista
    df_pista = df.groupby('tipo_pista').agg(
        sinistros=('id', 'count'),
        obitos=('mortos', 'sum'),
        feridos_graves=('feridos_graves', 'sum')
    ).reset_index()

    # 4. Top 12 Causas
    df_causas = df['causa_acidente'].value_counts().head(12).reset_index()
    df_causas.columns = ['causa', 'total']

    # 5. Top 10 Tipos de Acidente (Cinemática)
    df_tipos = df['tipo_acidente'].value_counts().head(10).reset_index()
    df_tipos.columns = ['tipo', 'total']

    # 6. Fases do Dia
    ordem_fases = ['Amanhecer', 'Pleno dia', 'Anoitecer', 'Plena Noite']
    df_fase = df.groupby('fase_dia').agg(
        sinistros=('id', 'count'),
        obitos=('mortos', 'sum')
    ).reindex([f for f in ordem_fases if f in df['fase_dia'].unique()]).fillna(0).reset_index()

    # 7. Condições Meteorológicas
    df_clima = df['condicao_metereologica'].value_counts().head(7).reset_index()
    df_clima.columns = ['clima', 'total']

    # 8. Tabela de Rodovias (Top 35 ordenadas por volume)
    br_summary = df.groupby('br').agg(
        sinistros=('id', 'count'),
        mortos=('mortos', 'sum'),
        feridos_graves=('feridos_graves', 'sum')
    ).reset_index()

    mun_counts = df.groupby(['br', 'municipio'])['id'].count().reset_index()
    if not mun_counts.empty:
        idx_max = mun_counts.groupby('br')['id'].idxmax()
        top_mun_per_br = mun_counts.loc[idx_max].rename(
            columns={'municipio': 'municipio_critico', 'id': 'sinistros_municipio'}
        )
        br_summary = pd.merge(br_summary, top_mun_per_br[['br', 'municipio_critico', 'sinistros_municipio']], on='br', how='left')
    else:
        br_summary['municipio_critico'] = 'N/D'
        br_summary['sinistros_municipio'] = 0

    br_summary['letalidade'] = (br_summary['mortos'] / br_summary['sinistros'] * 100).round(1)
    br_summary = br_summary.sort_values(by='sinistros', ascending=False)
    
    tabela_rodovias = []
    for idx, row in enumerate(br_summary.head(35).itertuples(), start=1):
        tabela_rodovias.append({
            'posicao': idx,
            'br_codigo': str(int(row.br)),
            'br_formatada': f"BR-{str(int(row.br)).zfill(3)}",
            'sinistros': int(row.sinistros),
            'sinistros_fmt': f"{int(row.sinistros):,}".replace(',', '.'),
            'mortos': int(row.mortos),
            'mortos_fmt': f"{int(row.mortos):,}".replace(',', '.'),
            'feridos_graves': int(row.feridos_graves),
            'feridos_graves_fmt': f"{int(row.feridos_graves):,}".replace(',', '.'),
            'letalidade': float(row.letalidade),
            'letalidade_fmt': f"{row.letalidade:.1f}%".replace('.', ','),
            'letalidade_width': min(int(row.letalidade * 4.5), 100),
            'municipio': str(getattr(row, 'municipio_critico', 'N/D')).title(),
            'sinistros_mun': int(getattr(row, 'sinistros_municipio', 0))
        })

    # 9. Tabela de Causas com Badges de Criticidade
    causas_group = df.groupby('causa_acidente').agg(
        sinistros=('id', 'count'),
        mortos=('mortos', 'sum'),
        feridos_graves=('feridos_graves', 'sum')
    ).reset_index()
    causas_group['letalidade'] = (causas_group['mortos'] / causas_group['sinistros'] * 100).round(1)
    causas_top = causas_group.sort_values(by='sinistros', ascending=False).head(15)
    tabela_causas = []
    for idx, row in enumerate(causas_top.itertuples(), start=1):
        if row.letalidade >= 15.0:
            badge_class = 'text-rose-700 bg-rose-50 dark:bg-rose-950/60 dark:text-rose-400 border border-rose-200 dark:border-rose-800'
            badge_texto = 'Crítica'
        elif row.letalidade >= 7.0:
            badge_class = 'text-amber-700 bg-amber-50 dark:bg-amber-950/60 dark:text-amber-400 border border-amber-200 dark:border-amber-800'
            badge_texto = 'Alta'
        else:
            badge_class = 'text-emerald-700 bg-emerald-50 dark:bg-emerald-950/60 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800'
            badge_texto = 'Moderada'

        tabela_causas.append({
            'posicao': idx,
            'causa': str(row.causa_acidente),
            'sinistros': int(row.sinistros),
            'sinistros_fmt': f"{int(row.sinistros):,}".replace(',', '.'),
            'mortos': int(row.mortos),
            'mortos_fmt': f"{int(row.mortos):,}".replace(',', '.'),
            'feridos_graves': int(row.feridos_graves),
            'feridos_graves_fmt': f"{int(row.feridos_graves):,}".replace(',', '.'),
            'letalidade': float(row.letalidade),
            'letalidade_fmt': f"{row.letalidade:.1f}%".replace('.', ','),
            'badge_class': badge_class,
            'badge_texto': badge_texto
        })

    # 10. Medidor Semicircular (Gauge 30 Segmentos)
    segmentos_ativos = min(max(int(round((letalidade / 15.0) * 30)), 1), 30) if letalidade > 0 else 0
    mortos_simples = int(df[df['tipo_pista'] == 'Simples']['mortos'].sum()) if total_sinistros > 0 else 0
    pista_simples_pct = round((mortos_simples / total_mortos * 100), 1) if total_mortos > 0 else 0.0

    # 11. Sub-blocos de Gravidade
    total_sem_vitimas = len(df[df['classificacao_acidente'] == 'Sem Vítimas'])
    total_fatais = len(df[df['classificacao_acidente'] == 'Com Vítimas Fatais'])
    total_feridos = len(df[df['classificacao_acidente'] == 'Com Vítimas Feridas'])

    sub_blocos = [
        {
            'titulo': 'Com Vítimas Feridas',
            'total': f"{total_feridos:,}".replace(',', '.'),
            'pct': f"{(total_feridos / total_sinistros * 100):.1f}%".replace('.', ',') if total_sinistros else '0,0%',
            'pct_num': round(total_feridos / total_sinistros * 100, 1) if total_sinistros else 0,
            'cor': 'bg-blue-600'
        },
        {
            'titulo': 'Sem Vítimas (Apenas Danos)',
            'total': f"{total_sem_vitimas:,}".replace(',', '.'),
            'pct': f"{(total_sem_vitimas / total_sinistros * 100):.1f}%".replace('.', ',') if total_sinistros else '0,0%',
            'pct_num': round(total_sem_vitimas / total_sinistros * 100, 1) if total_sinistros else 0,
            'cor': 'bg-emerald-500'
        },
        {
            'titulo': 'Com Vítimas Fatais',
            'total': f"{total_fatais:,}".replace(',', '.'),
            'pct': f"{(total_fatais / total_sinistros * 100):.1f}%".replace('.', ',') if total_sinistros else '0,0%',
            'pct_num': round(total_fatais / total_sinistros * 100, 1) if total_sinistros else 0,
            'cor': 'bg-rose-500'
        }
    ]

    return {
        'uf_sigla': uf_sigla,
        'uf_nome': uf_nome,
        'kpis': {
            'sinistros': total_sinistros,
            'sinistros_fmt': f"{total_sinistros:,}".replace(',', '.'),
            'obitos': total_mortos,
            'obitos_fmt': f"{total_mortos:,}".replace(',', '.'),
            'feridos_graves': total_feridos_graves,
            'feridos_graves_fmt': f"{total_feridos_graves:,}".replace(',', '.'),
            'feridos_leves': total_feridos_leves,
            'feridos_leves_fmt': f"{total_feridos_leves:,}".replace(',', '.'),
            'veiculos': total_veiculos,
            'veiculos_fmt': f"{total_veiculos:,}".replace(',', '.'),
            'pessoas': total_pessoas,
            'pessoas_fmt': f"{total_pessoas:,}".replace(',', '.'),
            'letalidade': round(letalidade, 1),
            'letalidade_fmt': f"{letalidade:.1f}%".replace('.', ',')
        },
        'gauge': {
            'letalidade': round(letalidade, 1),
            'segmentos_ativos': segmentos_ativos,
            'total_segmentos': 30,
            'pista_simples_pct': pista_simples_pct,
            'mortos_simples_fmt': f"{mortos_simples:,}".replace(',', '.'),
            'total_mortos_fmt': f"{total_mortos:,}".replace(',', '.')
        },
        'sub_blocos': sub_blocos,
        'evolucao_mensal': {
            'meses': [str(x) for x in df_m['mes_label'].tolist()],
            'sinistros': [int(x) for x in df_m['sinistros'].tolist()],
            'obitos': [int(x) for x in df_m['obitos'].tolist()]
        },
        'dias_semana': {
            'dias': [str(x) for x in df_d['dia_label'].tolist()],
            'dias_completos': [str(x).capitalize() for x in df_d['dia_semana'].tolist()],
            'sinistros': [int(x) for x in df_d['sinistros'].tolist()],
            'obitos': [int(x) for x in df_d['obitos'].tolist()],
            'pico_index': max_idx,
            'pico_dia_nome': pico_dia
        },
        'pista': {
            'categorias': [str(x) for x in df_pista['tipo_pista'].tolist()],
            'sinistros': [int(x) for x in df_pista['sinistros'].tolist()],
            'obitos': [int(x) for x in df_pista['obitos'].tolist()],
            'feridos_graves': [int(x) for x in df_pista['feridos_graves'].tolist()]
        },
        'causas': {
            'causas': [str(x) for x in df_causas['causa'].tolist()[::-1]],
            'totais': [int(x) for x in df_causas['total'].tolist()[::-1]]
        },
        'tabela_causas': tabela_causas,
        'tipos': {
            'tipos': [str(x) for x in df_tipos['tipo'].tolist()[::-1]],
            'totais': [int(x) for x in df_tipos['total'].tolist()[::-1]]
        },
        'fases_dia': {
            'fases': [str(x) for x in df_fase['fase_dia'].tolist()],
            'sinistros': [int(x) for x in df_fase['sinistros'].tolist()],
            'obitos': [int(x) for x in df_fase['obitos'].tolist()]
        },
        'clima': [{'name': str(r.clima), 'value': int(r.total)} for r in df_clima.itertuples()],
        'tabela_rodovias': tabela_rodovias,
        'insights': {
            'geral': gerar_insights(df),
            'rodovias': gerar_insights_rodovias(df),
            'causas': gerar_insights_causas(df),
            'temporal': gerar_insights_temporal(df)
        }
    }


def main():
    print("=" * 70)
    print("EXPORTADOR ESTÁTICO GITHUB PAGES — PRF ANALYTICS 2026")
    print("=" * 70)

    # Identificar diretórios docs/ candidatos para sincronização
    docs_dirs = [os.path.join(BASE_DIR, 'docs')]
    alt_p = os.path.join(BASE_DIR, 'Projeto_transito', 'docs')
    if os.path.exists(alt_p) and alt_p not in docs_dirs:
        docs_dirs.append(alt_p)
    alt_parent = os.path.join(os.path.dirname(BASE_DIR), 'docs')
    if os.path.exists(alt_parent) and alt_parent not in docs_dirs:
        docs_dirs.append(alt_parent)

    for d_dir in docs_dirs:
        os.makedirs(os.path.join(d_dir, 'data'), exist_ok=True)

    data_dir = os.path.join(docs_dirs[0], 'data')

    # 1. Copiar malha geográfica oficial (GeoJSON) para docs/data/
    geojson_src = None
    candidatos_geo = [
        os.path.join(BASE_DIR, 'data', 'brazil_geo.json'),
        os.path.join(BASE_DIR, 'Projeto_transito', 'data', 'brazil_geo.json'),
    ]
    for c in candidatos_geo:
        if os.path.exists(c):
            geojson_src = c
            break

    if geojson_src and os.path.exists(geojson_src):
        for d_dir in docs_dirs:
            shutil.copyfile(geojson_src, os.path.join(d_dir, 'data', 'brazil_geo.json'))
        print(f"[✓] GeoJSON dos 27 estados copiado para: {[os.path.join(d, 'data') for d in docs_dirs]}")
    else:
        print("[!] Aviso: brazil_geo.json não localizado para cópia automática.")

    # 2. Processar Resumo Nacional
    print("\n[*] Processando agregações nacionais sobre 54.895 sinistros...")
    resumo_nacional = processar_recorte_dados(DF_SINISTROS, 'Todo o Brasil', '')

    # Adicionar dados do Mapa e Rankings das 27 UFs
    df_uf = DF_SINISTROS.groupby('uf').agg(
        sinistros=('id', 'count'),
        mortos=('mortos', 'sum'),
        feridos_graves=('feridos_graves', 'sum')
    ).reset_index()
    df_uf['letalidade'] = (df_uf['mortos'] / df_uf['sinistros'] * 100).round(1)
    df_uf = df_uf.sort_values(by='sinistros', ascending=False)

    ranking_ufs = []
    mapa_series = []
    for idx, row in enumerate(df_uf.itertuples(), start=1):
        nome_uf = SIGLA_NOME_ESTADOS.get(row.uf, row.uf)
        ranking_ufs.append({
            'posicao': idx,
            'sigla': row.uf,
            'nome': nome_uf,
            'sinistros': int(row.sinistros),
            'sinistros_fmt': f"{int(row.sinistros):,}".replace(',', '.'),
            'mortos': int(row.mortos),
            'mortos_fmt': f"{int(row.mortos):,}".replace(',', '.'),
            'feridos_graves': int(row.feridos_graves),
            'feridos_graves_fmt': f"{int(row.feridos_graves):,}".replace(',', '.'),
            'letalidade': float(row.letalidade),
            'letalidade_fmt': f"{row.letalidade:.1f}%".replace('.', ',')
        })
        mapa_series.append({
            'name': nome_uf,
            'sigla': row.uf,
            'value': int(row.sinistros),
            'sinistros': int(row.sinistros),
            'mortos': int(row.mortos),
            'feridos_graves': int(row.feridos_graves),
            'letalidade': float(row.letalidade)
        })

    resumo_nacional['ranking_ufs'] = ranking_ufs
    resumo_nacional['mapa_series'] = mapa_series
    resumo_nacional['max_sinistros_uf'] = int(df_uf['sinistros'].max()) if not df_uf.empty else 5000
    resumo_nacional['municipios'] = TODOS_MUNICIPIOS
    resumo_nacional['regioes_brasil'] = REGIOES_BRASIL
    resumo_nacional['lista_classificacoes'] = LISTA_CLASSIFICACOES

    for d_dir in docs_dirs:
        caminho_nacional = os.path.join(d_dir, 'data', 'resumo_nacional.json')
        with open(caminho_nacional, 'w', encoding='utf-8') as f:
            json.dump(resumo_nacional, f, ensure_ascii=False, indent=2)
        tam_nac = os.path.getsize(caminho_nacional) / 1024
        print(f"[✓] '{caminho_nacional}' gerado ({tam_nac:.1f} KB)")

    # 3. Processar Recortes Especializados por Estado (27 UFs)
    print("\n[*] Processando agregações específicas para cada uma das 27 UFs...")
    por_uf = {}
    for sigla, nome in SIGLA_NOME_ESTADOS.items():
        df_estado = DF_SINISTROS[DF_SINISTROS['uf'] == sigla]
        por_uf[sigla] = processar_recorte_dados(df_estado, nome, sigla)
        print(f"    -> UF {sigla} ({nome}): {len(df_estado):,} sinistros processados.")

    for d_dir in docs_dirs:
        caminho_uf = os.path.join(d_dir, 'data', 'por_uf.json')
        with open(caminho_uf, 'w', encoding='utf-8') as f:
            json.dump(por_uf, f, ensure_ascii=False, indent=2)
        tam_uf = os.path.getsize(caminho_uf) / 1024
        print(f"[✓] '{caminho_uf}' gerado ({tam_uf:.1f} KB)")

    print("\n" + "=" * 70)
    print("EXPORTAÇÃO CONCLUÍDA COM SUCESSO!")
    print(f"Diretório de saída: {data_dir}")
    print("=" * 70)


if __name__ == '__main__':
    main()
