import json, os, time, re
from dotenv import load_dotenv
from langchain_aws import ChatBedrockConverse
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from knowledge.build_knowledge_base import retrieve_relevant_rules

load_dotenv()

SYSTEM_PROMPT = """You are an expert manufacturing process planning engineer with
20 years of experience in CNC machining and precision manufacturing.
Your task is to generate complete, correctly sequenced manufacturing
process plans for mechanical parts described in natural language.

Always follow these sequencing rules strictly:
1. Facing and centering is always the very first operation
2. All rough operations before semi-finish, semi-finish before finish
3. Centre drilling before drilling, drilling before boring, boring before reaming
4. Internal features (holes, bores, pockets) before external finishing
5. Keyway milling after the cylinder it sits on is finish-turned
6. O-ring groove and thread cutting after finish turning of that diameter
7. Grinding is always the last size-controlling operation
8. Chamfering and deburring are always the final operations

You must respond ONLY with a valid JSON object.
No explanation, no markdown, no code fences. Just the raw JSON."""

llm = ChatBedrockConverse(
    model_id=os.getenv("BEDROCK_MODEL_ID", "us.meta.llama3-1-8b-instruct-v1:0"),
    region_name=os.getenv("AWS_REGION", "us-east-1"),
    temperature=0.1,
    max_tokens=4096
)


def switch_model(new_model_id: str):
    global llm
    llm = ChatBedrockConverse(
        model_id=new_model_id,
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        temperature=0.1,
        max_tokens=4096
    )
    print(f"Model switched to: {new_model_id}")


def load_few_shot_examples(n: int = 2) -> str:
    dataset_path = os.getenv("DATASET_PATH", "dataset/synthetic_parts.json")
    try:
        with open(dataset_path, "r") as f:
            data = json.load(f)
        examples = data[:n]
        result = ""
        for ex in examples:
            result += f"EXAMPLE INPUT: {ex['part_description']}\n"
            result += f"EXAMPLE OUTPUT:\n{json.dumps({'features_identified': ex['features_list'], 'process_plan': ex['process_plan']}, indent=2)}\n\n"
        return result
    except Exception:
        return ""


def call_llm_with_retry(prompt_text: str,
                         max_retries: int = 3) -> str:
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{input}")
    ])
    chain = prompt | llm | StrOutputParser()

    for attempt in range(max_retries):
        try:
            result = chain.invoke({"input": prompt_text})
            time.sleep(0.5)
            return result
        except Exception as e:
            if "ThrottlingException" in str(e) or "rate" in str(e).lower():
                wait = 2 ** attempt
                print(f"Rate limited — waiting {wait}s before retry {attempt+1}")
                time.sleep(wait)
            else:
                raise e
    raise Exception("Max retries exceeded")


def parse_json_response(raw: str) -> dict:
    raw = raw.strip()
    # Strip markdown code fences
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"^```\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    raw = raw.strip()

    # Try direct parse first
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Try extracting outermost JSON object
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start != -1 and end > start:
        candidate = raw[start:end]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Try to fix truncated JSON by closing open brackets
    candidate = raw[start:] if start != -1 else raw
    open_braces   = candidate.count("{") - candidate.count("}")
    open_brackets = candidate.count("[") - candidate.count("]")
    # Remove trailing incomplete key-value pair
    last_comma = candidate.rfind(",")
    last_brace  = candidate.rfind("}")
    last_bracket = candidate.rfind("]")
    if last_comma > max(last_brace, last_bracket):
        candidate = candidate[:last_comma]
    # Close open structures
    candidate += "]" * open_brackets + "}" * open_braces
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        raise ValueError(
            f"Could not parse JSON from LLM response. "
            f"First 300 chars: {raw[:300]}"
        )


