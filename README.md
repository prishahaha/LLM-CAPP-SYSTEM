# LLM-Based Intelligent Computer Aided Process Planning (CAPP) for Manufacturing

## Research Question

Can a large language model (Claude, via the Anthropic API), combined with a
retrieval-augmented knowledge base of manufacturing process rules, generate
accurate, feasible, and expert-comparable process plans (operation sequences,
machine/tool selection, and parameter recommendations) for machined parts —
and how does its performance compare to traditional rule-based CAPP systems?

## Tech Stack

- **Python** — core implementation language
- **Anthropic Claude** (`anthropic` Python SDK) — LLM backbone for reasoning
  over part specifications and generating process plans
- **LangChain** (`langchain`, `langchain-anthropic`, `langchain-community`) —
  orchestration, prompting, and agent tooling around the LLM
- **ChromaDB** — vector store for the manufacturing knowledge base (RAG)
- **Streamlit** — interactive front-end for demoing and evaluating the system
- **pandas / numpy** — data handling and analysis
- **matplotlib / seaborn** — result visualization
- **sentence-transformers** — embeddings for knowledge retrieval
- **pytest** — automated testing
- **fpdf2** — generating PDF process plan reports

## Folder Structure

```
llm-capp-system/
├── dataset/           # Synthetic/benchmark part specifications and test cases
├── knowledge/         # Manufacturing knowledge base + ChromaDB vector store
├── agent/             # LLM agent logic (prompting, tool use, orchestration)
├── evaluation/         # Evaluation scripts and metrics for generated plans
├── app/               # Streamlit application code
├── results/figures/   # Generated charts and evaluation figures
├── tests/             # Automated tests (incl. environment sanity checks)
└── docs/               # Project documentation and write-ups
```

## Setup Instructions

1. **Clone the repository and enter the project directory.**

2. **Create and activate a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate      # macOS/Linux
   venv\Scripts\activate         # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` and set your `ANTHROPIC_API_KEY`. `.env` is
   gitignored and should never be committed.

5. **Verify your setup:**
   ```bash
   pytest tests/test_environment.py -v
   ```
   This confirms all dependencies are installed, your API key is loaded,
   and a live call to the Anthropic API succeeds.

6. **Run the app** (once implemented):
   ```bash
   streamlit run app/main.py
   ```

## Team

| Name | Role | Contact |
| ---- | ---- | ------- |
| _TBD_ | _TBD_ | _TBD_ |
