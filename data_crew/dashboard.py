# dashboard_data_crew.py
import streamlit as st
import pandas as pd
import os
import json
from main import run_data_crew 
import re


st.set_page_config(
    page_title="Agentic Data Analysis",
    layout="wide",
)


MAIN_DATA_PATH = "/home/R4/Harshiv/BackTestData"



if 'result' not in st.session_state:
    st.session_state.result = None
if 'query' not in st.session_state:
    st.session_state.query = "Find the average LTQ for each hour of the day."
if 'selected_files' not in st.session_state:
    st.session_state.selected_files = []



@st.cache_data(ttl=600)
def scan_data_directory(root_path):
    """Scans the directory for all .txt files and returns their paths."""
    txt_files = []
    for root, _, files in os.walk(root_path):
        for file in files:
            if file.endswith(".txt"):
                full_path = os.path.join(root, file)
                display_path = os.path.relpath(full_path, root_path)
                txt_files.append((full_path, display_path))
    txt_files.sort(key=lambda x: x[1])
    return txt_files


def parse_markdown_dataframe(markdown_table):
    """
    Parses a markdown table string into a pandas DataFrame.
    """
    try:
        lines = markdown_table.strip().split('\n')
        lines = [line for line in lines if not re.match(r'^[\s|:-]+$', line.strip())]
        data = [[cell.strip() for cell in line.split('|') if cell.strip()] for line in lines]
        if len(data) < 2: return None
        header = data[0]
        rows = data[1:]
        df = pd.DataFrame(rows, columns=header)
        return df
    except Exception as e:
        print(f"Error parsing markdown table: {e}")
        return None


st.title("Agentic Financial Data Analysis")
st.markdown(f"**Data Directory:** `{MAIN_DATA_PATH}`")
st.markdown("---")


try:
    all_files = scan_data_directory(MAIN_DATA_PATH)
    full_path_list, display_path_list = zip(*all_files)
except Exception as e:
    st.error(f"Failed to scan data directory: {e}")
    st.stop()



st.subheader("1. Select Data File(s)")
selected_display_paths = st.multiselect(
    "Select files to analyze:",
    options=display_path_list,
    label_visibility="collapsed"
)

st.session_state.selected_files = [
    full_path for full_path, display_path in all_files 
    if display_path in selected_display_paths
]



st.subheader("2. Enter Your Query")
st.session_state.query = st.text_area(
    "Your Query (e.g., 'Plot the LTP' or 'Find the hourly average of LTQ'):",
    value=st.session_state.query,
    height=100,
)


run_button = st.button("Run Analysis")


st.markdown("---")
st.subheader("3. Agent Output")
log_container = st.container()
result_container = st.container()

if run_button:
    if not st.session_state.selected_files:
        st.error("Please select at least one data file.")
    elif not st.session_state.query:
        st.error("Please enter an analysis query.")
    else:
        st.session_state.result = None
        result_container.empty()
        
        with log_container:
            log_placeholder = st.empty()
            log_placeholder.markdown("`Initializing agents...`")
        
        with st.spinner("Agents are working... Writing code and executing..."):
            try:
                result = run_data_crew(
                    query=st.session_state.query,
                    selected_file_paths=st.session_state.selected_files 
                )
                st.session_state.result = result
                log_placeholder.empty()
            except Exception as e:
                st.session_state.result = {"status": "failed", "error": f"An error occurred in the agent crew: {str(e)}", "script_file": None}
                log_placeholder.error(f"An error occurred: {e}")


if st.session_state.result:
    result = st.session_state.result
    
    if result["status"] == "success":
        st.success(f"**Analysis Successful!*")
        df = pd.read_csv(result.get("df_path"))
        with result_container:
            st.dataframe(df)
        

    elif result["status"] == "failed":
        st.error(f"**Analysis Failed!**")
        with result_container:
            st.code(result.get("error", "An unknown error occurred."), language="bash")
            

    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.expander("View Full Execution Log"):
            st.code(result.get("log", "No log captured."), language="bash")
            
    with col2:
        with st.expander("View Generated Python Script"):
            if result.get("final_code"): 
                st.code(result["final_code"], language="python")
            else:
                st.info("Script was not generated or saved.")
                

elif not run_button:
    st.info("Select file(s) and enter a query to begin.")