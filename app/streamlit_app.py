import json
import os
from datetime import datetime, timezone
from decimal import Decimal

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


def _to_epoch(value) -> int:
    """Coerce created_at (int, Decimal, numeric string or ISO string) to epoch seconds."""
    if isinstance(value, (int, float, Decimal)):
        return int(value)
    if isinstance(value, str):
        v = value.strip()
        try:
            return int(float(v))
        except ValueError:
            pass
        try:
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except ValueError:
            return 0
    return 0


st.set_page_config(
    page_title="CAPP-AI: Intelligent Process Planning",
    page_icon="⚙️",
    layout="wide"
)

DEFAULT_PAGE = "🔧 Generate Process Plan"
for state_key, default_value in {
    "active_plan_id": None,
    "active_result": None,
    "history": None,
    "page": DEFAULT_PAGE,
    "history_limit": 25,
    "part_description": "",
    "active_plan_created_at": None,
    "active_plan_loaded_from_history": False,
    "history_unavailable": False,
    "sidebar_error": None
}.items():
    if state_key not in st.session_state:
        st.session_state[state_key] = default_value


def refresh_history():
    try:
        from storage.dynamo_store import list_plans

        st.session_state.history = list_plans()
        st.session_state.history_unavailable = False
    except Exception as error:
        st.session_state.history = []
        st.session_state.history_unavailable = True
        st.session_state.sidebar_error = str(error)


# Restore a plan from the URL (?plan=<id>) after a browser refresh
if not st.session_state.get("_initial_plan_checked", False):
    st.session_state._initial_plan_checked = True
    query_plan_id = st.query_params.get("plan")
    if query_plan_id:
        try:
            from storage.dynamo_store import get_plan, rebuild_result

            stored_plan = get_plan(query_plan_id)
            if stored_plan is None:
                raise ValueError(f"Saved plan {query_plan_id} was not found")
            st.session_state.active_result = rebuild_result(stored_plan)
            st.session_state.active_plan_id = query_plan_id
            st.session_state.active_plan_created_at = stored_plan.get("created_at")
            st.session_state.active_plan_loaded_from_history = True
            st.session_state.part_description = st.session_state.active_result.get(
                "part_description", ""
            )
        except Exception as error:
            if "plan" in st.query_params:
                del st.query_params["plan"]
            st.session_state.sidebar_error = f"Could not load saved plan: {error}"


def clear_plan_query():
    if "plan" in st.query_params:
        del st.query_params["plan"]


def new_plan_callback():
    st.session_state.active_plan_id = None
    st.session_state.active_result = None
    st.session_state.active_plan_created_at = None
    st.session_state.active_plan_loaded_from_history = False
    st.session_state.part_description = ""
    st.session_state.page = DEFAULT_PAGE
    clear_plan_query()


def select_history_callback(plan_id):
    try:
        from storage.dynamo_store import get_plan, rebuild_result

        stored_plan = get_plan(plan_id)
        if stored_plan is None:
            raise ValueError(f"Saved plan {plan_id} was not found")
        result = rebuild_result(stored_plan)
        st.session_state.active_plan_id = plan_id
        st.session_state.active_result = result
        st.session_state.active_plan_created_at = stored_plan.get("created_at")
        st.session_state.active_plan_loaded_from_history = True
        st.session_state.part_description = result.get("part_description", "")
        st.session_state.page = DEFAULT_PAGE
        st.session_state.sidebar_error = None
        st.query_params["plan"] = plan_id
    except Exception as error:
        st.session_state.sidebar_error = f"Could not load saved plan: {error}"


def delete_history_callback(plan_id):
    try:
        from storage.dynamo_store import delete_plan

        delete_plan(plan_id)
        if st.session_state.active_plan_id == plan_id:
            st.session_state.active_plan_id = None
            st.session_state.active_result = None
            st.session_state.active_plan_created_at = None
            st.session_state.active_plan_loaded_from_history = False
            st.session_state.part_description = ""
            clear_plan_query()
        st.session_state.sidebar_error = None
        refresh_history()
    except Exception as error:
        st.session_state.sidebar_error = f"Could not delete saved plan: {error}"


def show_older_plans_callback():
    st.session_state.history_limit += 25


def local_plan_datetime(created_at):
    return datetime.fromtimestamp(_to_epoch(created_at))


