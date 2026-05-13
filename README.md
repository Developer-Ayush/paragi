# Paragi: A Continuous Learning Graph Intelligence Architecture

Paragi is an experimental cognitive runtime that prioritizes **relational inference** and **continuous learning** over static token prediction. Unlike traditional LLMs, Paragi maintains a living knowledge graph where every new fact strengthens the collective intelligence.

## 🧠 Core Architecture

- **Nodes as Pure Data Points**: Nodes in Paragi have no intrinsic meaning or embeddings. All behavior, meaning, and direction emerge from the **Edges**.
- **1024-Dimensional Edge Vectors**: Every edge carries a high-fidelity vector split into a 700-dim **Knowledge Block** (encoding 20 named human cognitive factors) and a 324-dim **Control Block** (governing activation spreading).
- **Multi-Hop Traversal**: Reasoning is performed via path discovery across typed edges (CAUSES, ANALOGY, SYNERGY, etc.) rather than simple similarity search.
- **Continuous Learning**: A Hebbian-inspired update rule ensures the graph matures with every interaction.
- **Democratic Consensus**: Contradictions are resolved through structural path voting and confidence scoring.

## 🚀 Features

- **AGI-Ready Reasoning**: Supports complex inter-domain reasoning through deep graph traversal.
- **Real-Time Knowledge**: Fetches latest data from the internet (Wikipedia/Crawl) and digests it into graph edges for future use.
- **Contribution Economy**: Users are co-builders. Every new fact taught to the main graph awards **usage credits**.
- **Personalized Memory**: Private "Personal Graphs" store individual context without sharing it with the main model.
- **Answer Evolution**: History isn't just text; it's a timeline. See how Paragi's understanding of your past questions improves over time.
- **Streaming UI**: Token-by-token streaming for a smooth, modern chat experience.
- **Secure Auth**: Full Firebase integration with Google Login.

## 🛠 Tech Stack

- **Backend**: FastAPI (Python), HDF5 (Graph Store), Bloom Filters (RAM Indexing), Ollama (Local LLM Refinement).
- **Frontend**: Next.js (React), Framer Motion (Animations), Tailwind CSS, Firebase Auth.

## 🚦 Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- [Ollama](https://ollama.com/) (running locally)
- Firebase Project (for Auth)

### Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

## 📖 Research Paper

The full architecture overview and technical specifications can be found in `index.html` in the root directory.

---
*Built with ❤️ for a future of open, explainable, and evolving intelligence.*
