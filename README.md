# LLM-Based Intelligent Computer-Aided Process Planning (CAPP)

An experimental process-planning system for machined parts. It uses an AWS
Bedrock chat model to interpret a natural-language part description, retrieves
manufacturing rules from a ChromaDB knowledge base, and produces a sequenced
process plan. A Streamlit app provides plan generation, dataset browsing,
evaluation-result views, and optional saved-plan history backed by Amazon
DynamoDB.

This is a research/demo project. Generated process plans and cutting parameters
must be checked by a qualified manufacturing engineer before use in production.

## What it does

1. Extracts part type, material, features, tolerance, surface finish, and
   dimensions from a text description.
2. Retrieves relevant process, tooling, machine, tolerance, and sequencing rules
   from the local manufacturing knowledge base.
3. Generates a JSON process plan with operations, machines, tools, parameters,
   purposes, and sequencing rationale.
4. Optionally saves plans to DynamoDB so they can be revisited from the app.
5. Compares an LLM planner with a rule-based baseline using the included
   synthetic benchmark and evaluation metrics.

## Technology

- Python
- AWS Bedrock through LangChain (`langchain-aws`)
- ChromaDB and Sentence Transformers (`all-MiniLM-L6-v2`) for rule retrieval
- Streamlit for the web app
- Amazon DynamoDB and boto3 for optional plan history
- pandas, NumPy, matplotlib, and seaborn for evaluation and visualizations

## Repository layout

```text
agent/        Bedrock-backed feature extraction and process-plan generation
app/          Streamlit application
dataset/      Synthetic benchmark data, vocabularies, and operation rules
evaluation/   Rule-based baseline, metrics, and evaluation runner
knowledge/    Manufacturing rules and ChromaDB index builder
results/      Example plans and checked-in evaluation outputs
storage/      DynamoDB table creation and plan persistence helpers
tests/        Environment and service smoke checks
requirements.txt
```

## Requirements

- Python 3.10 or later
- AWS credentials with access to the configured Bedrock model
- Access to Amazon Bedrock in the selected AWS region
- For saved-plan history: DynamoDB permissions and a `capp_process_plans` table
  (or a table name configured with `DYNAMODB_TABLE`)

## Setup

Run commands from the repository root.

### 1. Create a virtual environment and install dependencies

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configure AWS and project settings

Copy `.env.example` to `.env` and set values for your environment. At minimum,
configure AWS credentials using the AWS credential provider chain or the
`AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables, and
choose a Bedrock model available to your AWS account.

PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

The application settings in `.env.example` are:

| Variable | Purpose | Default |
| --- | --- | --- |
| `AWS_ACCESS_KEY_ID` | AWS access key, if not supplied by another credential provider | — |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key, if not supplied by another credential provider | — |
| `AWS_REGION` | AWS region for Bedrock and DynamoDB | `us-east-1` |
| `BEDROCK_MODEL_ID` | Bedrock model identifier | `us.meta.llama3-1-8b-instruct-v1:0` |
| `DYNAMODB_TABLE` | Table used for saved plans | `capp_process_plans` |
| `CHROMA_DB_PATH` | Local ChromaDB index directory | `knowledge/chroma_db` |
| `DATASET_PATH` | Dataset used by the app and evaluator | `dataset/synthetic_parts.json` |

Do not commit `.env` or real AWS credentials. Use an appropriately scoped AWS
identity and enable access to the selected Bedrock model in the AWS account and
region.

### 3. Build the local manufacturing knowledge base

The ChromaDB index is generated locally and is not included in the repository.
Build it before generating plans:

```bash
python knowledge/build_knowledge_base.py
```

This downloads/loads the Sentence Transformers embedding model on first use and
indexes the rules in `knowledge/manufacturing_rules.json` at `CHROMA_DB_PATH`.

### 4. Set up DynamoDB plan history (optional)

Plan generation can still succeed if DynamoDB is unavailable, but saved-plan
history and sidebar history require a reachable table. Create the configured
table with:

```bash
python -m storage.create_table
```

The AWS identity needs permission to describe/create the table during setup and
to scan, read, write, and delete items while using plan history.

### 5. Start the app

```bash
streamlit run app/streamlit_app.py
```

Open the local URL printed by Streamlit. Enter a part description and choose
**Generate Process Plan**. The app also includes a dataset explorer, evaluation
results, saved plans, and an about page. Generated plans can be downloaded as
JSON; saved plans can be reopened through the app history.

## Dataset and evaluation

The repository includes `dataset/synthetic_parts.json`, a synthetic dataset of
600 parts. To regenerate it:

```bash
python dataset/generate_dataset.py
```

Run the evaluation against the default 20-part test subset:

```bash
python -m evaluation.evaluate
```

Run the 100-part evaluation subset:

```bash
python -m evaluation.evaluate --full
```

Evaluation calls the configured Bedrock model for each test part and may incur
AWS usage charges. It writes comparison metrics to `results/`, including JSON,
CSV, a text summary, and charts under `results/figures/`.

## Checks

The environment smoke check makes a live Bedrock request and expects AWS
credentials and model access to be configured:

```bash
python tests/test_environment.py
```

The DynamoDB storage smoke check writes, reads, and deletes a temporary plan,
so run it only when the configured DynamoDB table and AWS permissions are ready:

```bash
python -m storage.test_storage
```

## Important notes

- This project is a research prototype, not a validated manufacturing
  execution system. Confirm operation sequencing, machine/tool selections,
  tolerances, and cutting parameters with qualified personnel.
- Dataset entries and encoded manufacturing rules are project artifacts. Treat
  benchmark scores as results for this implementation and dataset, not as
  proof of production readiness or general performance.
- AWS Bedrock and DynamoDB availability, permissions, model access, and charges
  are controlled by your AWS account.
