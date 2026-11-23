# 🛣️ Observatório de Sinistros Rodoviários da PRF (2026)

> **Plataforma Analítica SaaS de Inteligência Operacional, Geoespacial e Comportamental sobre Acidentes nas Rodovias Federais Brasileiras.**

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-4.2_LTS-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Pandas](https://img.shields.io/badge/Pandas-2.0%2B-150458?style=for-the-badge&logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![Apache ECharts](https://img.shields.io/badge/Apache_ECharts-5.5-AA344D?style=for-the-badge&logo=apacheecharts&logoColor=white)](https://echarts.apache.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![Alpine.js](https://img.shields.io/badge/Alpine.js-3.13-8BC0D0?style=for-the-badge&logo=alpinedotjs&logoColor=white)](https://alpinejs.dev/)
[![Status](https://img.shields.io/badge/Status-Produção-success?style=for-the-badge)](#)

---

## 📌 Visão Geral do Projeto

O **Observatório de Sinistros Rodoviários** é uma aplicação web completa desenvolvida em **Django** e **Pandas**, inspirada na estética visual e de usabilidade de plataformas SaaS de referência (*Linear, Stripe e Apple Web*). 

A plataforma processa a base oficial de microdados abertos da **Polícia Rodoviária Federal (PRF)** referente ao ano de **2026** (com **54.895 ocorrências** e mais de 30 variáveis por sinistro), oferecendo aos gestores de tráfego, pesquisadores e tomadores de decisão uma ferramenta veloz (<20ms de tempo de resposta), modular e intuitiva para auditoria de segurança viária.

---

## 📸 Preview da Aplicação

> [!TIP]
> Salve as capturas de tela das páginas nos caminhos indicados dentro da pasta `docs/` para que sejam renderizadas automaticamente no GitHub.

| Dashboard Principal (Light Mode) | Modo Escuro (Dark Mode Persistente) |
| :---: | :---: |
| ![Dashboard Principal](docs/preview-home.png) | ![Dark Mode](docs/preview-dark.png) |

| Módulo Geoespacial Vetorial | Rodovias & Trechos Críticos |
| :---: | :---: |
| ![Mapa Geoespacial](docs/preview-mapa.png) | ![Rodovias e Trechos](docs/preview-rodovias.png) |

| Causas & Fator Humano | Perfil Temporal & Meteorologia |
| :---: | :---: |
| ![Causas e Fator Humano](docs/preview-causas.png) | ![Perfil Temporal](docs/preview-temporal.png) |

---

## 🚀 Principais Funcionalidades

### 1. Arquitetura Multipáginas Especializada
- **Visão Geral Executiva (`/`):** Bento Grid moderno contendo 4 KPIs mestres (*Total de Sinistros, Óbitos, Feridos Graves, Índice de Letalidade*), gráfico de área suavizada de evolução mensal, barras de ciclo semanal, gauge semicircular segmentado de letalidade e ranking Top 8 Rodovias.
- **Módulo Geoespacial Dedicado (`/mapa/`):** Mapa coroplético vetorial oficial do Brasil (ECharts + GeoJSON IBGE) com 27 estados mapeados, gradiente por densidade de sinistros, tooltips detalhados e ranking lateral com filtragem direta ao clicar na UF.
- **Rodovias & Trechos Críticos (`/rodovias/`):** Diagnóstico de tipologia viária (*Pista Simples, Dupla, Múltipla*), tabela completa paginável e campo de busca instantâneo na tabela por número de BR ou município crítico.
- **Causas & Fator Humano (`/causas/`):** Ranking das Top 12 causas determinantes periciais e Top 10 tipos de colisão/cinemática (*Colisão traseira, frontal, tombamento, atropelamento*), com classificação de severidade.
- **Inteligência Temporal & Clima (`/temporal/`):** Curva temporal contínua (Jan–Set 2026), incidência por dia da semana, análise das 4 fases do dia (*Amanhecer, Pleno dia, Anoitecer, Plena Noite*) e distribuição climática em gráfico donut (*Céu Claro, Chuva, Nevoeiro, etc.*).

### 2. Motor de Insights Operacionais Inteligentes (Pandas Engine)
Em cada uma das quatro rotas analíticas, a aplicação executa diagnósticos automáticos em tempo real que se recalculam a cada filtro aplicado:
- **No Dashboard Principal:** Identifica concentração de óbitos em pistas simples, pico de vítimas em janelas horárias de 3 horas e causa predominante.
- **Em Rodovias:** Aponta a rodovia líder em volume, a tipologia de pista mais letal comparada à média e a taxa de concentração de mortes em trecho rural vs. urbano.
- **Em Causas:** Contrasta a causa mais recorrente contra a mais letal (*Transitar na contramão*) e a dinâmica mais incidente vs. a que mais gera fatalidades (*Colisão frontal*).
- **Em Temporal:** Revela o dia de pico em fluxo e letalidade (*Domingos*), o paradoxo noturno (*a noite chega a ser 2x mais mortal que o dia*) e o percentual sob condições adversas vs. tempo bom.

### 3. Busca Global Instantânea (`⌘K` ou `Ctrl+K`) com 1.858 Municípios
- Modal de busca rápida em estilo SaaS aberto por atalho de teclado global (`⌘K`).
- Carregamento assíncrono via `json_script` contendo **todos os 1.858 municípios únicos do Brasil** presentes no dataset, além das 27 UFs e todas as rodovias federais.
- Filtro em tempo real com **normalização de acentos Unicode (NFD)** para tolerância a variações ortográficas (ex.: `joao pessoa` encontra `JOÃO PESSOA`).
- Exibição suave dos primeiros 15 resultados para máxima taxa de quadros (60fps) e contador dinâmico de correspondências.

### 4. Modo Escuro (Dark Mode) Nativo e Persistente
- Paleta profissional em cinza-carvão e azul meia-noite (`#0B0F19`, `#111827`, `#1E293B`) ativada por botão na barra superior.
- Script anti-FOUC no `<head>` para leitura imediata de `localStorage.getItem('theme')`, eliminando qualquer piscada em branco na transição de páginas.
- Listener global `themeChanged` que recalcula dinamicamente paletas de eixos, grades, tooltips e polígonos vetoriais nos gráficos ECharts e medidores SVG sem recarregar a tela.

### 5. Drawer de Filtros Cruzados e Pílulas Ativas
- Painel lateral deslizante com opções combináveis de:
  - **Estado (UF):** Organizado em mega-menus suspensos por Regiões (*Norte, Nordeste, Centro-Oeste, Sudeste, Sul*).
  - **Classificação:** *Com Vítimas Fatais*, *Com Vítimas Feridas*, *Sem Vítimas (Apenas Danos)*.
  - **Rodovia Federal (BR):** Lista dinâmica ajustada ao estado selecionado.
- Pílulas visuais na Topbar indicando todos os filtros ativos com botão de remoção rápida (`×`).
- Preservação integral de query string ao navegar entre abas (`/rodovias/`, `/causas/`, etc.).

### 6. Exportação de Relatórios em CSV
- Endpoint dedicado (`/exportar/`) que compila o recorte ativo dos filtros e gera download de planilha em formato CSV com codificação `utf-8-sig` e delimitador oficial `;`.

---

## 📊 Estrutura e Engenharia de Dados

A base de dados é composta pelo arquivo oficial `datatran2026.csv` disponibilizado pela PRF:

| Métrica / Atributo | Descrição |
| :--- | :--- |
| **Volume Total** | **54.895 sinistros** registrados |
| **Vítimas Fatais** | **4.610 óbitos** documentados |
| **Feridos Graves** | **14.288 internações graves** |
| **Abrangência Espacial** | Todas as 27 Unidades Federativas e **1.858 municípios** brasileiros |
| **Rodovias Mapeadas** | Mais de 110 rodovias federais (BR-101, BR-116, BR-381, BR-153, etc.) |

### Tratamento Realizado no Backend (`views.py`):
1. **Padrão Singleton em Memória:** Os dados são lidos uma única vez na inicialização do servidor Django e mantidos em cache na memória RAM (`DF_SINISTROS`), garantindo respostas em milissegundos para agrupamentos pesados.
2. **Normalização Numérica:** Conversão das colunas de geolocalização (`latitude`, `longitude`) e quilometragem (`km`) de padrão brasileiro (`virgula`) para floats (`ponto`).
3. **Parse de Datas e Horários:** Tratamento da coluna `data_inversa` para `datetime64[ns]` e extração vetorial da hora cheia para agrupamento em blocos temporais de 3 horas.
4. **Agregações Vetorizadas:** Consultas agrupadas por `uf`, `tipo_pista`, `uso_solo`, `fase_dia` e `causa_acidente` executadas via Pandas de forma vetorizada.

---

## 🏗️ Arquitetura do Projeto

```text
Projeto_transito/
│
├── config/                         # Configurações do Projeto Django
│   ├── settings.py                 # Configurações gerais, apps e diretórios
│   ├── urls.py                     # Roteador central de URLs
│   ├── wsgi.py                     # Entrypoint para servidores WSGI
│   └── asgi.py                     # Entrypoint para servidores ASGI
│
├── dashboard/                      # App Principal de Inteligência e Visualização
│   ├── templates/dashboard/        # Templates HTML com Tailwind + Alpine.js
│   │   ├── base.html               # Layout base: Sidebar, Topbar, ⌘K e Drawer
│   │   ├── index.html              # Dashboard Principal (Bento Grid)
│   │   ├── mapa.html               # Módulo Geoespacial Interativo
│   │   ├── rodovias.html           # Diagnóstico de Rodovias e Trechos Críticos
│   │   ├── causas.html             # Causas Determinantes e Cinemática
│   │   └── temporal.html           # Perfil Temporal e Meteorologia
│   ├── urls.py                     # Rotas especializadas do dashboard
│   ├── views.py                    # Views analíticas, geradores de insights e API
│   └── tests.py                    # Suíte de testes automatizados
│
├── data/                           # Base de Dados e Vetores Geográficos
│   ├── datatran2026.csv            # Base oficial de sinistros da PRF 2026
│   └── brazil_geo.json             # Malha vetorial GeoJSON oficial dos 27 estados
│
├── docs/                           # Documentação e Imagens para o GitHub
│   └── .gitkeep                    # Pasta reservada para capturas de tela
│
├── manage.py                       # CLI de gerenciamento do Django
├── requirements.txt                # Dependências Python do ecossistema
└── .gitignore                      # Regras de exclusão para versionamento Git
```

---

## ⚙️ Como Executar Localmente

Siga o passo a passo abaixo para rodar o projeto na sua máquina:

### 1. Pré-requisitos
- **Python 3.9** ou superior instalado ([python.org](https://www.python.org/downloads/))
- **Git** instalado ([git-scm.com](https://git-scm.com/))

### 2. Clonar o Repositório
```bash
git clone https://github.com/SEU_USUARIO/NOME_DO_REPOSITORIO.git
cd NOME_DO_REPOSITORIO
```

### 3. Criar e Ativar o Ambiente Virtual (`venv`)

- **No macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

- **No Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

- **No Windows (Prompt de Comando CMD):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

### 4. Instalar as Dependências
Com o ambiente virtual ativado, instale os pacotes listados no `requirements.txt`:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Executar as Migrações Iniciais (Django)
```bash
python manage.py migrate
```

### 6. Iniciar o Servidor de Desenvolvimento
```bash
python manage.py runserver
```

Acesse a aplicação no navegador em:
👉 **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)**

---

## 🌐 Publicação Estática no GitHub Pages (`docs/`)

O projeto inclui uma arquitetura de **exportação estática (SPA Serverless)** pronta para hospedagem gratuita e de alta velocidade no **GitHub Pages** diretamente a partir do diretório `docs/`.

### 1. Atualizar ou Gerar os Dados Estáticos
Execute o script automatizado na raiz:
```bash
python exportar_github_pages.py
```
O script processa o `data/datatran2026.csv` com Pandas e gera:
- `docs/data/resumo_nacional.json`: Agregações nacionais, KPIs, séries mensais, ciclo semanal, top rodovias, causas, 1.858 municípios e insights automáticos.
- `docs/data/por_uf.json`: Dicionário indexado pelas 27 UFs com recortes e insights específicos de cada estado.
- `docs/data/brazil_geo.json`: Malha geográfica vetorial oficial dos 27 estados do Brasil.

### 2. Testar Localmente a Versão Estática
```bash
python3 -m http.server 8080 --directory docs
```
Acesse: **[http://localhost:8080](http://localhost:8080)**

### 3. Ativar no Repositório do GitHub
1. Vá até o repositório no GitHub e clique na aba **Settings**.
2. Na barra lateral esquerda, clique em **Pages**.
3. Na seção **Build and deployment** / **Source**, selecione **Deploy from a branch**.
4. Em **Branch**, selecione `main` (ou `master`) e no seletor de pasta escolha `/docs`.
5. Clique em **Save**. Em instantes seu dashboard estará no ar em:
   `https://<seu-usuario>.github.io/<seu-repositorio>/`

---

## 🛠️ Stack Tecnológico

| Camada | Tecnologia | Propósito |
| :--- | :--- | :--- |
| **Backend** | Python 3.9+ & Django 4.2 | Estrutura web robusta, roteamento e templates dinâmicos |
| **Data Engine** | Pandas & NumPy | Agregações estatísticas em memória RAM e geração de diagnósticos |
| **Visualização** | Apache ECharts 5.5 | Gráficos interativos (área, barras, donut e mapa geoespacial) |
| **Estilização** | Tailwind CSS 3.4 | Design System moderno com suporte a Bento Grid e Dark Mode |
| **Reatividade** | Alpine.js 3.13 | Controle de modais (`⌘K`), drawer de filtros e busca em tempo real |
| **Animações** | GSAP 3.12 | Transições suaves e contadores numéricos progressivos (*Count-Up*) |
| **Mapas** | GeoJSON Oficial IBGE | Vetorização das 27 Unidades Federativas do Brasil |

---

## 📄 Fonte dos Dados & Licença

- **Origem dos Dados:** [Polícia Rodoviária Federal (PRF)](https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf) sob a política de dados abertos do Governo Federal Brasileiro.
- **Licença:** Este projeto está sob a licença [MIT](LICENSE), permitindo uso para fins acadêmicos, operacionais e governamentais.

---

<p align="center">
  Desenvolvido com foco em alta performance, usabilidade SaaS e precisão analítica de dados de trânsito.
</p>
