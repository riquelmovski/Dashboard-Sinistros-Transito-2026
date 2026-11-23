"""
Arquivo: dashboard/views.py
Descrição: Arquitetura de Views do Observatório de Sinistros Rodoviários (PRF).
           - Visual e Estrutura SaaS (Linear, Stripe, Apple Web)
           - Carregamento único em memória (Singleton no início do servidor)
           - Filtragem reativa dinâmica com preservação de parâmetros de URL
           - Geração de dados analíticos em JSON limpo para Apache ECharts e GSAP
           - API GeoJSON oficial e exportação rápida de relatórios em CSV
"""

import os
from pathlib import Path
import json
import urllib.parse
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.conf import settings
import pandas as pd


# ==============================================================================
# 1. CARREGAMENTO E LIMPEZA DOS DADOS EM MEMÓRIA (SINGLETON)
# ==============================================================================
def _carregar_e_limpar_dados():
    """
    Localiza, lê e realiza a limpeza inicial do CSV da PRF.
    Mantém o DataFrame em memória (RAM) para resposta instantânea (<20ms).
    """
    caminho_csv = os.path.join(settings.BASE_DIR, 'data', 'datatran2026.csv')
    if not os.path.exists(caminho_csv):
        candidatos = [
            Path('data/datatran2026.csv'),
            Path('Projeto_transito/data/datatran2026.csv'),
            Path(settings.BASE_DIR).parent / 'data' / 'datatran2026.csv'
        ]
        for p in candidatos:
            if os.path.exists(p):
                caminho_csv = str(p)
                break
            
    if not caminho_csv or not os.path.exists(caminho_csv):
        raise FileNotFoundError("Arquivo 'data/datatran2026.csv' não foi encontrado.")

    # Leitura com latin1 e delimitador ';' oficial da PRF
    df = pd.read_csv(caminho_csv, sep=';', encoding='latin1')

    # Conversão de latitude, longitude e km para float
    for col in ['latitude', 'longitude', 'km']:
        df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Conversão de 'data_inversa' para datetime
    df['data_inversa'] = pd.to_datetime(df['data_inversa'])

    return df


# DataFrame global residente em memória
DF_SINISTROS = _carregar_e_limpar_dados()


def _extrair_todos_municipios(df):
    """
    Extrai todos os pares únicos válidos de (município, UF) presentes no dataset,
    ordenados alfabeticamente, com a contagem total de ocorrências de cada um.
    Alimenta a busca global rápida ⌘K sem sobrecarregar a renderização.
    """
    mun_df = df.groupby(['municipio', 'uf']).size().reset_index(name='total')
    mun_df = mun_df.sort_values(by=['municipio', 'uf'])
    
    lista = []
    for _, r in mun_df.iterrows():
        m_raw = str(r['municipio']).strip()
        uf_raw = str(r['uf']).strip()
        if not m_raw or m_raw.upper() == 'NAN' or not uf_raw:
            continue
        lista.append({
            'm': m_raw,
            'uf': uf_raw,
            't': f"{m_raw.title()} ({uf_raw})",
            's': int(r['total'])
        })
    return lista


# Lista completa de municípios carregada em memória (1.858 municípios únicos)
TODOS_MUNICIPIOS = _extrair_todos_municipios(DF_SINISTROS)