def format_params(value):
    """Turn cutting-parameter dicts / JSON strings into a readable line."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return "Refer handbook" if "refer_handbook" in value else value
    if isinstance(value, dict):
        parts = []
        if value.get("speed_mpm") and value["speed_mpm"] != "refer_handbook":
            parts.append(f"Speed: {value['speed_mpm']} m/min")
        if value.get("feed_mm_rev") and value["feed_mm_rev"] != "refer_handbook":
            parts.append(f"Feed: {value['feed_mm_rev']} mm/rev")
        if value.get("doc_mm") and value["doc_mm"] != "refer_handbook":
            parts.append(f"DoC: {value['doc_mm']} mm")
        return " | ".join(parts) if parts else "Refer handbook"
    return "Refer handbook"


def build_plan_dataframe(plan):
    """Shared formatting for the process-plan table (used on two pages)."""
    dataframe = pd.DataFrame(plan)
    for column in ("tool", "machine"):
        if column in dataframe.columns:
            dataframe[column] = dataframe[column].apply(
                lambda value: value.replace("_", " ")
                if isinstance(value, str) else value
            )
    if "operation" in dataframe.columns:
        dataframe["operation"] = dataframe["operation"].apply(
            lambda value: value.replace("_", " ").title()
            if isinstance(value, str) else value
        )
    if "cutting_params" in dataframe.columns:
        dataframe["cutting_params"] = dataframe["cutting_params"].apply(
            format_params
        )
    dataframe = dataframe.rename(columns={
        "step": "Step",
        "operation": "Operation",
        "machine": "Machine",
        "tool": "Tool",
        "cutting_params": "Cutting Parameters",
        "purpose": "Purpose"
    })
    display_columns = [
        column for column in (
            "Step", "Operation", "Machine", "Tool",
            "Cutting Parameters", "Purpose"
        ) if column in dataframe.columns
    ]
    return dataframe[display_columns]


def render_result(result, plan_id=None):
    st.success(
        f"✅ Process plan generated — "
        f"**{result.get('total_operations', 0)} operations**"
    )
    if plan_id:
        st.caption(f"💾 Saved to AWS DynamoDB — ID: {plan_id[:8]}")

    meta_col1, meta_col2, meta_col3 = st.columns(3)
    meta_col1.metric(
        "Part Type",
        str(result.get("part_type") or "—").replace("_", " ").title()
    )
    meta_col2.metric(
        "Material",
        str(result.get("material") or "—").replace("_", " ").title()
    )
    meta_col3.metric("Tolerance", str(result.get("tolerance") or "—"))

    st.markdown("**Features Identified:**")
    features = result.get("features_identified", [])
    if features and isinstance(features[0], dict):
        features = [feature.get("feature_name", "") for feature in features]
    feature_str = "  ".join(f"`{feature}`" for feature in features)
    st.markdown(feature_str if feature_str else "_None identified_")

    st.markdown("**Process Plan:**")
    plan = result.get("process_plan", [])
    if plan:
        st.dataframe(
            build_plan_dataframe(plan),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Step": st.column_config.NumberColumn(width="small"),
                "Operation": st.column_config.TextColumn(width="medium"),
                "Machine": st.column_config.TextColumn(width="medium"),
                "Tool": st.column_config.TextColumn(width="large"),
                "Cutting Parameters": st.column_config.TextColumn(width="large"),
                "Purpose": st.column_config.TextColumn(width="large")
            }
        )

    if result.get("planning_notes"):
        st.info(f"📝 {result['planning_notes']}")
    with st.expander("🔍 Knowledge Base Rules Retrieved"):
        rules = result.get("retrieved_rules_used", [])
        if not rules:
            st.caption("No retrieved rules stored for this plan.")
        for rule in rules:
            st.markdown(f"- {str(rule)[:150]}...")

    st.download_button(
        label="⬇️ Download Plan as JSON",
        data=json.dumps(result, indent=2, default=str),
        file_name=f"process_plan_{result.get('part_type', 'part')}.json",
        mime="application/json",
        key=f"download_plan_{plan_id or 'unsaved'}"
    )


# ── Sidebar navigation and recent plan history ───────────────
st.sidebar.title("⚙️ CAPP-AI")
st.sidebar.markdown("Intelligent Manufacturing Process Planning")
st.sidebar.button(
    "➕ New plan",
    use_container_width=True,
    on_click=new_plan_callback
)

page = st.sidebar.radio(
    "Navigate",
    ["🔧 Generate Process Plan",
     "📊 Dataset Explorer",
     "📈 Evaluation Results",
     "🗂️ Saved Plans",
     "ℹ️ About This Research"],
    key="page"
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Recent plans**")
if st.session_state.history is None:
    refresh_history()

if st.session_state.history_unavailable:
    st.sidebar.caption("History unavailable — check AWS/DynamoDB setup")
elif not st.session_state.history:
    st.sidebar.caption("No saved plans yet")
else:
    today = datetime.now().date()
    groups = {
        "Today": [],
        "Yesterday": [],
        "Previous 7 days": [],
        "Older": []
    }
    visible_history = st.session_state.history[:st.session_state.history_limit]
    for history_item in visible_history:
        local_time = local_plan_datetime(history_item.get("created_at"))
        age = (today - local_time.date()).days
        if age <= 0:
            group = "Today"
        elif age == 1:
            group = "Yesterday"
        elif age <= 7:
            group = "Previous 7 days"
        else:
            group = "Older"
        groups[group].append(history_item)

    for group_name, group_items in groups.items():
        if not group_items:
            continue
        st.sidebar.caption(group_name)
        for history_item in group_items:
            plan_id = history_item["plan_id"]
            prompt = history_item.get("prompt", "")
            label = prompt[:38] + ("…" if len(prompt) > 38 else "")
            title_col, delete_col = st.sidebar.columns([6, 1])
            title_col.button(
                label,
                key=f"hist_{plan_id}",
                type=(
                    "primary"
                    if st.session_state.active_plan_id == plan_id
                    else "secondary"
                ),
                use_container_width=True,
                on_click=select_history_callback,
                args=(plan_id,)
            )
            delete_col.button(
                "🗑",
                key=f"del_{plan_id}",
                on_click=delete_history_callback,
                args=(plan_id,)
            )

    if len(st.session_state.history) > st.session_state.history_limit:
        st.sidebar.button(
            "Show older plans",
            use_container_width=True,
            on_click=show_older_plans_callback
        )

if st.session_state.sidebar_error:
    st.sidebar.caption(st.session_state.sidebar_error)

st.sidebar.markdown("---")
st.sidebar.markdown(
    f"**Model:** `{os.getenv('BEDROCK_MODEL_ID','us.meta.llama3-1-8b-instruct-v1:0')}`"
)
st.sidebar.markdown("**Backend:** AWS Bedrock")
st.sidebar.markdown("**RAG:** ChromaDB + MiniLM")

# ════════════════════════════════════════════════════════════
# PAGE 1 — Generate Process Plan
# ════════════════════════════════════════════════════════════
if page == DEFAULT_PAGE:
    st.title("🔧 Process Plan Generator")
    st.markdown(
        "Enter a mechanical part description in natural language. "
        "The AI agent will extract features, query the manufacturing "
        "knowledge base, and generate a complete process plan."
    )

    col1, col2 = st.columns([4, 6])
    with col1:
        part_description = st.text_area(
            "Part Description",
            height=200,
            placeholder=(
                "Example: Mild steel cylindrical shaft, 80mm diameter, "
                "200mm length, one keyway 20x8mm, two M10 blind threaded "
                "holes, H7 tolerance on bearing seats, "
                "Ra 1.6 surface finish on journals"
            ),
            key="part_description"
        )
        generate_btn = st.button(
            "⚡ Generate Process Plan",
            type="primary",
            use_container_width=True
        )

    with col2:
        saved_ok = False
        if generate_btn:
            if not part_description.strip():
                st.error("Please enter a part description.")
            else:
                with st.spinner("Analysing part and generating process plan..."):
                    try:
                        from agent.process_planning_agent import (
                            generate_process_plan
                        )

                        result = generate_process_plan(part_description)
                        st.session_state.active_result = result
                        st.session_state.active_plan_id = None
                        st.session_state.active_plan_created_at = None
                        st.session_state.active_plan_loaded_from_history = False
                        clear_plan_query()

                        try:
                            from storage.dynamo_store import save_plan

                            plan_id = save_plan(part_description, result)
                            st.session_state.active_plan_id = plan_id
                            st.query_params["plan"] = plan_id
                            st.session_state.sidebar_error = None
                            refresh_history()
                            saved_ok = True
                        except Exception as error:
                            st.warning(
                                "Plan generated but could not be saved to "
                                f"DynamoDB: {error}"
                            )
                    except Exception as error:
                        st.error(f"❌ Generation failed: {str(error)}")
                        st.info(
                            "Check your AWS credentials in .env "
                            "and ensure Bedrock model access is enabled."
                        )

        if saved_ok:
            # Redraw so the new plan appears in the sidebar immediately
            st.rerun()

        if st.session_state.active_result is not None:
            if (
                st.session_state.active_plan_loaded_from_history
                and st.session_state.active_plan_id
            ):
                saved_at = local_plan_datetime(
                    st.session_state.active_plan_created_at
                )
                st.caption(
                    "Loaded from history · saved "
                    f"{saved_at.strftime('%Y-%m-%d %H:%M')}"
                )
            render_result(
                st.session_state.active_result,
                st.session_state.active_plan_id
            )
        elif not generate_btn:
            st.info(
                "👈 Enter a part description and click "
                "**Generate Process Plan** to begin."
            )

# ════════════════════════════════════════════════════════════
# PAGE 2 — Dataset Explorer
# ════════════════════════════════════════════════════════════
elif page == "📊 Dataset Explorer":
    st.title("📊 Dataset Explorer")
    st.markdown(
        "Browse the CAPP-Bench-600 synthetic dataset. "
        "Each entry contains a part description paired with "
        "its manufacturing process plan."
    )

    dataset_path = os.getenv("DATASET_PATH", "dataset/synthetic_parts.json")

    if not os.path.exists(dataset_path):
        st.error(
            "dataset/synthetic_parts.json not found. "
            "Run Phase 2 dataset generator first."
        )
    else:
        with open(dataset_path) as f:
            dataset = json.load(f)

        total = len(dataset)
        avg_ops = sum(
            d.get("total_operations", 0) for d in dataset
        ) / total if total else 0
        materials = list(set(d.get("material", "") for d in dataset))

        m1, m2, m3 = st.columns(3)
        m1.metric("Total Parts", total)
        m2.metric("Avg Operations / Plan", f"{avg_ops:.1f}")
        m3.metric("Materials Covered", len(materials))

        st.markdown("---")

        f1, f2, f3 = st.columns(3)
        part_types = sorted(set(d.get("part_type", "") for d in dataset))
        sel_types = f1.multiselect("Part Type", part_types, default=[])
        sel_mats = f2.multiselect("Material", sorted(materials), default=[])
        min_ops, max_ops = f3.slider("Operations range", 1, 20, (1, 20))

        filtered = [
            d for d in dataset
            if (not sel_types or d.get("part_type") in sel_types)
            and (not sel_mats or d.get("material") in sel_mats)
            and min_ops <= d.get("total_operations", 0) <= max_ops
        ]

        st.markdown(f"**Showing {len(filtered)} of {total} parts**")

        rows = [{
            "Part ID":    d.get("part_id", ""),
            "Type":       d.get("part_type", "").replace("_", " "),
            "Material":   d.get("material", "").replace("_", " "),
            "Tolerance":  d.get("tolerance", ""),
            "Ra (μm)":    d.get("surface_finish_Ra", ""),
            "Operations": d.get("total_operations", 0),
            "Description": d.get("part_description", "")[:80] + "..."
        } for d in filtered[:200]]

        df = pd.DataFrame(rows)

        selected = st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )

        if (selected and
                selected.get("selection") and
                selected["selection"].get("rows")):
            idx = selected["selection"]["rows"][0]
            part = filtered[idx]
            st.markdown("---")
            st.markdown(f"### 🔍 {part['part_id']} Detail")
            st.markdown(f"**Description:** {part.get('part_description','')}")

            plan = part.get("process_plan", [])
            if plan:
                plan_df = pd.DataFrame(plan)
                show_cols = [c for c in
                    ["step", "operation", "machine", "tool", "purpose"]
                    if c in plan_df.columns]
                st.dataframe(
                    plan_df[show_cols],
                    use_container_width=True,
                    hide_index=True
                )

# ════════════════════════════════════════════════════════════
# SAVED PLANS — AWS DynamoDB
# ════════════════════════════════════════════════════════════
elif page == "🗂️ Saved Plans":
    st.title("🗂️ Saved Plans")
    st.markdown(
        "Browse process plans generated in this app and saved to AWS DynamoDB."
    )

    try:
        from storage.dynamo_store import get_plan, list_plans

        with st.spinner("Loading saved plans from AWS DynamoDB..."):
            plan_summaries = list_plans()
            plans = [
                get_plan(summary["plan_id"]) or summary
                for summary in plan_summaries
            ]
    except Exception as e:
        st.error(
            f"Could not load saved plans: {e}. Run "
            "`py -m storage.create_table` and check IAM permissions."
        )
    else:
        st.metric("Total Saved Plans", len(plans))
        rows = [{
            "Time": local_plan_datetime(
                plan.get("created_at")
            ).strftime("%Y-%m-%d %H:%M"),
            "Prompt": plan.get("prompt", "")[:80],
            "Part Type": str(plan.get("part_type", "")).replace("_", " ").title(),
            "Material": str(plan.get("material", "")).replace("_", " ").title(),
            "Operations": plan.get("operations_summary", "")
        } for plan in plans]
        df = pd.DataFrame(
            rows,
            columns=["Time", "Prompt", "Part Type", "Material", "Operations"]
        )
        selected = st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )

        if (selected and selected.get("selection")
                and selected["selection"].get("rows")):
            idx = selected["selection"]["rows"][0]
            plan = plans[idx]
            st.markdown("---")
            st.markdown("### Selected Plan")
            st.markdown(f"**Prompt:** {plan.get('prompt', '')}")

            try:
                process_plan = json.loads(plan.get("process_plan_json", "[]"))
            except json.JSONDecodeError as e:
                st.error(f"Could not parse this plan's process-plan data: {e}")
                process_plan = []

            if process_plan:
                st.dataframe(
                    build_plan_dataframe(process_plan),
                    use_container_width=True,
                    hide_index=True
                )

            st.button(
                "Delete this plan",
                key=f"delete_{plan['plan_id']}",
                on_click=delete_history_callback,
                args=(plan["plan_id"],)
            )

        csv_columns = [
            "plan_id", "created_at", "created_at_readable", "prompt",
            "part_type", "material", "tolerance", "total_operations",
            "operations_summary"
        ]
        export_rows = []
        for plan in plans:
            row = {
                column: plan.get(column, "")
                for column in csv_columns
                if column != "created_at_readable"
            }
            row["created_at"] = _to_epoch(plan.get("created_at"))
            row["created_at_readable"] = local_plan_datetime(
                plan.get("created_at")
            ).strftime("%Y-%m-%d %H:%M")
            export_rows.append(row)
        csv_data = pd.DataFrame(export_rows, columns=csv_columns).to_csv(index=False)
        st.download_button(
            "⬇️ Export all saved plans as CSV",
            data=csv_data,
            file_name="saved_process_plans.csv",
            mime="text/csv"
        )

# ════════════════════════════════════════════════════════════
# PAGE 3 — Evaluation Results
# ════════════════════════════════════════════════════════════
elif page == "📈 Evaluation Results":
    st.title("📈 Evaluation Results")
    st.markdown(
        "Comparison of the LLM-RAG agent against the rule-based "
        "CAPP baseline across 5 metrics evaluated on 100 held-out test parts."
    )

    results_path = "results/evaluation_results.json"
    table_path   = "results/comparison_table.csv"

    if not os.path.exists(results_path):
        st.warning(
            "No evaluation results found. "
            "Run `py -m evaluation.evaluate --full` first."
        )
    else:
        with open(results_path) as f:
            results = json.load(f)

        summary = results.get("summary", {})
        rule_avgs = summary.get("rule_based_averages", {})
        llm_avgs  = summary.get("llm_agent_averages", {})

        st.markdown("### Summary")
        cols = st.columns(5)
        metric_map = {
            "feature_recognition_rate": "Feature Recognition",
            "operation_accuracy":        "Operation Accuracy",
            "sequence_correctness":      "Sequence Correctness",
            "operation_completeness":    "Completeness",
            "machine_selection_accuracy":"Machine Selection"
        }
        for col, (key, label) in zip(cols, metric_map.items()):
            llm_val  = llm_avgs.get(key, 0)
            rule_val = rule_avgs.get(key, 0)
            if key == "sequence_correctness":
                llm_val  = llm_val  * 100
                rule_val = rule_val * 100
            delta = round(llm_val - rule_val, 2)
            col.metric(
                label,
                f"{llm_val:.1f}%",
                delta=f"{delta:+.1f}% vs rule-based"
            )

        st.markdown("---")

        if os.path.exists(table_path):
            st.markdown("### Comparison Table")
            df = pd.read_csv(table_path)
            st.dataframe(
                df.style.highlight_max(
                    subset=["Rule-Based CAPP", "LLM Agent (Ours)"],
                    axis=1,
                    color="#d4edda"
                ),
                use_container_width=True,
                hide_index=True
            )

        st.markdown("---")

        st.markdown("### Charts")
        chart_col1, chart_col2 = st.columns(2)

        bar_path = "results/figures/bar_chart_comparison.png"
        box_path = "results/figures/accuracy_distribution.png"
        hm_path  = "results/figures/feature_recognition_heatmap.png"

        if os.path.exists(bar_path):
            chart_col1.image(bar_path,
                             caption="Rule-Based vs LLM Agent",
                             use_container_width=True)
        if os.path.exists(box_path):
            chart_col2.image(box_path,
                             caption="Operation Accuracy Distribution",
                             use_container_width=True)
        if os.path.exists(hm_path):
            st.image(hm_path,
                     caption="Accuracy by Part Type",
                     use_container_width=True)

        st.markdown("---")
        st.markdown(
            f"**Model evaluated:** `{summary.get('model_used','')}`  \n"
            f"**Parts evaluated:** {summary.get('total_parts_evaluated',0)}  \n"
            f"**Dataset:** CAPP-Bench-600 "
            f"(entries 500–599 held out as test set)"
        )

# ════════════════════════════════════════════════════════════
# PAGE 4 — About This Research
# ════════════════════════════════════════════════════════════
elif page == "ℹ️ About This Research":
    st.title("ℹ️ About This Research")

    st.markdown("""
    ## LLM-Based Intelligent Computer Aided Process Planning

    ### Research Question
    *Can a Retrieval-Augmented Generation (RAG) approach with Large Language
    Models generate manufacturing process plans comparable to rule-based CAPP
    systems, while accepting natural language part descriptions as input?*

    ### Methodology
    """)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
        **Dataset Construction**
        - 600 synthetic part-plan pairs (CAPP-Bench-600)
        - Feature vocabulary: FeatureNet 24 classes (Zhang et al., 2018)
        - Part types: mechanical component categories (cf. MechCAD)
        - Operation rules: standard machining practice, consistent with
          the Machining Data Handbook (Metcut, 1980)
        - Tolerance standard: ISO 286-1

        **System Architecture**
        - 🤖 LLM: Meta Llama 3.1 8B via AWS Bedrock
        - 🗄️ Vector DB: ChromaDB (local, persistent)
        - 🔍 Embeddings: sentence-transformers/all-MiniLM-L6-v2
        - 🔗 Orchestration: LangChain-AWS
        - 💾 Plan storage: AWS DynamoDB
        """)
    with c2:
        st.markdown("""
        **Evaluation**
        - 100 held-out test parts (PART_501 to PART_600)
        - 5 metrics: Feature Recognition, Operation Accuracy,
          Sequence Correctness, Completeness, Machine Selection
        - Baseline: Rule-based CAPP (direct lookup from the feature list)

        **Key Results** *(Llama 3.1 8B, 100 parts)*
        - ✅ Sequence Correctness: 100% (equal to rule-based)
        - ✅ Operation Completeness: 99.8%
        - ✅ Machine Selection: 97.9%
        - Operation Accuracy: 87.7%
        - Feature Recognition: 84.5%
        - ✅ 0/100 evaluation failures
        """)

    st.markdown("---")
    st.markdown("""
    ### Dataset Sources

    | Source | Used For | Link |
    |--------|----------|------|
    | FeatureNet (Zhang et al., 2018) | Feature vocabulary (24 classes) | [GitHub](https://github.com/madlabub/Machining-feature-dataset) |
    | MechCAD / BRT (2025) | Reference for part categories | [arXiv](https://arxiv.org/abs/2504.07134) |
    | Machining Data Handbook (Metcut, 1980) | Reference for operation rules and cutting parameters | [archive.org](https://archive.org/details/machiningdatahan0002unse) |
    | ISO 286-1 | Tolerance grades (H7 / h6 / H8 / IT9) | — |
    """)
    