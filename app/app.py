import streamlit as st
import os
import tempfile
import json
import pandas as pd
from PIL import Image
import pypneu
from pypneu.simulator import BatchSimulator
from pypneu.executor import StochasticPetriNetExecution
from pypneu.exporter import to_dot
from pypneu import PetriNetViewer, PetriNetStructure

# --- Page Config ---
st.set_page_config(layout="wide", page_title="pypneu web IDE")

# --- Custom Styling for Monotype Editor ---
st.markdown("""
    <style>
    /* Target the textarea inside the Streamlit component */
    div[data-baseweb="textarea"] textarea {
        font-family: 'Source Code Pro', 'Courier New', monospace !important;
        font-size: 14px !important;
        line-height: 1.5 !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("pypneu")

# --- Layout ---
left_col, right_col = st.columns([1, 1])

with left_col:
    st.subheader("Source")
    # Initial example code
    default_code = """ready.
ready -> #produce -> buffer.
buffer -> #path_a -> received_a.
buffer -> #path_b -> received_b.
received_a, received_b -> #reset -> ready."""

    pneu_code = st.text_area("Editor", value=default_code, height=400, label_visibility="collapsed")

    st.divider()

    # Bottom Buttons Row
    btn_col1, btn_col2, btn_col3 = st.columns(3)

    # --- Action Parameters ---
    with st.expander("Settings & Options"):
        n_runs = st.slider("Batch Runs", 10, 500, 100)
        max_steps = st.number_input("Max Steps per Run", 1, 100, 20)
        anim_steps = st.number_input("Animation Steps", 5, 30, 15)

# --- State Management ---
if 'net_data' not in st.session_state:
    st.session_state.net_data = None

# --- Action Logic ---
with right_col:
    st.subheader("Output")
    output_container = st.empty()

    # 1. PARSE / VISUALIZE STATIC
    if btn_col1.button("🔍 Parse & View", use_container_width=True):
        with tempfile.NamedTemporaryFile(suffix=".pneu", mode='w', delete=False) as f:
            f.write(pneu_code)
            tmp_path = f.name

        try:
            st.session_state.net_data = pypneu.compile_file(tmp_path)
            pn_struct = PetriNetStructure(**st.session_state.net_data)
            viewer = PetriNetViewer(pn_struct)

            # Create PNG in memory
            png_data = viewer.to_pydot_graph().create_png()
            st.image(png_data, caption="Petri Net Structure", use_container_width=True)
            st.success("Compilation Successful!")
        except Exception as e:
            st.error(f"Parse Error: {e}")
        finally:
            os.remove(tmp_path)

    # 2. RUN ANIMATION
    if btn_col2.button("🎬 Run & Animate", use_container_width=True):
        if st.session_state.net_data:
            with st.spinner("Generating Animation..."):
                # We reuse your generate_gif logic locally
                from pypneu.cli import generate_gif

                with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as tmp:
                    generate_gif(st.session_state.net_data, anim_steps, tmp.name)
                    st.image(tmp.name, caption="Simulation Playback")
                st.info("Animation captures one stochastic trace.")
        else:
            st.warning("Please Parse the net first.")

    # 3. ANALYZE (BATCH)
    if btn_col3.button("📊 Analyze Batch", use_container_width=True):
        if st.session_state.net_data:
            with st.spinner("Running Batch Simulation..."):
                simulator = BatchSimulator(StochasticPetriNetExecution, st.session_state.net_data)
                results = simulator.run_batch(n_runs=n_runs, iterations_per_run=max_steps)

                # Show Distribution
                st.write("### Final Marking Distribution")
                dist_data = [{"Marking": m, "Count": c} for m, c in results["marking_distribution"].items()]
                st.bar_chart(pd.DataFrame(dist_data).set_index("Marking"))

                # Show Compressed Traces
                st.write("### Path Probabilities")
                traces = results["json_data"]
                trace_summary = []
                for i, path in enumerate(traces["paths"]):
                    trace_summary.append({
                        "Path ID": f"Trace {i}",
                        "Sequence": " → ".join([str(x) for x in path]),
                        "Frequency": traces["counts"][i],
                        "Prob %": (traces["counts"][i] / n_runs) * 100
                    })
                st.table(pd.DataFrame(trace_summary))
        else:
            st.warning("Please Parse the net first.")