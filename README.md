# 🎮 LOL Analytics PhD — AI Coach & Match Intelligence Platform

Plataforma avançada de **análise de desempenho em League of Legends**, que combina **Machine Learning Supervisionado**, **Calibração Probabilística**, **Clusterização Comportamental** e **Interpretabilidade (XAI)** para gerar **insights acionáveis por jogador, rota e contexto de partida**.

🔬 **Diferencial Científico**  
Ao contrário de ferramentas estatísticas tradicionais (focadas apenas em KDA ou winrate), este projeto estima o **impacto marginal real de cada jogador na probabilidade de vitória**, utilizando engenharia de dados robusta e rigor metodológico de nível acadêmico.

---

## 🚀 Visão Geral do Projeto

O **LOL Analytics PhD** foi projetado para simular a **intuição de um coach humano experiente** através de modelos matemáticos e estatísticos.  
O sistema processa dados brutos de partidas ranqueadas para identificar **padrões complexos de tomada de decisão, impacto e consistência**.

### Principais Capacidades

- 📊 **Score de Impacto Normalizado (0–100)**  
  Métrica composta que avalia a eficiência do jogador relativa ao seu **elo, campeão e função**.

- 🧠 **Predição Calibrada de Vitória**  
  Estimativa probabilística com **calibração isotônica/sigmoide**, garantindo confiabilidade estatística.

- 🎯 **Avaliação Contextual**  
  Considera **matchup direto, duração da partida, escalamento e pressão de mapa**.

- 🧩 **Clusterização de Estilo de Jogo**  
  Classificação não-supervisionada (K-Means) para identificação de **arquétipos comportamentais**.

- 📉 **Detecção de Anomalias**  
  Identificação estatística de **feeding, colapsos táticos e jogos fora do padrão esperado**.

- 📝 **Relatório Narrativo (NLG)**  
  Geração automática de feedback explicativo em **linguagem natural**, interpretável por humanos.

---

## 🧠 Arquitetura e Pipeline de Dados

O sistema segue uma arquitetura de **pipeline linear**, com forte ênfase em **Feature Engineering temporal**.

```mermaid
graph TD
    A[Ingestão de Dados<br/>(Riot API)] -->|ETL| B[(PostgreSQL)]
    B --> C{Feature Engineering}
    C -->|Rolling Windows<br/>+ Deltas Temporais| D[XGBoost Classifier]
    D --> E[Módulo de Calibração]
    E -->|Otimização Brier Score| F[PCA + K-Means]
    F --> G[Motor Cognitivo<br/>(XAI / SHAP)]
    G --> H[Relatório Final<br/>+ API]

Componentes Técnicos

ETL & Ingestão
Coletores assíncronos com controle de rate limit da Riot Games API.

Pré-processamento
Tratamento de outliers e criação de features baseadas em janelas deslizantes (ex: desempenho médio dos últimos N jogos).

Modelagem
Aprendizado supervisionado com XGBoost, otimização de hiperparâmetros e validação cruzada.

Pós-processamento
Regras de negócio + tradução de vetores numéricos para diagnósticos interpretáveis.

📊 Performance do Modelo e Validação

O modelo foi validado em um dataset proprietário, garantindo robustez estatística e generalização.

Dataset: +144.000 partidas ranqueadas (Diamante+)

Algoritmo: XGBoost Classifier

Métrica de Calibração (Brier Score): 0.1165

Indica alta confiabilidade nas probabilidades previstas.

| Rota    | Accuracy | F1-Score | Observação                                             |
| ------- | -------- | -------- | ------------------------------------------------------ |
| JUNGLE  | 87.2%    | 0.87     | Maior previsibilidade devido ao impacto global no mapa |
| BOTTOM  | 85.5%    | 0.86     | Alta correlação com controle de dragões                |
| UTILITY | 83.0%    | 0.83     | Impacto medido via visão e CC                          |
| MIDDLE  | 81.6%    | 0.82     | Alta variância mecânica                                |
| TOP     | 79.0%    | 0.79     | Rota mais isolada, menor impacto global imediato       |

🧩 Arquétipos Comportamentais (Unsupervised Learning)

Utilizando PCA (Análise de Componentes Principais) para redução de dimensionalidade seguido de K-Means Clustering, o sistema classifica jogadores em quatro perfis táticos:

🛡️ Controlador de Mapa
Ênfase em visão, rotação e objetivos neutros.

⚔️ Dominante de Recursos (Hyper-Carry)
Alto gold share, DPM e conversão de vantagem.

🧭 Facilitador Tático
Foco em CC, peel e assistências estratégicas.

🚀 Iniciador de Vanguarda
Alta mitigação de dano e iniciação de lutas (engage).

📦 Estrutura do Repositório
analytics-do-vale/
├── api.py                 # Endpoints da API
├── app.py                 # Core lógico do AI Coach
├── main.py                # Entry point
│
├── etl/                   # Pipeline de Dados
│   ├── riot_collector.py
│   └── monitor.py
│
├── features/              # Engenharia de Features
│   ├── engine.py
│   └── post_processing.py
│
├── models/                # Núcleo de ML
│   ├── trainer.py
│   ├── validation.py
│   ├── calibration.py
│   ├── clustering.py
│   └── coach.py
│
├── templates/
│   └── report.html
│
└── tests/
🔐 Configuração e Instalação
1️⃣ Clone e instale dependências
git clone https://github.com/seu-usuario/analytics-do-vale.git
cd analytics-do-vale
pip install -r requirements.txt

2️⃣ Configuração

Crie o arquivo de configuração local:

cp settings.example.yaml settings.yaml


Edite conforme necessário:

riot:
  api_key: "RGAPI-XXXXXXXX-XXXX-XXXX"

database:
  url: "postgresql://user:pass@localhost:5432/lol_analytics"

model:
  threshold: 0.65


⚠️ Nota de Segurança
O arquivo settings.yaml contém credenciais sensíveis e não deve ser versionado.

🛠️ Stack Tecnológico

Linguagem: Python 3.11

Machine Learning: XGBoost, Scikit-learn, SHAP

Data Engineering: Pandas, NumPy, Joblib

Fonte de Dados: Riot Games API

Banco de Dados: PostgreSQL

👤 Autor

Marcos Freire
Engenharia de Computação — UNIVASF

Projeto desenvolvido com foco em Machine Learning aplicado a e-sports, engenharia de features complexas e sistemas inteligentes de suporte à decisão.
