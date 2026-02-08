import os
from crewai import Agent, Task, Crew, Process
from crewai import LLM
from dotenv import load_dotenv
from backtesting_agent.prompts import DATA_ANALYSIS_PROMPT
from verification import checker

load_dotenv()
llm = LLM(
    model="gpt-4.1-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
)

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)
coder_agent = Agent(
  role='Quantitative Data Scientist',
  goal='Write a complete, runnable Python script to perform analysis on a given list of data files based on a user query.',
  backstory='You are a senior data scientist. You are a master of pandas and matplotlib. You are given file paths and a natural language query, and you write the code to execute it. You never write explanations, only code.',
  llm=llm,
  verbose=True,
  allow_delegation=False
)

def run_data_crew(query: str, selected_file_paths: list) -> dict:
    """
    Runs the data analysis crew with pre-selected file paths and a natural language query.
    """
    print("Starting the Data Analysis Agentic Crew...")
    data_fields = "Ticker,Date,Time,LTP,BuyPrice,BuyQty,SellPrice,SellQty,LTQ,OpenInterest"
    print("\n--- Building Coder Task ---")


    coding_task = Task(
        description=DATA_ANALYSIS_PROMPT.format(query=query, filepaths=selected_file_paths),
        expected_output="A single Python code block containing all imports and the `run_analysis` function.",
        agent=coder_agent
    )
    
    print("Running Coder Task...")
    coding_crew = Crew(
        agents=[coder_agent],
        tasks=[coding_task],
        process=Process.sequential,
        verbose=True
    )
    generated_code = coding_crew.kickoff().raw

    if "```python" in generated_code:
        generated_code = generated_code.split("```python")[1].split("```")[0]
    generated_code = generated_code.strip()

    print("\n--- Handing code to Verification Checker ---")
    check_result = checker(
        python_code=generated_code,
        selected_file_paths=selected_file_paths
    )
    return check_result