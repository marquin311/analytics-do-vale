🎮 LOL Analytics PhD
AI Coach & Match Intelligence Platform

Plataforma avançada de análise de desempenho em League of Legends, combinando Machine Learning Supervisionado, Calibração Probabilística, Clusterização Comportamental e Explainable AI (XAI) para gerar insights acionáveis por jogador, rota e contexto de partida.

🔬 Diferencial Científico
Diferente de ferramentas tradicionais baseadas apenas em KDA ou Winrate, este projeto estima o impacto marginal real de cada jogador na probabilidade de vitória, utilizando engenharia de dados temporal e validação estatística rigorosa.

🚀 Visão Geral do Projeto

O LOL Analytics PhD foi concebido para simular a tomada de decisão de um coach humano experiente, traduzindo dados brutos de partidas ranqueadas em avaliações táticas, cognitivas e estratégicas.

Principais Capacidades

📊 Score de Impacto Normalizado (0–100)
Métrica composta que avalia a eficiência do jogador relativa ao elo, rota e campeão.

🧠 Predição de Vitória Calibrada
Probabilidades ajustadas via calibração isotônica/sigmoide (otimização por Brier Score).

🎯 Avaliação Contextual de Partida
Considera matchup, duração, escalamento de campeões e dinâmica temporal.

🧩 Clusterização de Estilo de Jogo
Classificação não supervisionada (PCA + K-Means) para identificação de arquétipos comportamentais.

📉 Detecção de Anomalias
Identificação estatística de feeding intencional, colapsos táticos e desempenho fora da curva.

📝 Relatórios Narrativos (NLG)
Geração automática de feedback explicativo em linguagem natural.

🧠 Arquitetura e Pipeline de Dados

O sistema segue uma arquitetura de pipeline linear, com forte ênfase em Feature Engineering temporal e separação clara de responsabilidades.

graph TD
    A[Riot API] --> B[ETL Pipeline]
    B --> C[(PostgreSQL)]
    C --> D[Temporal Feature Engineering]
    D --> E[XGBoost Classifier]
    E --> F[Probability Calibration]
    F --> G[PCA + K-Means]
    G --> H[Explainability Engine - SHAP]
    H --> I[Reports + API]

Componentes Técnicos

ETL & Ingestão
Coletores assíncronos com controle de rate limit da Riot API.

Feature Engineering
Janelas deslizantes, deltas temporais, normalização por elo e rota.

Modelagem Supervisionada
XGBoost com ajuste de hiperparâmetros e validação cruzada.

Pós-processamento
Regras de negócio + tradução de vetores numéricos para linguagem humana.

📊 Performance do Modelo e Validação

Validação realizada em dataset proprietário, garantindo robustez estatística.

Dataset: +144.000 partidas ranqueadas (Diamante+)

Algoritmo: XGBoost Classifier

Brier Score: 0.1165 (alta confiabilidade probabilística)

Métricas por Rota
| Rota    | Accuracy | F1-Score | Observação                    |
| ------- | -------- | -------- | ----------------------------- |
| JUNGLE  | 87.2%    | 0.87     | Maior impacto global no mapa  |
| BOTTOM  | 85.5%    | 0.86     | Alta correlação com objetivos |
| UTILITY | 83.0%    | 0.83     | Impacto via visão e CC        |
| MIDDLE  | 81.6%    | 0.82     | Alta variância mecânica       |
| TOP     | 79.0%    | 0.79     | Rota mais isolada             |

🧩 Arquétipos Comportamentais (Unsupervised Learning)

Utilizando PCA + K-Means, o sistema identifica 4 perfis táticos principais:

🛡️ Controlador de Mapa
Foco em visão, rotação e objetivos neutros.

⚔️ Dominante de Recursos (Hyper Carry)
Alto Gold Share, DPM e conversão de vantagem.

🧭 Facilitador Tático
Ênfase em CC, peel e suporte estratégico.

🚀 Iniciador de Vanguarda
Alta mitigação de dano e iniciação de lutas.

analytics-do-vale/
├── api.py                 # Endpoints da API
├── app.py                 # Core lógico do AI Coach
├── main.py                # Entry point
│
├── etl/
│   ├── riot_collector.py  # Wrapper Riot API
│   └── monitor.py         # Monitoramento
│
├── features/
│   ├── engine.py          # Feature Engineering
│   └── post_processing.py # Normalização
│
├── models/
│   ├── trainer.py         # Treinamento
│   ├── validation.py      # Métricas
│   ├── calibration.py     # Calibração
│   ├── clustering.py      # Arquétipos
│   └── coach.py           # Regras de decisão
│
├── templates/
│   └── report.html        # Relatório HTML
│
├── tests/
│   └── test_features.py
│
├── requirements.txt
├── settings.example.yaml
└── README.md

🔐 Configuração e Instalação
1️⃣ Clonar e instalar dependências
git clone https://github.com/marquin311/analytics-do-vale.git
cd analytics-do-vale
pip install -r requirements.txt

2️⃣ Configurar variáveis sensíveis
cp settings.example.yaml settings.yaml


Edite o settings.yaml:

riot:
  api_key: "RGAPI-XXXX"

database:
  url: "postgresql://user:pass@localhost:5432/lol_analytics"


⚠️ Nota de Segurança
settings.yaml está listado no .gitignore e não deve ser versionado.

🛠️ Stack Tecnológico

Linguagem: Python 3.11

Machine Learning: XGBoost, Scikit-learn

Explainability: SHAP

Data Engineering: Pandas, NumPy, Joblib

Banco de Dados: PostgreSQL

Fonte de Dados: Riot Games API

👤 Autor

Marcos Freire
Engenharia de Computação — UNIVASF

Projeto desenvolvido com foco em pesquisa aplicada, engenharia de features complexas e sistemas inteligentes de suporte à decisão em e-sports.
