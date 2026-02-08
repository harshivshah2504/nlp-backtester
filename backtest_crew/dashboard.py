import streamlit as st
import json
import pandas as pd
import importlib
import main
importlib.reload(main)
from main import run_crew
import pickle
from bokeh.io import output_file, save
from bokeh.embed import file_html
from bokeh.resources import CDN
from bokeh.plotting import figure
import matplotlib.pyplot as plt

st.set_page_config(page_title="Strategy Generator", layout="wide")

st.title("Multi-Agent Backtesting Strategy Generator")



query = st.text_area(
    "Enter your trading strategy idea:",
    height=300
)



if st.button("Run Strategy Generator"):
    with st.spinner("Running multi-agent crew... please wait"):
        try:
            result = run_crew(query)
        except Exception as e:
            st.error(f"Execution failed: {e}")
            st.stop()



    st.markdown("---")
    st.header("Final Output")



    if isinstance(result, dict):
        stats_file = result.get("stats_file")
        fig_file = result.get("fig_file")
        if stats_file is not None:
            with open(stats_file, "rb") as f:
                    stats = pickle.load(f)
            st.subheader("Backtest Statistics")
            st.write(stats)
            trades_df = pd.DataFrame(stats['_trades'])
            for col in trades_df.columns:
                if pd.api.types.is_timedelta64_dtype(trades_df[col]):
                    trades_df[col] = trades_df[col].astype(str)
                elif trades_df[col].dtype == "object":
                    trades_df[col] = trades_df[col].astype(str)
            st.dataframe(trades_df, use_container_width=True)
    
        if fig_file is not None:
            st.subheader("Equity Curve & Trade Visualization")
            with open(fig_file, "r", encoding="utf-8") as f:
                html_content = f.read()
            st.components.v1.html(html_content, height=600, scrolling=True)


        if "final_code" in result:
            st.subheader("Generated Strategy Code")
            st.code(result["final_code"], language="python")

    else:
        st.text(result)

else:
    st.info("Enter a trading idea above and click Run Strategy Generator to start.")
