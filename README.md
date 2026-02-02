🎮 LOL Analytics PhD — AI Coach & Match Intelligence Platform

Plataforma avançada de análise de desempenho em League of Legends, que combina Machine Learning Supervisionado, Calibração Probabilística, Clusterização Comportamental e Interpretabilidade (XAI) para gerar insights acionáveis por jogador, rota e contexto de partida.

🔬 Diferencial Científico: Ao contrário de ferramentas estatísticas comuns (que olham apenas para KDA ou Winrate), este projeto avalia o impacto marginal de cada jogador na probabilidade real de vitória, utilizando engenharia de dados robusta e rigor acadêmico.

🚀 Visão Geral do Projeto

O LOL Analytics PhD foi desenhado para simular a intuição de um coach humano experiente através de modelos matemáticos. O sistema processa dados brutos da partida para identificar padrões complexos de jogo.

Principais Capacidades:

📊 Score de Impacto Normalizado (0–100): Uma métrica composta que avalia a eficiência do jogador relativa ao seu elo e campeão.

🧠 Predição Calibrada: Estimativa de probabilidade de vitória com calibração isotônica/sigmoide.

🎯 Avaliação Contextual: Considera o matchup específico, duração da partida e escalamento dos campeões.

🧩 Clusterização de Estilo de Jogo: Classificação não-supervisionada (K-Means) para identificar arquétipos de jogadores.

📉 Detecção de Anomalias: Identificação estatística de feeding intencional ou colapsos táticos.

📝 Relatório Narrativo (NLG): Geração de feedback em linguagem natural explicativa.

🧠 Arquitetura e Pipeline de Dados

O sistema segue uma arquitetura de pipeline linear com forte ênfase em Feature Engineering temporal.

graph TD
    A[Ingestão de Dados (Riot API)] -->|ETL| B(PostgreSQL)
    B --> C{Feature Engineering}
    C -->|Rolling Windows + Deltas| D[XGBoost Model]
    D --> E[Módulo de Calibração]
    E -->|Brier Score Opt.| F[Clusterização (PCA + KMeans)]
    F --> G[Motor Cognitivo (XAI/SHAP)]
    G --> H[Relatório Final & API]


Componentes Técnicos:

ETL & Ingestão: Coletores assíncronos otimizados para respeitar os rate limits da Riot Games.

Pré-processamento: Tratamento de outliers e criação de features de janela deslizante (ex: ouro por minuto nos últimos 5 jogos).

Modelagem: Treinamento supervisionado com otimização de hiperparâmetros.

Pós-processamento: Aplicação de regras de negócio e tradução dos vetores numéricos para texto legível.

📊 Performance do Modelo e Validação

O modelo foi validado em um dataset proprietário, garantindo robustez estatística.

Dataset: +144.000 partidas ranqueadas (Diamante+).

Algoritmo: XGBoost Classifier.

Métrica de Calibração (Brier Score): 0.1165 (Indica alta confiabilidade nas probabilidades previstas).

Métricas por Rota (Cross-Validation)

Rota (Role)

Accuracy

F1-Score

Observação

JUNGLE

87.2%

0.87

Maior previsibilidade devido ao impacto global no mapa.

BOTTOM

85.5%

0.86

Alta correlação com controle de dragões.

UTILITY

83.0%

0.83

Impacto medido via visão e controle de grupo (CC).

MIDDLE

81.6%

0.82

Alta variância mecânica.

TOP

79.0%

0.79

Rota de maior isolamento (menor impacto global imediato).

🧩 Arquétipos Comportamentais (Unsupervised Learning)

Utilizando PCA (Análise de Componentes Principais) para redução de dimensionalidade seguida de K-Means Clustering, o sistema classifica jogadores em 4 perfis táticos:

🛡️ Controlador de Mapa: Foco em Visão, Rotação e Objetivos Neutros.

⚔️ Dominante de Recursos (Hyper-Carry): Alto Gold Share, DPM (Dano por Minuto) e Conversão de recursos.

🧭 Facilitador Tático: Foco em CC (Controle de Grupo), Peel e Assistências.

🚀 Iniciador de Vanguarda: Alta mitigação de dano e iniciação de lutas (Engage).

📦 Estrutura do Repositório

analytics-do-vale/
├── api.py                 # Endpoints da API (FastAPI/Flask)
├── app.py                 # Core lógico do AI Coach
├── main.py                # Entry point da aplicação
│
├── etl/                   # Pipeline de Engenharia de Dados
│   ├── riot_collector.py  # Wrapper para Riot API
│   └── monitor.py         # Monitoramento de jobs
│
├── features/              # Engenharia de Atributos
│   ├── engine.py          # Transformação de dados brutos
│   └── post_processing.py # Normalização
│
├── models/                # Núcleo de Data Science
│   ├── trainer.py         # Script de treino (XGBoost)
│   ├── validation.py      # Cálculo de métricas e curvas ROC
│   ├── calibration.py     # Calibração de probabilidades
│   ├── clustering.py      # Definição de arquétipos
│   └── coach.py           # Camada de regras de negócio
│
├── templates/             # Front-end básico
│   └── report.html
│
└── tests/                 # Testes unitários e de integração


🔐 Configuração e Instalação

Para executar o projeto localmente, siga os passos abaixo:

Clone o repositório e instale as dependências:

git clone [https://github.com/seu-usuario/analytics-do-vale.git](https://github.com/seu-usuario/analytics-do-vale.git)
cd analytics-do-vale
pip install -r requirements.txt


Configure as variáveis de ambiente:
Crie um arquivo settings.yaml baseado no exemplo.

cp settings.example.yaml settings.yaml


Edite o settings.yaml:

riot_api:
  key: "RGAPI-XXXXXXXX-XXXX-XXXX"
database:
  url: "postgresql://user:pass@localhost:5432/lol_analytics"
model:
  threshold: 0.65


⚠️ Nota de Segurança: O arquivo settings.yaml contém credenciais sensíveis e está listado no .gitignore.

🛠️ Stack Tecnológico

Linguagem: Python 3.11

Machine Learning: XGBoost, Scikit-learn, SHAP (Explainable AI)

Data Engineering: Pandas, NumPy, Joblib

Data Source: Riot Games API (Wrapper customizado)

Banco de Dados: PostgreSQL

👤 Autor

Marcos Freire
Engenharia de Computação — UNIVASF

Projeto desenvolvido com foco em pesquisa de Machine Learning aplicado a e-sports, engenharia de features complexas e sistemas de suporte à decisão.

LinkedIn | Portfólio
