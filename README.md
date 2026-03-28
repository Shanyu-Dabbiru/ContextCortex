# ContextCortex: The Engineering Historian
**Stop "Context Debt." Build a persistent memory graph for your team.**

## 🕹️ The "Ghost Review" Demo

https://github.com/user-attachments/assets/fbc7fb7d-0b72-4bd2-a5b1-348bff5d2a43

---

## 🚨 The Problem: Architectural Amnesia
During my time at Fidelity, I identified a recurring bottleneck: **Context Debt**.

Critical architectural decisions are made in Slack threads or meetings, but the documentation rots. Six months later, a new dev joins, doesn't know the "unwritten rule," and writes code that triggers a production outage. We aren't losing data; we're losing intent.

ContextCortex (The Engineering Historian) is a proactive "Ghost Reviewer." It intercepts code intent and checks it against a HydraDB relationship graph to flag conflicts before they ever hit a branch.

---

## ⚙️ The Stack
| Layer | Tech | The "Why" |
| :--- | :--- | :--- |
| **Orchestration** | Dify | YAML-based logic. Decouples the "Brain" from the UI for portability. |
| **Memory** | HydraDB | Moves beyond "Vector Search" into Knowledge Triples. |
| **Inference** | GMI Cloud | H100s for Kimi K2.5. Needed for <2s reasoning on complex logs. |
| **Interface** | FastAPI / CLI | Native integration into the developer's existing terminal workflow. |

---

## 🧠 System Architecture: Relational Recall
Standard RAG finds similar text. ContextCortex finds **authority**.

<img width="1220" height="493" alt="Screenshot 2026-03-28 at 3 55 34 PM" src="https://github.com/user-attachments/assets/c00bb0cc-4cb3-4748-b92c-de3e47d311c5" />


Instead of just storing files, we map Triples:
`[PRIMARY_DB] -> [RESTRICTED_BY] -> [POST_MORTEM_NOV_24]`  
`[POST_MORTEM_NOV_24] -> [DECIDED_IN] -> [SLACK_THREAD_9912]`  

```mermaid
graph LR
    Input[Code/PR Input] --> Intent[Dify: Intent Extraction]
    Intent --> Memory[HydraDB: Relational Recall]
    Memory --> Logic{Conflict Found?}
    Logic -->|Yes| Alert[👻 GHOST ALERT: Cites Slack history]
    Logic -->|No| Pass[✅ CLEAN: No constraints violated]


1. The Success Path
Input:

Exporting users via ANALYTICS_REPLICA_URL

Output:

✅ Ghost Review: Clean! No conflicts detected.

2. The Violation (The "Aha" Moment)
Input:

Running pandas script against PRODUCTION_PRIMARY_URL for marketing export.

Output:

👻 GHOST REVIEW ALERT 👻
Constraint Violated: Ad-hoc scripts are banned from the Primary DB.
Reasoning: Mandated on Nov 14, 2024, to prevent row-level locking.
Evidence: [Link to Slack Thread #9912]

🚀 Running the Local Demo
To run the standalone CLI demo of the Ghost Review kill chain on your local machine:

1. Clone & Branch
bash
git clone <your-repo-url>
cd ContextCortex
# Switch to the dedicated demo environment
git checkout demov1
2. Set up the Python Environment
bash
python3 -m venv venv
source venv/bin/activate
# Install the core microservice dependencies
pip install fastapi uvicorn httpx pydantic python-dotenv
3. Boot the Historian Memory Service
Open your first terminal window and start the API:

bash
MEMORY_SERVICE_URL=http://localhost:8010 PYTHONPATH=. python3 -m services.memory.app.main
(Leave this running in the background).

4. Launch the Ghost Review CLI
Open a second terminal window (ensure your virtual environment is activated) and run:

bash
python3 scripts/interactive_demo.py