def generate_process_plan(part_description: str) -> dict:
    # STEP 1 — Feature extraction
    feature_prompt = f"""
    Analyse this mechanical part description and extract its features.
    Part description: {part_description}

    Respond ONLY with this JSON structure, no other text:
    {{
      "part_type": "shaft or flange or bracket or coupling or gear or bearing_housing or pulley or cover_plate or bushing or connecting_rod",
      "material": "mild_steel or EN24_alloy_steel or cast_iron or aluminium_6061 or stainless_steel_316",
      "features": ["list of feature names from: round_external_cylinder, through_hole, blind_hole, rectangular_blind_slot, O_ring_groove, thread_external, thread_internal, chamfer, rectangular_pocket, rectangular_through_slot, taper, rectangular_through_step, circular_end_pocket"],
      "tolerance": "h6 or H7 or H8 or IT9",
      "surface_finish_Ra": 0.8 or 1.6 or 3.2 or 6.3,
      "key_dimensions": "brief dimension summary as string"
    }}
    """

    raw_features = call_llm_with_retry(feature_prompt)
    extracted = parse_json_response(raw_features)

    # STEP 2 — RAG knowledge retrieval
    all_rules = []

    search_queries = [
        f"operations for {extracted.get('material','steel')} {extracted.get('part_type','')}",
        f"tolerance {extracted.get('tolerance','IT9')} requirements finishing operation",
        f"sequencing rules process planning"
    ]
    for feature in extracted.get("features", []):
        search_queries.append(f"operations needed for {feature}")
        search_queries.append(f"tool selection {feature} {extracted.get('material','steel')}")

    seen = set()
    for query in search_queries:
        results = retrieve_relevant_rules(query, n_results=3)
        for r in results:
            if r["text"] not in seen:
                seen.add(r["text"])
                all_rules.append(r["text"])

    rules_context = "\n".join(all_rules[:20])

    # STEP 3 — Process plan generation
    few_shot = load_few_shot_examples(n=2)

    plan_prompt = f"""
    Generate a complete manufacturing process plan for this part.

    PART DESCRIPTION: {part_description}

    EXTRACTED FEATURES:
    {json.dumps(extracted, indent=2)}

    RELEVANT MANUFACTURING RULES FROM KNOWLEDGE BASE:
    {rules_context}

    {f"EXAMPLES OF CORRECT PROCESS PLANS:{chr(10)}{few_shot}" if few_shot else ""}

    Generate a complete process plan following ALL sequencing rules.
    Respond ONLY with this exact JSON structure:
    {{
      "features_identified": ["list of feature names"],
      "process_plan": [
        {{
          "step": 1,
          "operation": "operation name",
          "machine": "machine name",
          "tool": "tool name",
          "cutting_params": "speed/feed/doc summary",
          "purpose": "why this operation is needed",
          "sequencing_rule": "which rule justifies this position"
        }}
      ],
      "total_operations": 0,
      "planning_notes": "any important notes about this part"
    }}
    """

    raw_plan = call_llm_with_retry(plan_prompt)
    plan_data = parse_json_response(raw_plan)

    # STEP 4 — Validate and assemble final output
    process_plan = plan_data.get("process_plan", [])

    if len(process_plan) < 3:
        raise ValueError(f"Plan too short: only {len(process_plan)} operations")
    if len(process_plan) > 20:
        process_plan = process_plan[:20]

    final_output = {
        "part_description": part_description,
        "part_type": extracted.get("part_type", "unknown"),
        "material": extracted.get("material", "unknown"),
        "tolerance": extracted.get("tolerance", "unknown"),
        "surface_finish_Ra": extracted.get("surface_finish_Ra", 3.2),
        "key_dimensions": extracted.get("key_dimensions", ""),
        "features_identified": plan_data.get("features_identified",
                                             extracted.get("features", [])),
        "retrieved_rules_used": all_rules[:10],
        "process_plan": process_plan,
        "total_operations": len(process_plan),
        "planning_notes": plan_data.get("planning_notes", "")
    }

    return final_output
