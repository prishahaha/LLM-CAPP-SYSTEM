import json
import os
from sentence_transformers import SentenceTransformer
import chromadb
from dotenv import load_dotenv

load_dotenv()

_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model

def build_chunks(rules: dict) -> list[str]:
    chunks = []

    for feature, data in rules.get("feature_to_operations", {}).items():
        ops = data.get("base_operations", [])
        source = data.get("source", "Machining Data Handbook")
        note = data.get("note", "")
        text = (f"FEATURE_RULE [{feature}]: To machine {feature}, "
                f"perform these operations in order: {', '.join(ops)}. "
                f"{note}. Source: {source}")
        chunks.append(text)

    for entry in rules.get("sequencing_rules", []):
        text = (f"SEQUENCING_RULE [priority {entry['priority']}]: "
                f"{entry['rule']}. Source: {entry['source']}")
        chunks.append(text)

    for grade, data in rules.get("tolerance_requirements", {}).items():
        text = (f"TOLERANCE_RULE [{grade}]: For {grade} tolerance, "
                f"mandatory finishing operation is {data['mandatory_operation']}. "
                f"Typical Ra: {data['typical_Ra']} microns. "
                f"Note: {data['note']}. Source: {data['source']}")
        chunks.append(text)

    for entry in rules.get("cutting_parameters", []):
        text = (f"CUTTING_PARAMS [{entry['material']} + {entry['operation']}]: "
                f"For {entry['operation']} of {entry['material']} — "
                f"cutting speed: {entry['speed_mpm']} m/min, "
                f"feed: {entry['feed_mm_rev']} mm/rev, "
                f"depth of cut: {entry['doc_mm']} mm. "
                f"Source: {entry['source']}")
        chunks.append(text)

    for key, data in rules.get("tool_selection_rules", {}).items():
        source = data.get("source", "Machining Data Handbook")
        if "rough" in data or "finish" in data:
            detail_parts = []
            if "rough" in data:
                detail_parts.append(f"roughing tool: {data['rough']}")
            if "finish" in data:
                detail_parts.append(f"finishing tool: {data['finish']}")
            detail = "; ".join(detail_parts)
        else:
            detail = f"tool: {data.get('tool', '')}"
        text = (f"TOOL_RULE [{key}]: {detail}. Source: {source}")
        chunks.append(text)

    for machine, data in rules.get("machine_capabilities", {}).items():
        ops = data.get("operations", [])
        suitable = data.get("suitable_for", [])
        note = data.get("note", "")
        source = data.get("source", "Machining Data Handbook")
        text = (f"MACHINE_RULE [{machine}]: Capable of operations: {', '.join(ops)}. "
                f"Suitable for part types: {', '.join(suitable)}. "
                f"{note}. Source: {source}")
        chunks.append(text)

    for grade, data in rules.get("surface_finish_requirements", {}).items():
        text = (f"SURFACE_FINISH_RULE [{grade}]: At Ra {data['value_microns']} microns, "
                f"required operation is {data['required_operation']}. "
                f"Note: {data['note']}. Source: {data['source']}")
        chunks.append(text)

    return chunks


def build_knowledge_base():
    rules_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "manufacturing_rules.json")
    with open(rules_path, encoding="utf-8") as f:
        rules = json.load(f)

    chunks = build_chunks(rules)

    model = get_embedding_model()
    embeddings = model.encode(chunks).tolist()

    chroma_path = os.getenv("CHROMA_DB_PATH", "knowledge/chroma_db")
    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_or_create_collection("manufacturing_rules")

    existing = collection.get()
    if existing["ids"]:
        collection.delete(ids=existing["ids"])

    ids = [f"chunk_{i}" for i in range(len(chunks))]
    collection.add(ids=ids, documents=chunks, embeddings=embeddings)

    print(f"Indexed {len(chunks)} chunks into ChromaDB collection 'manufacturing_rules' at {chroma_path}")
    return collection


if __name__ == "__main__":
    build_knowledge_base()


def retrieve_relevant_rules(query: str, n_results: int = 5) -> list[dict]:
    model = get_embedding_model()
    chroma_path = os.getenv("CHROMA_DB_PATH", "knowledge/chroma_db")
    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_collection("manufacturing_rules")
    query_embedding = model.encode([query]).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=n_results
    )
    return [
        {"rank": i + 1, "text": doc}
        for i, doc in enumerate(results["documents"][0])
    ]