def _carregar_geojson_brasil():
    """
    Carrega a malha geográfica oficial dos 27 estados do Brasil (GeoJSON)
    em cache na memória.
    """
    caminho_geo = os.path.join(settings.BASE_DIR, 'data', 'brazil_geo.json')
    if not os.path.exists(caminho_geo):
        candidatos_geo = [
            Path('data/brazil_geo.json'),
            Path('Projeto_transito/data/brazil_geo.json'),
            Path(settings.BASE_DIR).parent / 'data' / 'brazil_geo.json'
        ]
        for p in candidatos_geo:
            if os.path.exists(p):
                caminho_geo = str(p)
                break

    if caminho_geo and os.path.exists(caminho_geo):
        try:
            with open(caminho_geo, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return None


GEOJSON_BRASIL = _carregar_geojson_brasil()

# Mapeamento Oficial de Regiões e Estados do Brasil
REGIOES_BRASIL = {
    'Norte': [
        ('AC', 'Acre'), ('AP', 'Amapá'), ('AM', 'Amazonas'),
        ('PA', 'Pará'), ('RO', 'Rondônia'), ('RR', 'Roraima'), ('TO', 'Tocantins')
    ],
    'Nordeste': [
        ('AL', 'Alagoas'), ('BA', 'Bahia'), ('CE', 'Ceará'),
        ('MA', 'Maranhão'), ('PB', 'Paraíba'), ('PE', 'Pernambuco'),
        ('PI', 'Piauí'), ('RN', 'Rio Grande do Norte'), ('SE', 'Sergipe')
    ],
    'Centro-Oeste': [
        ('DF', 'Distrito Federal'), ('GO', 'Goiás'),
        ('MT', 'Mato Grosso'), ('MS', 'Mato Grosso do Sul')
    ],
    'Sudeste': [
        ('ES', 'Espírito Santo'), ('MG', 'Minas Gerais'),
        ('RJ', 'Rio de Janeiro'), ('SP', 'São Paulo')
    ],
    'Sul': [
        ('PR', 'Paraná'), ('RS', 'Rio Grande do Sul'), ('SC', 'Santa Catarina')
    ]
}

SIGLA_NOME_ESTADOS = {}
for ufs in REGIOES_BRASIL.values():
    for sigla, nome in ufs:
        SIGLA_NOME_ESTADOS[sigla] = nome

LISTA_CLASSIFICACOES = [
    {'nome': 'Com Vítimas Feridas', 'cor_dot': 'bg-blue-500', 'cor_badge': 'text-blue-700 bg-blue-50 border-blue-200'},
    {'nome': 'Sem Vítimas', 'cor_dot': 'bg-emerald-500', 'cor_badge': 'text-emerald-700 bg-emerald-50 border-emerald-200'},
    {'nome': 'Com Vítimas Fatais', 'cor_dot': 'bg-rose-500', 'cor_badge': 'text-rose-700 bg-rose-50 border-rose-200'},
]


# ==============================================================================
# 2. FUNÇÕES AUXILIARES DE ROTEAMENTO E FILTRAGEM DINÂMICA
# ==============================================================================
def get_brs_disponiveis(df_base, uf_selecionada=None):
    """
    Extrai todas as BRs reais presentes no estado selecionado (ou todas as BRs do CSV),
    ordenadas numericamente, descartando valores nulos ou zero.
    """
    if uf_selecionada and uf_selecionada != 'TODAS':
        brs_raw = df_base[df_base['uf'] == uf_selecionada]['br'].dropna().unique()
    else:
        brs_raw = df_base['br'].dropna().unique()
    
    brs_validas = sorted([int(b) for b in brs_raw if int(b) > 0])
    return [{'codigo': str(b), 'label': f"BR-{str(b).zfill(3)}"} for b in brs_validas]


def filtrar_dados(request):
    """
    Processa os parâmetros GET (uf, municipio, classificacao, br) e filtra o DataFrame.
    Garante limpeza automática de BR inconsistente com a UF selecionada.
    """
    uf_selecionada = request.GET.get('uf', '').strip()
    municipio_selecionado = request.GET.get('municipio', '').strip()
    classificacao_selecionada = request.GET.get('classificacao', '').strip()
    br_selecionada = request.GET.get('br', '').strip()

    df_filtrado = DF_SINISTROS.copy()

    # 1. Filtro por Estado (UF)
    if uf_selecionada and uf_selecionada != 'TODAS':
        df_filtrado = df_filtrado[df_filtrado['uf'] == uf_selecionada]

    # 1.1. Filtro por Município
    if municipio_selecionado:
        df_filtrado = df_filtrado[df_filtrado['municipio'].astype(str).str.upper() == municipio_selecionado.upper()]

    # Obter lista de BRs válidas
    lista_brs = get_brs_disponiveis(DF_SINISTROS, uf_selecionada)
    codigos_validos = {b['codigo'] for b in lista_brs}

    # Validação cruzada de BR
    if br_selecionada and br_selecionada != 'TODAS':
        if br_selecionada not in codigos_validos:
            br_selecionada = ''
        else:
            try:
                br_num = int(br_selecionada)
                df_filtrado = df_filtrado[df_filtrado['br'] == br_num]
            except ValueError:
                df_filtrado = df_filtrado[df_filtrado['br'].astype(str) == br_selecionada]

    # 2. Filtro por Classificação do Acidente
    if classificacao_selecionada and classificacao_selecionada != 'TODAS':
        df_filtrado = df_filtrado[df_filtrado['classificacao_acidente'] == classificacao_selecionada]

    filtros = {
        'uf': uf_selecionada,
        'municipio': municipio_selecionado,
        'classificacao': classificacao_selecionada,
        'br': br_selecionada,
        'tem_filtro_ativo': bool(uf_selecionada or municipio_selecionado or classificacao_selecionada or br_selecionada),
        'lista_brs': lista_brs,
    }

    return df_filtrado, filtros


def get_base_context(request, df_filtrado, filtros, active_tab):
    """
    Monta o contexto compartilhado por todas as rotas da aplicação SaaS.
    """
    total_sinistros = len(df_filtrado)
    kpi_sinistros = f"{total_sinistros:,.0f}".replace(',', '.')

    if total_sinistros > 0:
        total_obitos = int(df_filtrado['mortos'].sum())
        total_feridos_graves = int(df_filtrado['feridos_graves'].sum())
        total_feridos_leves = int(df_filtrado['feridos_leves'].sum())
        total_veiculos = int(df_filtrado['veiculos'].sum())
        total_pessoas = int(df_filtrado['pessoas'].sum())
        
        letalidade = (total_obitos / total_sinistros) * 100
        letalidade_num = round(letalidade, 1)
        kpi_obitos = f"{total_obitos:,.0f}".replace(',', '.')
        kpi_feridos_graves = f"{total_feridos_graves:,.0f}".replace(',', '.')
        kpi_feridos_leves = f"{total_feridos_leves:,.0f}".replace(',', '.')
        kpi_veiculos = f"{total_veiculos:,.0f}".replace(',', '.')
        kpi_pessoas = f"{total_pessoas:,.0f}".replace(',', '.')
        kpi_letalidade = f"{letalidade:.1f}%".replace('.', ',')
    else:
        total_obitos = 0
        total_feridos_graves = 0
        total_feridos_leves = 0
        total_veiculos = 0
        total_pessoas = 0
        letalidade_num = 0.0
        kpi_obitos = '0'
        kpi_feridos_graves = '0'
        kpi_feridos_leves = '0'
        kpi_veiculos = '0'
        kpi_pessoas = '0'
        kpi_letalidade = '0,0%'

    # Preservar parâmetros ativos na URL
    params = {}
    if filtros['uf']:
        params['uf'] = filtros['uf']
    if filtros.get('municipio'):
        params['municipio'] = filtros['municipio']
    if filtros['classificacao']:
        params['classificacao'] = filtros['classificacao']
    if filtros['br']:
        params['br'] = filtros['br']

    query_string = f"?{urllib.parse.urlencode(params)}" if params else ""
    current_path = request.path

    def make_url(new_uf=None, new_class=None, new_br=None, new_mun=None, clear_br=False, clear_mun=False):
        p = params.copy()
        if new_uf is not None:
            if new_uf:
                p['uf'] = new_uf
            else:
                p.pop('uf', None)
        if new_class is not None:
            if new_class:
                p['classificacao'] = new_class
            else:
                p.pop('classificacao', None)
        if clear_br or (new_uf is not None and new_uf != filtros['uf']):
            p.pop('br', None)
        elif new_br is not None:
            if new_br:
                p['br'] = new_br
            else:
                p.pop('br', None)
        if clear_mun or (new_uf is not None and new_uf != filtros['uf']):
            p.pop('municipio', None)
        elif new_mun is not None:
            if new_mun:
                p['municipio'] = new_mun
            else:
                p.pop('municipio', None)
        qs = urllib.parse.urlencode(p)
        return f"{current_path}?{qs}" if qs else current_path

    regioes_com_urls = {}
    for reg, ufs in REGIOES_BRASIL.items():
        regioes_com_urls[reg] = [
            {
                'sigla': sigla,
                'nome': nome,
                'url': make_url(new_uf=sigla, clear_mun=True),
                'url_remover': make_url(new_uf='', clear_mun=True),
                'ativa': sigla == filtros['uf']
            }
            for sigla, nome in ufs
        ]

    classificacoes_com_urls = [
        {
            'nome': item['nome'],
            'cor_dot': item['cor_dot'],
            'cor_badge': item['cor_badge'],
            'url': make_url(new_class=item['nome']),
            'url_remover': make_url(new_class=''),
            'ativa': item['nome'] == filtros['classificacao']
        }
        for item in LISTA_CLASSIFICACOES
    ]

    brs_com_urls = [
        {
            'codigo': b['codigo'],
            'label': b['label'],
            'url': make_url(new_br=b['codigo']),
            'url_remover': make_url(new_br=''),
            'ativa': b['codigo'] == filtros['br']
        }
        for b in filtros['lista_brs']
    ]

    uf_label = 'Todo o Brasil'
    uf_nome_completo = 'Todo o Brasil'
    if filtros['uf']:
        uf_nome_completo = SIGLA_NOME_ESTADOS.get(filtros['uf'], filtros['uf'])
        uf_label = f"{filtros['uf']} — {uf_nome_completo}"

    br_label = f"BR-{str(filtros['br']).zfill(3)}" if filtros['br'] else 'Todas as Rodovias'
    municipio_label = filtros.get('municipio', '').title() if filtros.get('municipio') else ''

    # Lista consolidada base para a busca rápida ⌘K (UFs + BRs):
    all_ufs_search = [
        {
            'tipo': 'Estado',
            'titulo': f"{sigla} - {nome}",
            'url': make_url(new_uf=sigla, clear_mun=True),
            'meta': 'Unidade Federativa',
            'keywords': f"{sigla} {nome}"
        }
        for sigla, nome in SIGLA_NOME_ESTADOS.items()
    ]
    all_brs_disponiveis = get_brs_disponiveis(DF_SINISTROS, None)
    all_brs_search = [
        {
            'tipo': 'Rodovia',
            'titulo': b['label'],
            'url': make_url(new_br=b['codigo']),
            'meta': 'Rodovia Federal',
            'keywords': f"BR {b['codigo']} {b['label']}"
        }
        for b in all_brs_disponiveis
    ]
    itens_base_search = all_ufs_search + all_brs_search

    return {
        'total_sinistros_raw': total_sinistros,
        'total_obitos_raw': total_obitos,
        'total_feridos_graves_raw': total_feridos_graves,
        'total_feridos_leves_raw': total_feridos_leves,
        'total_veiculos_raw': total_veiculos,
        'total_pessoas_raw': total_pessoas,
        
        'kpi_sinistros': kpi_sinistros,
        'kpi_obitos': kpi_obitos,
        'kpi_feridos_graves': kpi_feridos_graves,
        'kpi_feridos_leves': kpi_feridos_leves,
        'kpi_veiculos': kpi_veiculos,
        'kpi_pessoas': kpi_pessoas,
        'kpi_letalidade': kpi_letalidade,
        'taxa_letalidade_num': letalidade_num,

        'uf_selecionada': filtros['uf'],
        'uf_nome_completo': uf_nome_completo,
        'uf_label': uf_label,
        'municipio_selecionado': filtros.get('municipio', ''),
        'municipio_label': municipio_label,
        'classificacao_selecionada': filtros['classificacao'],
        'br_selecionada': filtros['br'],
        'br_label': br_label,
        'tem_filtro_ativo': filtros['tem_filtro_ativo'],

        'regioes_brasil': regioes_com_urls,
        'lista_classificacoes': classificacoes_com_urls,
        'lista_brs': brs_com_urls,

        'url_todos_estados': make_url(new_uf='', clear_mun=True),
        'url_todos_municipios': make_url(new_mun='', clear_mun=True),
        'url_todas_classificacoes': make_url(new_class=''),
        'url_todas_brs': make_url(new_br=''),
        'url_limpar_tudo': current_path,

        'active_tab': active_tab,
        'query_string': query_string,
        'current_path': current_path,
        'todos_municipios': TODOS_MUNICIPIOS,
        'itens_base_search_json': json.dumps(itens_base_search),
        'itens_busca_rapida_json': json.dumps(itens_base_search),
        'total_base_oficial': f"{len(DF_SINISTROS):,}".replace(',', '.'),
    }


# ==============================================================================
# 2.5. DIAGNÓSTICO INTELIGENTE (PANDAS INSIGHTS)
# ==============================================================================
def gerar_insights(df_filtrado):
    """
    Diagnóstico Automático Inteligente utilizando Pandas sobre o recorte ativo.
    Calcula dinamicamente 3 descobertas operacionais:
    1. Perfil de Infraestrutura (Pista simples vs. duplas e letalidade comparativa)
    2. Janela Horária Crítica (Janela de 3h e fase do dia com maior número de vítimas graves e fatais)
    3. Fator Humano / Causa Predominante e Localidade (BR ou Município)
    """
    if len(df_filtrado) == 0:
        return {
            'vazio': True,
            'mensagem': 'Nenhum sinistro registrado para a combinação de filtros selecionada. Amplie os parâmetros de Estado, Classificação ou Rodovia para gerar o diagnóstico.',
            'itens': []
        }

    total_sinistros = len(df_filtrado)
    total_mortos = int(df_filtrado['mortos'].sum())

    # 1. Perfil de Infraestrutura
    pista_grp = df_filtrado.groupby('tipo_pista').agg(
        sinistros=('id', 'count'),
        mortos=('mortos', 'sum')
    )
    pista_grp['letalidade'] = (pista_grp['mortos'] / pista_grp['sinistros'] * 100).round(1)

    simples_row = pista_grp.loc['Simples'] if 'Simples' in pista_grp.index else None
    dupla_row = pista_grp.loc['Dupla'] if 'Dupla' in pista_grp.index else None

    mortos_simples = int(simples_row['mortos']) if simples_row is not None else 0
    pct_simples = round(mortos_simples / total_mortos * 100, 1) if total_mortos > 0 else 0.0
    let_simples = float(simples_row['letalidade']) if simples_row is not None else 0.0
    let_dupla = float(dupla_row['letalidade']) if dupla_row is not None else 0.0

    pct_simples_str = f"{pct_simples:.1f}%".replace('.', ',')
    let_simples_str = f"{let_simples:.1f}%".replace('.', ',')
    let_dupla_str = f"{let_dupla:.1f}%".replace('.', ',')
    mortos_simples_fmt = f"{mortos_simples:,}".replace(',', '.')

    # 2. Janela Horária Crítica
    df_temp = df_filtrado.copy()
    horas_extraidas = df_temp['horario'].astype(str).str.slice(0, 2).str.extract(r'(\d+)')[0]
    df_temp['hora'] = horas_extraidas.astype(float).fillna(0).astype(int)
    df_temp['bloco_3h'] = (df_temp['hora'] // 3) * 3
    df_temp['vitimas_graves_fatais'] = df_temp['mortos'] + df_temp['feridos_graves']

    janela_grp = df_temp.groupby('bloco_3h')['vitimas_graves_fatais'].sum()
    top_hora_inicio = int(janela_grp.idxmax()) if not janela_grp.empty else 18
    top_hora_fim = top_hora_inicio + 3
    top_vitimas_janela = int(janela_grp.max()) if not janela_grp.empty else 0
    top_vitimas_fmt = f"{top_vitimas_janela:,}".replace(',', '.')

    fase_grp = df_temp.groupby('fase_dia')['vitimas_graves_fatais'].sum()
    top_fase = str(fase_grp.idxmax()) if not fase_grp.empty else 'Plena Noite'

    # 3. Fator Humano / Causa Predominante & Localidade
    top_causa_s = df_filtrado['causa_acidente'].value_counts()
    top_causa = str(top_causa_s.index[0]) if not top_causa_s.empty else 'N/D'
    top_causa_cnt = int(top_causa_s.iloc[0]) if not top_causa_s.empty else 0
    top_causa_pct = round(top_causa_cnt / total_sinistros * 100, 1)
    top_causa_pct_str = f"{top_causa_pct:.1f}%".replace('.', ',')

    if df_filtrado['br'].dropna().nunique() == 1:
        br_val = int(df_filtrado['br'].dropna().iloc[0])
        top_mun_s = df_filtrado['municipio'].value_counts()
        top_mun_nome = top_mun_s.index[0].title() if not top_mun_s.empty else 'Trecho Crítico'
        local_desc = f"com pico concentrado no município de <strong class='font-bold text-slate-900 dark:text-white'>{top_mun_nome}</strong>"
        local_destaque = f"BR-{br_val:03d} • {top_mun_nome}"
    else:
        top_br_s = df_filtrado['br'].dropna().value_counts()
        top_br_val = int(top_br_s.index[0]) if not top_br_s.empty else 101
        local_desc = f"com maior incidência na rodovia <strong class='font-bold text-slate-900 dark:text-white'>BR-{top_br_val:03d}</strong>"
        local_destaque = f"BR-{top_br_val:03d}"

    insights = [
        {
            'tipo': 'infraestrutura',
            'titulo': 'Perfil de Infraestrutura',
            'badge': 'Letalidade Viária',
            'badge_cor': 'bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-400 border border-rose-200 dark:border-rose-800',
            'destaque': f"{pct_simples_str} dos óbitos em pista simples",
            'descricao': f"Pistas simples concentram <strong class='font-bold text-slate-900 dark:text-white'>{pct_simples_str}</strong> dos óbitos (<span class='tabular-nums font-semibold'>{mortos_simples_fmt}</span> mortes), apresentando letalidade de <strong class='font-bold text-slate-900 dark:text-white'>{let_simples_str}</strong>, superior às pistas duplas (<strong class='font-semibold'>{let_dupla_str}</strong>).",
        },
        {
            'tipo': 'temporal',
            'titulo': 'Janela Horária Crítica',
            'badge': 'Pico de Severidade',
            'badge_cor': 'bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-400 border border-amber-200 dark:border-amber-800',
            'destaque': f"Pico crítico das {top_hora_inicio:02d}h às {top_hora_fim:02d}h",
            'descricao': f"O período de <strong class='font-bold text-slate-900 dark:text-white'>{top_fase}</strong> registra a maior severidade, com pico de ocorrências graves entre <strong class='font-bold text-slate-900 dark:text-white'>{top_hora_inicio:02d}h e {top_hora_fim:02d}h</strong> (<span class='tabular-nums font-semibold'>{top_vitimas_fmt}</span> vítimas graves e fatais).",
        },
        {
            'tipo': 'causa',
            'titulo': 'Fator Humano & Rodovia',
            'badge': 'Causa Predominante',
            'badge_cor': 'bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-400 border border-blue-200 dark:border-blue-800',
            'destaque': f"{top_causa_pct_str}: {top_causa}",
            'descricao': f"A principal causa determinante é <strong class='font-bold text-slate-900 dark:text-white'>'{top_causa}'</strong> (<strong class='font-bold text-slate-900 dark:text-white'>{top_causa_pct_str}</strong> dos casos), {local_desc}.",
        }
    ]

    return {
        'vazio': False,
        'itens': insights,
        'total_analisado': f"{total_sinistros:,}".replace(',', '.')
    }


def gerar_insights_rodovias(df_filtrado):
    """
    Diagnóstico Automático Inteligente para Rodovias & Trechos Críticos.
    1. Rodovia Mais Crítica: BR com maior volume e participação percentual.
    2. Trecho de Maior Letalidade: Tipo de pista com maior taxa de letalidade e comparação com a média.
    3. Perímetro Urbano vs. Rural (uso_solo): Proporção de sinistros e concentração de óbitos.
    """
    if len(df_filtrado) == 0:
        return {
            'vazio': True,
            'mensagem': 'Nenhum sinistro registrado para a combinação de filtros selecionada. Amplie os parâmetros de Estado, Classificação ou Rodovia para gerar o diagnóstico.',
            'itens': []
        }

    total_sinistros = len(df_filtrado)
    total_mortos = int(df_filtrado['mortos'].sum())
    let_geral = (total_mortos / total_sinistros * 100) if total_sinistros > 0 else 0.0

    # 1. Rodovia Mais Crítica
    brs_validas = df_filtrado['br'].dropna()
    if brs_validas.empty:
        destaque_br = "Sem rodovias identificadas"
        desc_br = "Não há rodovias federais identificadas neste recorte selecionado."
    elif brs_validas.nunique() == 1:
        top_br_num = int(brs_validas.iloc[0])
        top_br_sin = len(df_filtrado)
        top_mun_s = df_filtrado['municipio'].value_counts()
        top_mun_nome = top_mun_s.index[0].title() if not top_mun_s.empty else 'N/D'
        top_mun_sin = int(top_mun_s.iloc[0]) if not top_mun_s.empty else 0
        pct_mun = round(top_mun_sin / top_br_sin * 100, 1) if top_br_sin > 0 else 0.0
        pct_mun_str = f"{pct_mun:.1f}%".replace('.', ',')
        top_br_sin_fmt = f"{top_br_sin:,}".replace(',', '.')
        destaque_br = f"BR-{top_br_num:03d} sob análise detalhada"
        desc_br = f"Recorte focado na rodovia <strong class='font-bold text-slate-900 dark:text-white'>BR-{top_br_num:03d}</strong> (<span class='tabular-nums font-semibold'>{top_br_sin_fmt}</span> sinistros), onde o município de <strong class='font-bold text-slate-900 dark:text-white'>{top_mun_nome}</strong> concentra <strong class='font-bold text-slate-900 dark:text-white'>{pct_mun_str}</strong> das ocorrências deste trecho."
    else:
        top_br_s = brs_validas.value_counts()
        top_br_num = int(top_br_s.index[0])
        top_br_sin = int(top_br_s.iloc[0])
        pct_br = round(top_br_sin / total_sinistros * 100, 1)
        pct_br_str = f"{pct_br:.1f}%".replace('.', ',')
        top_br_mortos = int(df_filtrado[df_filtrado['br'] == top_br_num]['mortos'].sum())
        top_br_sin_fmt = f"{top_br_sin:,}".replace(',', '.')
        top_br_mortos_fmt = f"{top_br_mortos:,}".replace(',', '.')
        destaque_br = f"BR-{top_br_num:03d} lidera com {pct_br_str} dos sinistros"
        desc_br = f"A rodovia <strong class='font-bold text-slate-900 dark:text-white'>BR-{top_br_num:03d}</strong> é a mais crítica no recorte, concentrando <strong class='font-bold text-slate-900 dark:text-white'>{pct_br_str}</strong> do volume (<span class='tabular-nums font-semibold'>{top_br_sin_fmt}</span> ocorrências e <span class='tabular-nums font-semibold'>{top_br_mortos_fmt}</span> óbitos)."

    # 2. Trecho de Maior Letalidade por Tipo de Pista
    pista_grp = df_filtrado.groupby('tipo_pista').agg(
        sinistros=('id', 'count'),
        mortos=('mortos', 'sum')
    )
    pista_grp['letalidade'] = (pista_grp['mortos'] / pista_grp['sinistros'] * 100).round(1)
    
    if not pista_grp.empty:
        pista_mais_letal = pista_grp['letalidade'].idxmax()
        let_top_pista = float(pista_grp.loc[pista_mais_letal, 'letalidade'])
        mortos_top_pista = int(pista_grp.loc[pista_mais_letal, 'mortos'])
        mortos_top_fmt = f"{mortos_top_pista:,}".replace(',', '.')
        
        razao = round(let_top_pista / let_geral, 1) if let_geral > 0 else 1.0
        razao_str = f"{razao:.1f}x".replace('.', ',')
        let_top_str = f"{let_top_pista:.1f}%".replace('.', ',')
        let_geral_str = f"{let_geral:.1f}%".replace('.', ',')
        
        destaque_pista = f"Pista {pista_mais_letal}: letalidade de {let_top_str}"
        desc_pista = f"A tipologia <strong class='font-bold text-slate-900 dark:text-white'>Pista {pista_mais_letal}</strong> registra a maior gravidade com <strong class='font-bold text-slate-900 dark:text-white'>{let_top_str}</strong> de letalidade, superando em <strong class='font-semibold'>{razao_str}</strong> a média do recorte ({let_geral_str}) e somando <span class='tabular-nums font-semibold'>{mortos_top_fmt}</span> mortes."
    else:
        destaque_pista = "Dados de pista insuficientes"
        desc_pista = "Não foram encontrados registros categorizados por tipo de pista neste recorte."

    # 3. Perímetro Urbano vs. Rural (uso_solo)
    solo_grp = df_filtrado.groupby('uso_solo').agg(
        sinistros=('id', 'count'),
        mortos=('mortos', 'sum')
    )
    solo_grp['letalidade'] = (solo_grp['mortos'] / solo_grp['sinistros'] * 100).round(1)

    sin_rural = int(solo_grp.loc['Não', 'sinistros']) if 'Não' in solo_grp.index else 0
    mortos_rural = int(solo_grp.loc['Não', 'mortos']) if 'Não' in solo_grp.index else 0
    let_rural = float(solo_grp.loc['Não', 'letalidade']) if 'Não' in solo_grp.index else 0.0

    sin_urb = int(solo_grp.loc['Sim', 'sinistros']) if 'Sim' in solo_grp.index else 0
    let_urb = float(solo_grp.loc['Sim', 'letalidade']) if 'Sim' in solo_grp.index else 0.0

    pct_sin_rural = round(sin_rural / total_sinistros * 100, 1) if total_sinistros > 0 else 0.0
    pct_mortos_rural = round(mortos_rural / total_mortos * 100, 1) if total_mortos > 0 else 0.0
    
    pct_sin_rural_str = f"{pct_sin_rural:.1f}%".replace('.', ',')
    pct_mortos_rural_str = f"{pct_mortos_rural:.1f}%".replace('.', ',')
    let_rural_str = f"{let_rural:.1f}%".replace('.', ',')
    let_urb_str = f"{let_urb:.1f}%".replace('.', ',')

    destaque_solo = f"Trecho rural concentra {pct_mortos_rural_str} dos óbitos"
    desc_solo = f"Embora responda por <strong class='font-bold text-slate-900 dark:text-white'>{pct_sin_rural_str}</strong> dos acidentes, a área rural responde por <strong class='font-bold text-slate-900 dark:text-white'>{pct_mortos_rural_str}</strong> das vidas perdidas, com letalidade de <strong class='font-bold text-slate-900 dark:text-white'>{let_rural_str}</strong> contra <strong class='font-semibold'>{let_urb_str}</strong> nas áreas urbanas."

    insights = [
        {
            'tipo': 'rodovia_critica',
            'titulo': 'Rodovia Mais Crítica',
            'badge': 'Volume Viário',
            'badge_cor': 'bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-400 border border-blue-200 dark:border-blue-800',
            'destaque': destaque_br,
            'descricao': desc_br,
        },
        {
            'tipo': 'pista_letal',
            'titulo': 'Trecho de Maior Letalidade',
            'badge': 'Letalidade Viária',
            'badge_cor': 'bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-400 border border-rose-200 dark:border-rose-800',
            'destaque': destaque_pista,
            'descricao': desc_pista,
        },
        {
            'tipo': 'perimetro',
            'titulo': 'Urbano vs. Rural',
            'badge': 'Dinâmica Territorial',
            'badge_cor': 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800',
            'destaque': destaque_solo,
            'descricao': desc_solo,
        }
    ]

    return {
        'vazio': False,
        'itens': insights,
        'total_analisado': f"{total_sinistros:,}".replace(',', '.')
    }


def gerar_insights_causas(df_filtrado):
    """
    Diagnóstico Automático Inteligente para Causas & Fator Humano.
    1. Causa Número 1: A causa_acidente mais frequente e participação percentual.
    2. Causa Mais Letal: Entre as causas relevantes (top 15 em volume), a de maior índice de mortalidade.
    3. Dinâmica de Impacto (tipo_acidente): Tipo mais frequente vs. tipo mais fatal.
    """
    if len(df_filtrado) == 0:
        return {
            'vazio': True,
            'mensagem': 'Nenhum sinistro registrado para a combinação de filtros selecionada. Amplie os parâmetros de Estado, Classificação ou Rodovia para gerar o diagnóstico.',
            'itens': []
        }

    total_sinistros = len(df_filtrado)

    # 1. Causa Número 1 Mais Frequente
    causas_counts = df_filtrado['causa_acidente'].value_counts()
    top_causa_nome = str(causas_counts.index[0]) if not causas_counts.empty else 'N/D'
    top_causa_vol = int(causas_counts.iloc[0]) if not causas_counts.empty else 0
    top_causa_pct = round(top_causa_vol / total_sinistros * 100, 1) if total_sinistros > 0 else 0.0
    top_causa_pct_str = f"{top_causa_pct:.1f}%".replace('.', ',')
    top_causa_vol_fmt = f"{top_causa_vol:,}".replace(',', '.')

    destaque_causa1 = f"{top_causa_pct_str}: {top_causa_nome}"
    desc_causa1 = f"A falha comportamental mais reincidente é <strong class='font-bold text-slate-900 dark:text-white'>'{top_causa_nome}'</strong>, respondendo por <strong class='font-bold text-slate-900 dark:text-white'>{top_causa_pct_str}</strong> de todas as ocorrências (<span class='tabular-nums font-semibold'>{top_causa_vol_fmt}</span> registros)."

    # 2. Causa Mais Letal (entre as 15 principais em volume para relevância estatística)
    causas_grp = df_filtrado.groupby('causa_acidente').agg(
        sinistros=('id', 'count'),
        mortos=('mortos', 'sum')
    )
    causas_grp['letalidade'] = (causas_grp['mortos'] / causas_grp['sinistros'] * 100).round(1)

    top15_causas = causas_grp.sort_values(by='sinistros', ascending=False).head(15)
    if not top15_causas.empty and top15_causas['mortos'].sum() > 0:
        causa_letal_row = top15_causas.sort_values(by='letalidade', ascending=False).iloc[0]
        causa_letal_nome = str(causa_letal_row.name)
        causa_letal_taxa = float(causa_letal_row['letalidade'])
        causa_letal_mortos = int(causa_letal_row['mortos'])
        causa_letal_sin = int(causa_letal_row['sinistros'])
        causa_letal_taxa_str = f"{causa_letal_taxa:.1f}%".replace('.', ',')
        causa_letal_mortos_fmt = f"{causa_letal_mortos:,}".replace(',', '.')
        causa_letal_sin_fmt = f"{causa_letal_sin:,}".replace(',', '.')
        
        destaque_causa_letal = f"{causa_letal_taxa_str} de letalidade: {causa_letal_nome}"
        desc_causa_letal = f"Entre as causas de volume expressivo, <strong class='font-bold text-slate-900 dark:text-white'>'{causa_letal_nome}'</strong> é a mais letal: <strong class='font-bold text-slate-900 dark:text-white'>{causa_letal_taxa_str}</strong> dos acidentes resultam em óbito (<span class='tabular-nums font-semibold'>{causa_letal_mortos_fmt}</span> mortes em <span class='tabular-nums font-semibold'>{causa_letal_sin_fmt}</span> ocorrências)."
    else:
        destaque_causa_letal = "Sem óbitos registrados nas causas principais"
        desc_causa_letal = "Nenhuma causa relevante registrou fatalidades no recorte selecionado."

    # 3. Dinâmica de Impacto (tipo_acidente: mais frequente vs mais fatal)
    tipos_grp = df_filtrado.groupby('tipo_acidente').agg(
        sinistros=('id', 'count'),
        mortos=('mortos', 'sum')
    )
    tipos_grp['letalidade'] = (tipos_grp['mortos'] / tipos_grp['sinistros'] * 100).round(1)

    if not tipos_grp.empty:
        tipo_freq_nome = str(tipos_grp['sinistros'].idxmax())
        tipo_freq_sin = int(tipos_grp.loc[tipo_freq_nome, 'sinistros'])
        tipo_freq_pct = round(tipo_freq_sin / total_sinistros * 100, 1)
        tipo_freq_pct_str = f"{tipo_freq_pct:.1f}%".replace('.', ',')

        tipo_fatal_nome = str(tipos_grp['mortos'].idxmax())
        tipo_fatal_mortos = int(tipos_grp.loc[tipo_fatal_nome, 'mortos'])
        tipo_fatal_let = float(tipos_grp.loc[tipo_fatal_nome, 'letalidade'])
        tipo_fatal_let_str = f"{tipo_fatal_let:.1f}%".replace('.', ',')
        tipo_fatal_mortos_fmt = f"{tipo_fatal_mortos:,}".replace(',', '.')

        destaque_impacto = f"{tipo_freq_nome} lidera em casos; {tipo_fatal_nome} em mortes"
        desc_impacto = f"A dinamica mais incidente é <strong class='font-bold text-slate-900 dark:text-white'>{tipo_freq_nome}</strong> (<strong class='font-bold text-slate-900 dark:text-white'>{tipo_freq_pct_str}</strong> dos casos), porém a <strong class='font-bold text-slate-900 dark:text-white'>{tipo_fatal_nome}</strong> é a que mais mata, somando <span class='tabular-nums font-semibold'>{tipo_fatal_mortos_fmt}</span> óbitos com taxa de letalidade de <strong class='font-bold text-slate-900 dark:text-white'>{tipo_fatal_let_str}</strong>."
    else:
        destaque_impacto = "Dados de colisão insuficientes"
        desc_impacto = "Não foi possível analisar a dinâmica de impacto para o recorte."

    insights = [
        {
            'tipo': 'causa_top',
            'titulo': 'Causa Número 1',
            'badge': 'Causa Mais Frequente',
            'badge_cor': 'bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-400 border border-blue-200 dark:border-blue-800',
            'destaque': destaque_causa1,
            'descricao': desc_causa1,
        },
        {
            'tipo': 'causa_letal',
            'titulo': 'Causa Mais Letal',
            'badge': 'Alta Severidade',
            'badge_cor': 'bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-400 border border-rose-200 dark:border-rose-800',
            'destaque': destaque_causa_letal,
            'descricao': desc_causa_letal,
        },
        {
            'tipo': 'dinamica_impacto',
            'titulo': 'Dinâmica de Impacto',
            'badge': 'Cinemática de Colisão',
            'badge_cor': 'bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-400 border border-amber-200 dark:border-amber-800',
            'destaque': destaque_impacto,
            'descricao': desc_impacto,
        }
    ]

    return {
        'vazio': False,
        'itens': insights,
        'total_analisado': f"{total_sinistros:,}".replace(',', '.')
    }


def gerar_insights_temporal(df_filtrado):
    """
    Diagnóstico Automático Inteligente para Perfil Temporal & Clima.
    1. Dia Crítico da Semana: Dia com maior volume de sinistros e de óbitos.
    2. Turno de Maior Risco (fase_dia): Comparação de letalidade entre Plena Noite e Pleno dia.
    3. Impacto Climático (condicao_metereologica): Condições adversas vs. tempo bom.
    """
    if len(df_filtrado) == 0:
        return {
            'vazio': True,
            'mensagem': 'Nenhum sinistro registrado para a combinação de filtros selecionada. Amplie os parâmetros de Estado, Classificação ou Rodovia para gerar o diagnóstico.',
            'itens': []
        }

    total_sinistros = len(df_filtrado)

    # 1. Dia Crítico da Semana
    dias_grp = df_filtrado.groupby('dia_semana').agg(
        sinistros=('id', 'count'),
        mortos=('mortos', 'sum')
    )
    dias_grp['letalidade'] = (dias_grp['mortos'] / dias_grp['sinistros'] * 100).round(1)

    if not dias_grp.empty:
        top_dia_vol = str(dias_grp['sinistros'].idxmax())
        top_dia_vol_cnt = int(dias_grp.loc[top_dia_vol, 'sinistros'])
        pct_dia_vol = round(top_dia_vol_cnt / total_sinistros * 100, 1)
        pct_dia_vol_str = f"{pct_dia_vol:.1f}%".replace('.', ',')
        top_dia_vol_fmt = f"{top_dia_vol_cnt:,}".replace(',', '.')

        top_dia_mortos = str(dias_grp['mortos'].idxmax())
        top_dia_mortos_cnt = int(dias_grp.loc[top_dia_mortos, 'mortos'])
        top_dia_mortos_let = float(dias_grp.loc[top_dia_mortos, 'letalidade'])
        top_dia_mortos_let_str = f"{top_dia_mortos_let:.1f}%".replace('.', ',')
        top_dia_mortos_fmt = f"{top_dia_mortos_cnt:,}".replace(',', '.')

        destaque_dia = f"{top_dia_vol.capitalize()} concentra maior fluxo; {top_dia_mortos.capitalize()} mais óbitos"
        desc_dia = f"O <strong class='font-bold text-slate-900 dark:text-white'>{top_dia_vol.capitalize()}</strong> lidera em ocorrências com <strong class='font-bold text-slate-900 dark:text-white'>{pct_dia_vol_str}</strong> do total (<span class='tabular-nums font-semibold'>{top_dia_vol_fmt}</span> casos). O maior volume de fatalidades se concentra no <strong class='font-bold text-slate-900 dark:text-white'>{top_dia_mortos.capitalize()}</strong> (<span class='tabular-nums font-semibold'>{top_dia_mortos_fmt}</span> óbitos com letalidade de <strong class='font-bold text-slate-900 dark:text-white'>{top_dia_mortos_let_str}</strong>)."
    else:
        destaque_dia = "Sem dados semanais suficientes"
        desc_dia = "Não foi possível consolidar a distribuição por dia da semana."

    # 2. Turno de Maior Risco (fase_dia: Plena Noite vs Pleno dia)
    fases_grp = df_filtrado.groupby('fase_dia').agg(
        sinistros=('id', 'count'),
        mortos=('mortos', 'sum')
    )
    fases_grp['letalidade'] = (fases_grp['mortos'] / fases_grp['sinistros'] * 100).round(1)

    let_noite = float(fases_grp.loc['Plena Noite', 'letalidade']) if 'Plena Noite' in fases_grp.index else 0.0
    let_dia = float(fases_grp.loc['Pleno dia', 'letalidade']) if 'Pleno dia' in fases_grp.index else 0.0
    mortos_noite = int(fases_grp.loc['Plena Noite', 'mortos']) if 'Plena Noite' in fases_grp.index else 0
    mortos_noite_fmt = f"{mortos_noite:,}".replace(',', '.')

    let_noite_str = f"{let_noite:.1f}%".replace('.', ',')
    let_dia_str = f"{let_dia:.1f}%".replace('.', ',')

    razao_turno = round(let_noite / let_dia, 1) if let_dia > 0 else 1.0
    razao_turno_str = f"{razao_turno:.1f}x".replace('.', ',')

    destaque_fase = f"Plena Noite é {razao_turno_str} mais letal que o Pleno dia"
    desc_fase = f"A letalidade durante a <strong class='font-bold text-slate-900 dark:text-white'>Plena Noite</strong> atinge <strong class='font-bold text-slate-900 dark:text-white'>{let_noite_str}</strong> (<span class='tabular-nums font-semibold'>{mortos_noite_fmt}</span> mortes), superando em <strong class='font-bold text-slate-900 dark:text-white'>{razao_turno_str}</strong> o índice registrado em <strong class='font-semibold'>Pleno dia</strong> (<strong class='font-semibold'>{let_dia_str}</strong>), evidenciando o perigo da combinação entre velocidade e visibilidade reduzida."

    # 3. Impacto Climático (condicao_metereologica)
    adversas_list = ['Chuva', 'Garoa/Chuvisco', 'Nevoeiro/Neblina', 'Granizo', 'Neve', 'Vento']
    bom_list = ['Céu Claro', 'Sol']

    sin_adv = int(df_filtrado['condicao_metereologica'].isin(adversas_list).sum())
    sin_bom = int(df_filtrado['condicao_metereologica'].isin(bom_list).sum())
    
    pct_adv = round(sin_adv / total_sinistros * 100, 1) if total_sinistros > 0 else 0.0
    pct_bom = round(sin_bom / total_sinistros * 100, 1) if total_sinistros > 0 else 0.0
    pct_adv_str = f"{pct_adv:.1f}%".replace('.', ',')
    pct_bom_str = f"{pct_bom:.1f}%".replace('.', ',')
    sin_adv_fmt = f"{sin_adv:,}".replace(',', '.')

    mortos_adv = int(df_filtrado[df_filtrado['condicao_metereologica'].isin(adversas_list)]['mortos'].sum())
    let_adv = round(mortos_adv / sin_adv * 100, 1) if sin_adv > 0 else 0.0
    let_adv_str = f"{let_adv:.1f}%".replace('.', ',')

    destaque_clima = f"{pct_bom_str} dos sinistros ocorrem sob tempo bom"
    desc_clima = f"Condições adversas (chuva, garoa e neblina) somam <strong class='font-bold text-slate-900 dark:text-white'>{pct_adv_str}</strong> dos casos (<span class='tabular-nums font-semibold'>{sin_adv_fmt}</span> sinistros com letalidade de <strong class='font-bold text-slate-900 dark:text-white'>{let_adv_str}</strong>). A grande maioria (<strong class='font-bold text-slate-900 dark:text-white'>{pct_bom_str}</strong>) ocorre sob <strong class='font-semibold'>tempo bom</strong>, comprovando que a desatenção supera o clima como vetor primário de risco."

    insights = [
        {
            'tipo': 'dia_semana',
            'titulo': 'Dia Crítico da Semana',
            'badge': 'Ciclo Semanal',
            'badge_cor': 'bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-400 border border-blue-200 dark:border-blue-800',
            'destaque': destaque_dia,
            'descricao': desc_dia,
        },
        {
            'tipo': 'turno_risco',
            'titulo': 'Turno de Maior Risco',
            'badge': 'Paradoxo Noturno',
            'badge_cor': 'bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-400 border border-rose-200 dark:border-rose-800',
            'destaque': destaque_fase,
            'descricao': desc_fase,
        },
        {
            'tipo': 'clima',
            'titulo': 'Impacto Meteorológico',
            'badge': 'Condições da Pista',
            'badge_cor': 'bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-400 border border-amber-200 dark:border-amber-800',
            'destaque': destaque_clima,
            'descricao': desc_clima,
        }
    ]

    return {
        'vazio': False,
        'itens': insights,
        'total_analisado': f"{total_sinistros:,}".replace(',', '.')
    }


# ==============================================================================
# 3. ROTA 1: DASHBOARD PRINCIPAL (/)
# ==============================================================================
def index(request):
    df_filtrado, filtros = filtrar_dados(request)
    context = get_base_context(request, df_filtrado, filtros, active_tab='visao_geral')

    if len(df_filtrado) == 0:
        empty_evolucao = {'meses': [], 'sinistros': [], 'obitos': []}
        empty_dias = {'dias': [], 'dias_completos': [], 'sinistros': [], 'obitos': [], 'pico_index': 0, 'pico_dia_nome': ''}
        context['chart_evolucao_data'] = empty_evolucao
        context['chart_evolucao_json'] = json.dumps(empty_evolucao)
        context['chart_dias_data'] = empty_dias
        context['chart_dias_json'] = json.dumps(empty_dias)
        context['sub_blocos_gravidade'] = []
        context['top8_rodovias'] = []
        context['top5_rodovias'] = []
        context['gauge_data'] = {'letalidade': 0.0, 'segmentos_ativos': 0, 'total_segmentos': 30, 'pista_simples_pct': 0.0, 'mortos_simples': '0', 'total_mortos': '0'}
        context['insights_inteligentes'] = {
            'vazio': True,
            'mensagem': 'Nenhum sinistro registrado para a combinação de filtros selecionada. Amplie os parâmetros de Estado, Classificação ou Rodovia para gerar o diagnóstico.',
            'itens': []
        }
        return render(request, 'dashboard/index.html', context)

    # Diagnóstico Inteligente com Pandas
    context['insights_inteligentes'] = gerar_insights(df_filtrado)

    # 1. Card Principal Grande: Evolução Temporal & Tendência
    df_mensal = df_filtrado.groupby(df_filtrado['data_inversa'].dt.strftime('%Y-%m')).agg(
        sinistros=('id', 'count'),
        obitos=('mortos', 'sum')
    ).reset_index().rename(columns={'data_inversa': 'mes'})

    # Mapear '2026-01' -> 'Jan', '2026-02' -> 'Fev', etc.
    meses_pt = {
        '01': 'Jan', '02': 'Fev', '03': 'Mar', '04': 'Abr', '05': 'Mai',
        '06': 'Jun', '07': 'Jul', '08': 'Ago', '09': 'Set', '10': 'Out',
        '11': 'Nov', '12': 'Dez'
    }
    df_mensal['mes_label'] = df_mensal['mes'].apply(lambda x: meses_pt.get(x.split('-')[1], x))

    chart_evolucao_data = {
        'meses': [str(x) for x in df_mensal['mes_label'].tolist()],
        'sinistros': [int(x) for x in df_mensal['sinistros'].tolist()],
        'obitos': [int(x) for x in df_mensal['obitos'].tolist()],
    }
    context['chart_evolucao_data'] = chart_evolucao_data
    context['chart_evolucao_json'] = json.dumps(chart_evolucao_data)

    # 3 Sub-blocos de Gravidade na base interna do card grande
    classif_counts = df_filtrado['classificacao_acidente'].value_counts()
    total_s = len(df_filtrado)

    sub_blocos = [
        {
            'nome': 'Com Vítimas Feridas',
            'total': f"{classif_counts.get('Com Vítimas Feridas', 0):,}".replace(',', '.'),
            'pct': round((classif_counts.get('Com Vítimas Feridas', 0) / total_s) * 100, 1),
            'cor_bg': 'bg-blue-600',
            'cor_texto': 'text-blue-600',
            'cor_badge': 'bg-blue-50 text-blue-700 border-blue-200'
        },
        {
            'nome': 'Sem Vítimas (Apenas Danos)',
            'total': f"{classif_counts.get('Sem Vítimas', 0):,}".replace(',', '.'),
            'pct': round((classif_counts.get('Sem Vítimas', 0) / total_s) * 100, 1),
            'cor_bg': 'bg-emerald-500',
            'cor_texto': 'text-emerald-600',
            'cor_badge': 'bg-emerald-50 text-emerald-700 border-emerald-200'
        },
        {
            'nome': 'Com Vítimas Fatais',
            'total': f"{classif_counts.get('Com Vítimas Fatais', 0):,}".replace(',', '.'),
            'pct': round((classif_counts.get('Com Vítimas Fatais', 0) / total_s) * 100, 1),
            'cor_bg': 'bg-rose-500',
            'cor_texto': 'text-rose-600',
            'cor_badge': 'bg-rose-50 text-rose-700 border-rose-200'
        }
    ]
    context['sub_blocos_gravidade'] = sub_blocos

    # 2. Card de Barras Interativo: Incidência por Dia da Semana
    ordem_dias = ['segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado', 'domingo']
    dias_abrev = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
    dias_map = dict(zip(ordem_dias, dias_abrev))

    df_dias = df_filtrado.groupby('dia_semana').agg(
        sinistros=('id', 'count'),
        obitos=('mortos', 'sum')
    ).reindex(ordem_dias).fillna(0).reset_index()
    df_dias['dia_label'] = df_dias['dia_semana'].map(dias_map)

    max_idx = int(df_dias['sinistros'].idxmax()) if not df_dias.empty else 0
    pico_dia_nome = df_dias.loc[max_idx, 'dia_semana'].capitalize() if not df_dias.empty else 'Fins de semana'

    chart_dias_data = {
        'dias': [str(x) for x in df_dias['dia_label'].tolist()],
        'dias_completos': [str(d).capitalize() for d in df_dias['dia_semana'].tolist()],
        'sinistros': [int(x) for x in df_dias['sinistros'].tolist()],
        'obitos': [int(x) for x in df_dias['obitos'].tolist()],
        'pico_index': int(max_idx),
        'pico_dia_nome': str(pico_dia_nome)
    }
    context['chart_dias_data'] = chart_dias_data
    context['chart_dias_json'] = json.dumps(chart_dias_data)
    context['pico_dia_nome'] = pico_dia_nome

    # 3. Medidor Semicircular Segmentado (Gauge 30 segmentos): Letalidade e Pistas
    letalidade_val = context['taxa_letalidade_num']
    # 30 segmentos onde 0% = 0 segmentos e 15% ou mais = 30 segmentos
    segmentos_ativos = min(max(int(round((letalidade_val / 15.0) * 30)), 1), 30) if letalidade_val > 0 else 0

    total_mortos_recorte = int(df_filtrado['mortos'].sum())
    mortos_simples = int(df_filtrado[df_filtrado['tipo_pista'] == 'Simples']['mortos'].sum())
    pista_simples_pct = round((mortos_simples / total_mortos_recorte * 100), 1) if total_mortos_recorte > 0 else 0.0

    context['gauge_data'] = {
        'letalidade': letalidade_val,
        'segmentos_ativos': segmentos_ativos,
        'total_segmentos': 30,
        'pista_simples_pct': pista_simples_pct,
        'mortos_simples': f"{mortos_simples:,}".replace(',', '.'),
        'total_mortos': f"{total_mortos_recorte:,}".replace(',', '.')
    }

    # 4. Tabela Top 8 Rodovias Mais Críticas
    br_summary = df_filtrado.groupby('br').agg(
        sinistros=('id', 'count'),
        mortos=('mortos', 'sum'),
        feridos_graves=('feridos_graves', 'sum')
    ).reset_index()

    mun_counts = df_filtrado.groupby(['br', 'municipio'])['id'].count().reset_index()
    if not mun_counts.empty:
        idx_max = mun_counts.groupby('br')['id'].idxmax()
        top_mun_per_br = mun_counts.loc[idx_max].rename(columns={'municipio': 'municipio_critico', 'id': 'sinistros_municipio'})
        br_summary = pd.merge(br_summary, top_mun_per_br[['br', 'municipio_critico', 'sinistros_municipio']], on='br', how='left')
    else:
        br_summary['municipio_critico'] = 'N/D'
        br_summary['sinistros_municipio'] = 0

    br_summary['letalidade'] = (br_summary['mortos'] / br_summary['sinistros'] * 100).round(1)
    br_top8 = br_summary.sort_values(by='sinistros', ascending=False).head(8)

    lista_top8 = []
    for pos, (_, row) in enumerate(br_top8.iterrows(), start=1):
        lista_top8.append({
            'posicao': pos,
            'br_formatada': f"BR-{str(int(row['br'])).zfill(3)}",
            'br_codigo': str(int(row['br'])),
            'sinistros': f"{int(row['sinistros']):,}".replace(',', '.'),
            'mortos': f"{int(row['mortos']):,}".replace(',', '.'),
            'feridos_graves': f"{int(row['feridos_graves']):,}".replace(',', '.'),
            'letalidade': f"{row['letalidade']:.1f}%".replace('.', ','),
            'letalidade_num': row['letalidade'],
            'letalidade_width': min(int(row['letalidade'] * 5), 100),
            'municipio': str(row.get('municipio_critico', 'N/D')).title(),
            'sinistros_mun': int(row.get('sinistros_municipio', 0))
        })
    context['top8_rodovias'] = lista_top8
    context['top5_rodovias'] = lista_top8

    return render(request, 'dashboard/index.html', context)


# ==============================================================================
# 4. ROTA 2: MAPA GEOESPACIAL DEDICADO (/mapa/)
# ==============================================================================
def mapa(request):
    df_filtrado, filtros = filtrar_dados(request)
    context = get_base_context(request, df_filtrado, filtros, active_tab='mapa')

    # Agregação por UF
    df_uf = df_filtrado.groupby('uf').agg(
        sinistros=('id', 'count'),
        mortos=('mortos', 'sum'),
        feridos_graves=('feridos_graves', 'sum')
    ).reset_index()

    df_uf['nome_estado'] = df_uf['uf'].map(SIGLA_NOME_ESTADOS)
    df_uf['letalidade'] = (df_uf['mortos'] / df_uf['sinistros'] * 100).round(1)

    # Dados para o mapa ECharts
    mapa_series_data = []
    for _, row in df_uf.iterrows():
        nome_est = str(row['nome_estado'])
        mapa_series_data.append({
            'name': nome_est,
            'sigla': str(row['uf']),
            'value': int(row['sinistros']),
            'sinistros': int(row['sinistros']),
            'mortos': int(row['mortos']),
            'feridos_graves': int(row['feridos_graves']),
            'letalidade': float(row['letalidade']),
            'url': f"?uf={row['uf']}"
        })

    # Ranking Top UFs para o painel lateral
    df_ranking = df_uf.sort_values(by='sinistros', ascending=False)
    ranking_ufs = []
    for pos, (_, row) in enumerate(df_ranking.iterrows(), 1):
        ranking_ufs.append({
            'posicao': pos,
            'sigla': row['uf'],
            'nome': row['nome_estado'],
            'sinistros': f"{int(row['sinistros']):,}".replace(',', '.'),
            'mortos': f"{int(row['mortos']):,}".replace(',', '.'),
            'letalidade': f"{row['letalidade']:.1f}%".replace('.', ','),
            'ativa': row['uf'] == filtros['uf']
        })

    context['mapa_series_json'] = json.dumps(mapa_series_data)
    context['ranking_ufs'] = ranking_ufs
    context['max_sinistros_uf'] = int(df_uf['sinistros'].max()) if not df_uf.empty else 1000

    return render(request, 'dashboard/mapa.html', context)


# ==============================================================================
# 5. ROTA 3: RODOVIAS & TRECHOS CRÍTICOS (/rodovias/)
# ==============================================================================
def rodovias(request):
    df_filtrado, filtros = filtrar_dados(request)
    context = get_base_context(request, df_filtrado, filtros, active_tab='rodovias')
    context['insights_inteligentes'] = gerar_insights_rodovias(df_filtrado)

    if len(df_filtrado) == 0:
        empty_pista = {'categorias': [], 'sinistros': [], 'obitos': [], 'feridos_graves': []}
        context['chart_pista_data'] = empty_pista
        context['chart_pista_json'] = json.dumps(empty_pista)
        context['tabela_rodovias'] = []
        return render(request, 'dashboard/rodovias.html', context)

    # Gráfico Tipo de Pista ECharts
    df_pista = df_filtrado.groupby('tipo_pista').agg(
        sinistros=('id', 'count'),
        obitos=('mortos', 'sum'),
        feridos_graves=('feridos_graves', 'sum')
    ).reset_index()

    chart_pista_data = {
        'categorias': [str(x) for x in df_pista['tipo_pista'].tolist()],
        'sinistros': [int(x) for x in df_pista['sinistros'].tolist()],
        'obitos': [int(x) for x in df_pista['obitos'].tolist()],
        'feridos_graves': [int(x) for x in df_pista['feridos_graves'].tolist()],
    }
    context['chart_pista_data'] = chart_pista_data
    context['chart_pista_json'] = json.dumps(chart_pista_data)

    # Tabela Completa de Rodovias
    br_summary = df_filtrado.groupby('br').agg(
        sinistros=('id', 'count'),
        mortos=('mortos', 'sum'),
        feridos_graves=('feridos_graves', 'sum'),
        veiculos=('veiculos', 'sum')
    ).reset_index()

    mun_counts = df_filtrado.groupby(['br', 'municipio'])['id'].count().reset_index()
    if not mun_counts.empty:
        idx_max = mun_counts.groupby('br')['id'].idxmax()
        top_mun_per_br = mun_counts.loc[idx_max].rename(columns={'municipio': 'municipio_critico', 'id': 'sinistros_municipio'})
        br_summary = pd.merge(br_summary, top_mun_per_br[['br', 'municipio_critico', 'sinistros_municipio']], on='br', how='left')
    else:
        br_summary['municipio_critico'] = 'N/D'
        br_summary['sinistros_municipio'] = 0

    br_summary['letalidade'] = (br_summary['mortos'] / br_summary['sinistros'] * 100).round(1)
    br_summary = br_summary.sort_values(by='sinistros', ascending=False)

    tabela_rodovias = []
    for idx, row in enumerate(br_summary.itertuples(), start=1):
        tabela_rodovias.append({
            'posicao': idx,
            'br_formatada': f"BR-{str(int(row.br)).zfill(3)}",
            'br_codigo': str(int(row.br)),
            'sinistros': f"{int(row.sinistros):,}".replace(',', '.'),
            'mortos': f"{int(row.mortos):,}".replace(',', '.'),
            'feridos_graves': f"{int(row.feridos_graves):,}".replace(',', '.'),
            'letalidade': f"{row.letalidade:.1f}%".replace('.', ','),
            'letalidade_num': row.letalidade,
            'letalidade_width': min(int(row.letalidade * 4.5), 100),
            'municipio': str(getattr(row, 'municipio_critico', 'N/D')).title(),
            'sinistros_mun': int(getattr(row, 'sinistros_municipio', 0))
        })
    context['tabela_rodovias'] = tabela_rodovias

    return render(request, 'dashboard/rodovias.html', context)


# ==============================================================================
# 6. ROTA 4: CAUSAS & FATOR HUMANO (/causas/)
# ==============================================================================
def causas(request):
    df_filtrado, filtros = filtrar_dados(request)
    context = get_base_context(request, df_filtrado, filtros, active_tab='causas')
    context['insights_inteligentes'] = gerar_insights_causas(df_filtrado)

    if len(df_filtrado) == 0:
        empty_causas = {'causas': [], 'totais': []}
        empty_tipos = {'tipos': [], 'totais': []}
        context['chart_causas_data'] = empty_causas
        context['chart_causas_json'] = json.dumps(empty_causas)
        context['chart_tipos_data'] = empty_tipos
        context['chart_tipos_json'] = json.dumps(empty_tipos)
        context['tabela_causas'] = []
        return render(request, 'dashboard/causas.html', context)

    # 1. Top 12 Causas Determinantes
    df_causas = df_filtrado['causa_acidente'].value_counts().head(12).reset_index()
    df_causas.columns = ['causa', 'total']

    chart_causas_data = {
        'causas': [str(x) for x in df_causas['causa'].tolist()[::-1]], # Inverter para ordem decrescente no ECharts horizontal
        'totais': [int(x) for x in df_causas['total'].tolist()[::-1]]
    }
    context['chart_causas_data'] = chart_causas_data
    context['chart_causas_json'] = json.dumps(chart_causas_data)

    # 2. Top 10 Tipos de Acidente / Cinemática
    df_tipos = df_filtrado['tipo_acidente'].value_counts().head(10).reset_index()
    df_tipos.columns = ['tipo', 'total']

    chart_tipos_data = {
        'tipos': [str(x) for x in df_tipos['tipo'].tolist()[::-1]],
        'totais': [int(x) for x in df_tipos['total'].tolist()[::-1]]
    }
    context['chart_tipos_data'] = chart_tipos_data
    context['chart_tipos_json'] = json.dumps(chart_tipos_data)

    # 3. Tabela Detalhada Causa vs. Risco de Letalidade
    causas_group = df_filtrado.groupby('causa_acidente').agg(
        sinistros=('id', 'count'),
        mortos=('mortos', 'sum'),
        feridos_graves=('feridos_graves', 'sum')
    ).reset_index()

    causas_group['letalidade'] = (causas_group['mortos'] / causas_group['sinistros'] * 100).round(1)
    causas_top = causas_group.sort_values(by='sinistros', ascending=False).head(20)

    tabela_causas = []
    for idx, row in enumerate(causas_top.itertuples(), start=1):
        if row.letalidade >= 15.0:
            badge_class = "text-rose-700 bg-rose-50 border border-rose-200"
            badge_texto = "Crítica"
        elif row.letalidade >= 7.0:
            badge_class = "text-amber-700 bg-amber-50 border border-amber-200"
            badge_texto = "Alta"
        else:
            badge_class = "text-emerald-700 bg-emerald-50 border border-emerald-200"
            badge_texto = "Moderada"

        tabela_causas.append({
            'posicao': idx,
            'causa': str(row.causa_acidente),
            'sinistros': f"{int(row.sinistros):,}".replace(',', '.'),
            'mortos': f"{int(row.mortos):,}".replace(',', '.'),
            'feridos_graves': f"{int(row.feridos_graves):,}".replace(',', '.'),
            'letalidade': f"{row.letalidade:.1f}%".replace('.', ','),
            'badge_class': badge_class,
            'badge_texto': badge_texto
        })
    context['tabela_causas'] = tabela_causas

    return render(request, 'dashboard/causas.html', context)


# ==============================================================================
# 7. ROTA 5: PERFIL TEMPORAL & CLIMA (/temporal/)
# ==============================================================================
def temporal(request):
    df_filtrado, filtros = filtrar_dados(request)
    context = get_base_context(request, df_filtrado, filtros, active_tab='temporal')
    context['insights_inteligentes'] = gerar_insights_temporal(df_filtrado)

    if len(df_filtrado) == 0:
        empty_mensal = {'meses': [], 'sinistros': [], 'obitos': []}
        empty_semana = {'dias': [], 'sinistros': [], 'obitos': []}
        empty_fase = {'fases': [], 'sinistros': [], 'obitos': []}
        empty_clima = []
        context['chart_mensal_data'] = empty_mensal
        context['chart_mensal_json'] = json.dumps(empty_mensal)
        context['chart_semana_data'] = empty_semana
        context['chart_semana_json'] = json.dumps(empty_semana)
        context['chart_dias_data'] = empty_semana
        context['chart_dias_json'] = json.dumps(empty_semana)
        context['chart_fase_data'] = empty_fase
        context['chart_fase_json'] = json.dumps(empty_fase)
        context['chart_clima_data'] = empty_clima
        context['chart_clima_json'] = json.dumps(empty_clima)
        context['total_clima_formatado'] = '0'
        return render(request, 'dashboard/temporal.html', context)

    # 1. Evolução Mensal Area Spline
    df_mensal = df_filtrado.groupby(df_filtrado['data_inversa'].dt.strftime('%Y-%m')).agg(
        sinistros=('id', 'count'),
        obitos=('mortos', 'sum')
    ).reset_index().rename(columns={'data_inversa': 'mes'})

    meses_pt = {
        '01': 'Jan', '02': 'Fev', '03': 'Mar', '04': 'Abr', '05': 'Mai',
        '06': 'Jun', '07': 'Jul', '08': 'Ago', '09': 'Set', '10': 'Out',
        '11': 'Nov', '12': 'Dez'
    }
    df_mensal['mes_label'] = df_mensal['mes'].apply(lambda x: meses_pt.get(x.split('-')[1], x))

    chart_mensal_data = {
        'meses': [str(x) for x in df_mensal['mes_label'].tolist()],
        'sinistros': [int(x) for x in df_mensal['sinistros'].tolist()],
        'obitos': [int(x) for x in df_mensal['obitos'].tolist()],
    }
    context['chart_mensal_data'] = chart_mensal_data
    context['chart_mensal_json'] = json.dumps(chart_mensal_data)

    # 2. Ciclo Semanal
    ordem_dias = ['segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado', 'domingo']
    dias_abrev = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
    dias_map = dict(zip(ordem_dias, dias_abrev))

    df_dias = df_filtrado.groupby('dia_semana').agg(
        sinistros=('id', 'count'),
        obitos=('mortos', 'sum')
    ).reindex(ordem_dias).fillna(0).reset_index()
    df_dias['dia_label'] = df_dias['dia_semana'].map(dias_map)

    chart_semana_data = {
        'dias': [str(x) for x in df_dias['dia_label'].tolist()],
        'sinistros': [int(x) for x in df_dias['sinistros'].tolist()],
        'obitos': [int(x) for x in df_dias['obitos'].tolist()],
    }
    context['chart_semana_data'] = chart_semana_data
    context['chart_semana_json'] = json.dumps(chart_semana_data)
    context['chart_dias_data'] = chart_semana_data
    context['chart_dias_json'] = json.dumps(chart_semana_data)

    # 3. Fase do Dia
    ordem_fases = ['Amanhecer', 'Pleno dia', 'Anoitecer', 'Plena Noite']
    df_fase = df_filtrado.groupby('fase_dia').agg(
        sinistros=('id', 'count'),
        obitos=('mortos', 'sum')
    ).reindex([f for f in ordem_fases if f in df_filtrado['fase_dia'].unique()]).fillna(0).reset_index()

    chart_fase_data = {
        'fases': [str(x) for x in df_fase['fase_dia'].tolist()],
        'sinistros': [int(x) for x in df_fase['sinistros'].tolist()],
        'obitos': [int(x) for x in df_fase['obitos'].tolist()],
    }
    context['chart_fase_data'] = chart_fase_data
    context['chart_fase_json'] = json.dumps(chart_fase_data)

    # 4. Condições Meteorológicas (Donut ECharts)
    df_clima = df_filtrado['condicao_metereologica'].value_counts().head(7).reset_index()
    df_clima.columns = ['clima', 'total']

    chart_clima_data = [{'name': str(r.clima), 'value': int(r.total)} for r in df_clima.itertuples()]
    context['chart_clima_data'] = chart_clima_data
    context['chart_clima_json'] = json.dumps(chart_clima_data)
    context['total_clima_formatado'] = f"{int(df_clima['total'].sum()):,}".replace(',', '.')

    return render(request, 'dashboard/temporal.html', context)


# ==============================================================================
# 8. ROTAS DE SUPORTE: API GEOJSON & EXPORTAÇÃO CSV
# ==============================================================================
def geojson_brasil(request):
    """
    Retorna o GeoJSON oficial dos 27 estados em formato JSON de alta velocidade
    com cabeçalho de cache para ECharts.
    """
    if GEOJSON_BRASIL:
        response = JsonResponse(GEOJSON_BRASIL, safe=False)
        response['Cache-Control'] = 'public, max-age=86400'
        return response
    return JsonResponse({'error': 'GeoJSON não disponível'}, status=404)


def export_csv(request):
    """
    Exportação rápida do recorte filtrado em CSV para o botão "Exportar Relatório".
    """
    df_filtrado, filtros = filtrar_dados(request)
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="relatorio_sinistros_prf_2026.csv"'
    
    # Exportar colunas principais com separador ';'
    colunas_export = [
        'id', 'data_inversa', 'dia_semana', 'horario', 'uf', 'br', 'km',
        'municipio', 'causa_acidente', 'tipo_acidente', 'classificacao_acidente',
        'fase_dia', 'condicao_metereologica', 'tipo_pista', 'mortos', 'feridos_graves', 'veiculos'
    ]
    cols_existentes = [c for c in colunas_export if c in df_filtrado.columns]
    df_filtrado[cols_existentes].to_csv(response, index=False, sep=';', encoding='utf-8-sig')
    return response
