# 🗺️ Roadmap Científico & Técnico: Analytics do Vale (v16+)

**Objetivo:** Evoluir a plataforma de uma ferramenta de "Análise Descritiva" para um ecossistema de "Inteligência Preditiva Contextual", fundamentado em modelagem estatística robusta e conceitos de *Product Data Science*.

---

## 🧪 Fase 1: Feature Engineering Contextual (v16.0)

**Foco:** Eliminar métricas absolutas em favor de métricas relativas (contexto) e temporais (dinâmica).

### 1.1. Dinâmica de Snowball (Aceleração de Recursos)

A literatura indica que o estado estático (ouro total) é menos preditivo do que a dinâmica de ganho ao longo do tempo.

* **Conceito:** Implementar `gold_velocity_rel` (velocidade comparada ao oponente direto) e `gold_acceleration` (derivada da velocidade) para detectar a verdadeira criação de vantagem.
* **Implementação:** Coleta de dados minuto a minuto para treinar redes neurais ou modelos de regressão na evolução temporal do ouro e XP.
* **Benefício de Produto:** Diferencia o jogador que "está forte" (acumulou ouro) daquele que "está ficando incontrolável" (aceleração positiva constante).

### 1.2. Avaliação de Decisão sob Restrição (Draft vs. Execução)

Isolar a habilidade do jogador da qualidade da composição do time, utilizando análise estatística de sinergia e *counter-picking*.

* **Métrica A (Ex-Ante):** `Draft Quality Score`. Baseado na taxa de vitória histórica da composição e pontuação de sinergia dos vetores de campeões.
* **Métrica B (Ex-Post):** `Execution Score`. A performance do jogador *dada* a restrição imposta pelo draft.
* **Insight de Produto:** Transforma a análise de "Você jogou mal" para "Você extraiu o máximo de um draft com 30% de chance de vitória".

---

## ⚖️ Fase 2: Modelagem Preditiva Robusta (v17.0)

**Foco:** Formalização matemática para estabilidade e reprodutibilidade acadêmica.

### 2.1. Ensemble Temporal Ponderado

Substituir heurísticas por uma função de probabilidade explícita, reconhecendo que diferentes modelos (Regressão Logística vs Random Forest) performam melhor em fases distintas do jogo.

* **Fórmula:** $$P(win) = w_{early}(t) \cdot P_{RL} + w_{mid}(t) \cdot P_{RF} + w_{late}(t) \cdot P_{XGB}$$
  * Onde $P_{RL}$ (Regressão Logística) domina o early game e $P_{RF}$ (Random Forest) captura a complexidade do late game.
* **Benefício:** Explicabilidade matemática e redução de variância nas previsões em tempo real.

### 2.2. Score de Impacto de Objetivos (Abstração)

Criar um `objective_impact_score` dinâmico em vez de regras fixas. A importância de torres, inibidores e monstros épicos varia conforme a duração da partida e o estado atual (vencendo/perdendo).

* **Abstração:** O modelo aprende o peso do objetivo baseado no *timing* e na frequência de eventos subsequentes (ex: Torre levada -> Vitória em X min).

---

## 🔍 Fase 2.5: Explicabilidade & Confiança (v17.5)

**Foco:** *Explainable AI* (XAI) e Sanidade de Produto. A confiança do usuário precede a complexidade do Deep Learning.

### 2.5.1. Camada de Explicabilidade (SHAP Values)

Implementar atribuição de feature para justificar o score. O usuário deve ver quais variáveis específicas (KDA, Ouro, Visão) mais contribuíram para o resultado do modelo.

* **Interface:** "Por que nota 69? (+12 Controle de Dragões, -18 Mortes Críticas)".

### 2.5.2. Regras de Anti-Alucinação (Sanity Check Protocol)

Camada de validação pós-modelo para garantir integridade do produto.

* **Regra:** *Hard caps* onde a IA é proibida de elogiar (ex: KDA < 1.0 em vitória = "Carregado").
* **Objetivo:** Impedir outliers estatísticos de gerarem feedbacks que quebram a confiança do usuário.

---

## 🧠 Fase 3: Deep Learning Comportamental (v18.0)

**Foco:** Captura de padrões não-lineares e modelagem espacial avançada.

### 3.1. Modelo Híbrido de Sequência de Itens (ANN + Semântica)

Utilizar Redes Neurais (MLP/ANN) para prever resultados baseados na sequência de compra de itens e atributos do campeão.

* **Abordagem Híbrida:** A rede neural detecta o padrão de derrota, e uma camada semântica traduz o contexto (ex: "Build sem resistência mágica contra time de alto AP").

### 3.2. Spatial Playstyle Modeling (Clusterização Espacial)

Evoluir a classificação de arquétipos usando *K-Means* aplicado a coordenadas espaciais de eventos no mapa.

* **Aplicação:** Gerar *heatmaps* de comportamento para diferenciar estilos (ex: "Jungler Ganker" vs "Jungler Farmer") baseado em onde as ações ocorrem, não apenas em estatísticas finais.

---

### 📅 Resumo de Implementação

| Versão | Feature Chave | Base Científica Principal |
| :--- | :--- | :--- |
| **v16.0** | `gold_acceleration`, Draft vs Execução | *Gold/XP Dynamics*, *Synergy Analysis* |
| **v17.0** | Ensemble $P(win)$, `objective_impact_score` | *Logistic vs Random Forest*, *Objective Importance* |
| **v17.5** | SHAP Explainer, Anti-Hallucination | *Feature Selection* |
| **v18.0** | Híbrido ANN, Spatial Modeling | *Neural Networks*, *Playstyle Clusters* |
