import streamlit as st
import json
import os
import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="CAPP-AI: Intelligent Process Planning",
    page_icon="⚙️",
    layout="wide"
)

# ── Sidebar navigation ──────────────────────────────────────
st.sidebar.title("⚙️ CAPP-AI")
st.sidebar.markdown("Intelligent Manufacturing Process Planning")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    ["🔧 Generate Process Plan",
     "📊 Dataset Explorer",
     "📈 Evaluation Results",
     "ℹ️ About This Research"]
)

st.sidebar.markdown("---")
st.sidebar.markdown(
    f"**Model:** `{os.getenv('BEDROCK_MODEL_ID','us.meta.llama3-1-8b-instruct-v1:0')}`"
)
st.sidebar.markdown("**Backend:** AWS Bedrock")
st.sidebar.markdown("**RAG:** ChromaDB + MiniLM")

# ════════════════════════════════════════════════════════════
# PAGE 1 — Generate Process Plan
# ════════════════════════════════════════════════════════════
if page == "🔧 Generate Process Plan":
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
            )
        )

        generate_btn = st.button(
            "⚡ Generate Process Plan",
            type="primary",
            use_container_width=True
        )

    with col2:
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

                        st.success(
                            f"✅ Process plan generated — "
                            f"**{result['total_operations']} operations**"
                        )

                        # Part summary
                        meta_col1, meta_col2, meta_col3 = st.columns(3)
                        meta_col1.metric("Part Type",
                                         result.get("part_type", "—").replace("_", " ").title())
                        meta_col2.metric("Material",
                                         result.get("material", "—").replace("_", " ").title())
                        meta_col3.metric("Tolerance",
                                         result.get("tolerance", "—"))

                        # Features identified
                        st.markdown("**Features Identified:**")
                        features = result.get("features_identified", [])
                        if features and isinstance(features[0], dict):
                            features = [f.get("feature_name", "") for f in features]
                        feature_str = "  ".join(
                            [f"`{f}`" for f in features]
                        )
                        st.markdown(feature_str if feature_str else "_None identified_")

                        # Process plan table
                        st.markdown("**Process Plan:**")
                        plan = result.get("process_plan", [])
                        if plan:
                            df = pd.DataFrame(plan)

                            # Format tool column — replace underscores with spaces
                            if "tool" in df.columns:
                                df["tool"] = df["tool"].str.replace("_", " ")

                            # Format machine column — replace underscores with spaces
                            if "machine" in df.columns:
                                df["machine"] = df["machine"].str.replace("_", " ")

                            # Format operation column — replace underscores with spaces
                            if "operation" in df.columns:
                                df["operation"] = df["operation"].str.replace("_", " ").str.title()

                            # Format cutting_params — convert JSON dict to readable string
                            def format_params(val):
                                if isinstance(val, dict):
                                    parts = []
                                    if val.get("speed_mpm") and val["speed_mpm"] != "refer_handbook":
                                        parts.append(f"Speed: {val['speed_mpm']} m/min")
                                    if val.get("feed_mm_rev") and val["feed_mm_rev"] != "refer_handbook":
                                        parts.append(f"Feed: {val['feed_mm_rev']} mm/rev")
                                    if val.get("doc_mm") and val["doc_mm"] != "refer_handbook":
                                        parts.append(f"DoC: {val['doc_mm']} mm")
                                    return " | ".join(parts) if parts else "Refer handbook"
                                if isinstance(val, str):
                                    try:
                                        import json
                                        parsed = json.loads(val)
                                        return format_params(parsed)
                                    except Exception:
                                        if "refer_handbook" in val:
                                            return "Refer handbook"
                                        return val
                                return "Refer handbook"

                            if "cutting_params" in df.columns:
                                df["cutting_params"] = df["cutting_params"].apply(format_params)

                            # Rename columns for display
                            df = df.rename(columns={
                                "step":          "Step",
                                "operation":     "Operation",
                                "machine":       "Machine",
                                "tool":          "Tool",
                                "cutting_params":"Cutting Parameters",
                                "purpose":       "Purpose"
                            })

                            display_cols = [c for c in
                                ["Step", "Operation", "Machine",
                                 "Tool", "Cutting Parameters", "Purpose"]
                                if c in df.columns]

                            st.dataframe(
                                df[display_cols],
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

                        # Planning notes
                        if result.get("planning_notes"):
                            st.info(f"📝 {result['planning_notes']}")

                        # RAG rules used
                        with st.expander(
                            "🔍 Knowledge Base Rules Retrieved"
                        ):
                            for rule in result.get(
                                "retrieved_rules_used", []
                            ):
                                st.markdown(f"- {rule[:150]}...")

                        # Download
                        st.download_button(
                            label="⬇️ Download Plan as JSON",
                            data=json.dumps(result, indent=2),
                            file_name=f"process_plan_{result.get('part_type','part')}.json",
                            mime="application/json"
                        )

                    except Exception as e:
                        st.error(f"❌ Generation failed: {str(e)}")
                        st.info(
                            "Check your AWS credentials in .env "
                            "and ensure Bedrock model access is enabled."
                        )
        else:
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
        "its verified manufacturing process plan."
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

        # Summary metrics
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

        # Filters
        f1, f2, f3 = st.columns(3)
        part_types = sorted(set(d.get("part_type", "") for d in dataset))
        sel_types = f1.multiselect(
            "Part Type", part_types, default=[]
        )
        sel_mats = f2.multiselect(
            "Material", sorted(materials), default=[]
        )
        min_ops, max_ops = f3.slider(
            "Operations range", 1, 20, (1, 20)
        )

        filtered = [
            d for d in dataset
            if (not sel_types or d.get("part_type") in sel_types)
            and (not sel_mats or d.get("material") in sel_mats)
            and min_ops <= d.get("total_operations", 0) <= max_ops
        ]

        st.markdown(f"**Showing {len(filtered)} of {total} parts**")

        # Table
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

        # Detail view on row click
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
# PAGE 3 — Evaluation Results
# ════════════════════════════════════════════════════════════
elif page == "📈 Evaluation Results":
    st.title("📈 Evaluation Results")
    st.markdown(
        "Comparison of the LLM-RAG agent against the rule-based "
        "CAPP baseline across 5 metrics evaluated on 100 unseen test parts."
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

        # Summary metrics row
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

        # Comparison table
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

        # Charts
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

        # Model info
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
        - Part taxonomy: MechCAD 10-class dataset
        - Operation rules: Machining Data Handbook (Metcut, 1980)
        - Tolerance standard: ISO 286-1

        **System Architecture**
        - 🤖 LLM: Meta Llama 3.1 8B via AWS Bedrock
        - 🗄️ Vector DB: ChromaDB (local, persistent)
        - 🔍 Embeddings: sentence-transformers/all-MiniLM-L6-v2
        - 🔗 Orchestration: LangChain-AWS
        """)
    with c2:
        st.markdown("""
        **Evaluation**
        - 20 unseen test parts (preliminary quick-test run; full 100-part
          held-out evaluation pending)
        - 5 metrics: Feature Recognition, Operation Accuracy,
          Sequence Correctness, Completeness, Machine Selection
        - Baseline: Rule-based CAPP (direct lookup)

        **Key Results** *(20-part preliminary run)*
        - ✅ Sequence Correctness: 100% (matches rule-based)
        - ✅ Operation Completeness: 99.17% (+2.51% vs baseline)
        - ✅ Machine Selection: 100%
        - ✅ 0/20 evaluation failures
        """)

    st.markdown("---")
    st.markdown("""
    ### Dataset Sources

    | Source | Used For | Link |
    |--------|----------|------|
    | FeatureNet (Zhang et al., 2018) | Feature vocabulary (24 classes) | [GitHub](https://github.com/madlabub/Machining-feature-dataset) |
    | MechCAD / BRT (2025) | Part type taxonomy (10 classes) | [arXiv](https://arxiv.org/abs/2504.07134) |
    | Machining Data Handbook (Metcut, 1980) | Operation rules, cutting params | [archive.org](https://archive.org/details/machiningdatahan0002unse) |
    | ISO 286-1 | Tolerance grades (H7 / h6 / H8 / IT9) | — |
    """)
