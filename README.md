# ContextCortex
A stateful "Neural Memory" for engineering teams. ContextCortex maps the 'Why' behind code—Slack threads, PRs, and meeting notes—into a relational HydraDB graph to eliminate architectural amnesia.


# 🧠 ContextCortex: Neural Memory for Engineering Teams

**ContextCortex** is a production-grade, stateful agentic system designed to bridge the "Context Gap" in software development. By utilizing **HydraDB's Cortex architecture**, ContextCortex creates a persistent relationship graph between developer communication (Slack/Meetings) and codebase execution (GitHub).

---

## ⚡ The Stack

| Layer | Technology | Role |
| :--- | :--- | :--- |
| **Brain** | **GMI Cloud (H100)** | Ultra-low latency inference via **Kimi K2.5**. |
| **Memory** | **HydraDB (Cortex)** | Relational Graph Triples for long-term state. |
| **Orchestration** | **Dify v1.13+** | Multi-agent YAML DSL for complex logic routing. |
| **Interface** | **Photon Spectrum** | Native "Flow of Work" deployment (Slack/iMessage). |

---

## ✨ Why ContextCortex?

### 🔄 Relational Recall vs. Stateless RAG
Standard RAG treats context as isolated text chunks. **ContextCortex** treats context as a living graph. 
*   **Triple logic:** `(Commit:8a2f) -[RESOLVES]-> (Slack_Thread:441) -[DECIDED_BY]-> (User:Shanyu)`.
*   **Result:** When you ask "Why this architecture?", the agent recalls the specific person, time, and Slack thread that drove the decision.

### 🛡️ Architectural Guardrails
ContextCortex proactively scans new PRs against historical "Hidden Knowledge." If a new code change violates a decision made in a meeting 3 weeks ago, the agent flags it instantly via **Photon/Slack**.

---

## 🛠️ System Architecture

```mermaid
graph LR
    A[Slack/GitHub/Docs] --> B[Dify Ingestion]
    B --> C[GMI Cloud: Fact Extraction]
    C --> D[(HydraDB: Context Graph)]
    E[Developer Query] --> F[Dify Logic]
    F -->|Graph Traversal| D
    D -->|Augmented History| G[Kimi K2.5 Reasoning]
    G --> H[Photon: Context Injection]
