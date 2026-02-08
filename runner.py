from backtesting_agent.gemini import get_llm_response,get_llm_metadata
from backtesting_agent.extract_python_code import extract_python_code
from backtesting_agent.extract_classes import extract_classes
import json, os, re, sys
import subprocess
import io

RESULTS_DIR = "strategies"
OUTPUT_FILE = os.path.join(RESULTS_DIR, "strategies.json")
os.makedirs(RESULTS_DIR, exist_ok=True)

MAX_RETRIES = 100
results = {}

def run_code(code):
    """Executes the provided Python code string in a subprocess."""
    code = re.sub(r"```python\s*([\s\S]*?)\s*```", r"\1", code)
    script_filename = "temp_script.py"
    with open(script_filename, "w", encoding="utf-8") as script_file:
        script_file.write(code)
    try:
        result = subprocess.run(["python3", script_filename], capture_output=True, text=True, timeout=180)
        print("Output:\n", result.stdout.strip())
        print("Errors:\n", result.stderr.strip() if result.stderr else "No errors.")
    except subprocess.TimeoutExpired:
        print("Error: The script took too long to execute and was terminated.")
    except Exception as e:
        print(f"Unexpected Error: {e}")

    return result.stdout.strip(), result.stderr.strip() if result.stderr else ""

def extract_metadata_from_query(query: str):
    """
    Uses an LLM to extract the ticker and start date from the NLP query.
    """
    print("--- Extracting Metadata from Query ---")
    metadata_prompt = f"""
    Analyze the following user query and extract the stock ticker and a start date.
    The start date should be in 'YYYYMMDD' format. If only a year is provided, default to the first day of that year.
    If a ticker is not found, use "GOOG" as the default.
    If a start date is not found, use "2022-01-01" as the default.
    Please respond with ONLY a JSON object in the format: {{"ticker": "...", "start_date": "..."}}

    Query: "{query}"
    """
    response = get_llm_metadata(metadata_prompt)
    json_str = response.strip().replace("```json", "").replace("```", "")
    
    try:
        metadata = json.loads(json_str)
        ticker = metadata.get('ticker', 'GOOG').upper()
        start_date = metadata.get('start_date', '20250701')
        print(f"Extracted Ticker: {ticker}, Start Date: {start_date}")
        return ticker, start_date
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Could not parse metadata from LLM response: '{json_str}'. Using defaults. Error: {e}")
        return "GOOG", "20250701"

def process_nlp_query(query: str, strategy_id: str, ticker: str, start_date: str):
    """
    Contains the main loop logic to generate, validate, and correct backtesting code.
    """
    print("=" * 100)
    print(f"\nProcessing new Strategy for Ticker: {ticker}, Start Date: {start_date}")
    
    initial_prompt = f"""
    {query}
    Always name the strategy class as Strategy.
    """
    

    llm_response = get_llm_response(initial_prompt)
    python_code = extract_python_code(llm_response)
    print(f"Initial Generated Code:\n{python_code}")
    print("\n--- Finalizing and injecting the main execution block ---")

    # Define the standardized main block
    main_block = f'''
if __name__ == '__main__':
    # These variables are injected from the main script
    start_date = "{start_date}"
    
    # Assuming the LLM generated MultiBacktest and Strategy classes
    try:
        bt = MultiBacktest(Strategy, cash=100000, commission=0.00005, margin=1/100, fail_fast=False)
        ticker_name = f"{ticker}"
        stats = bt.backtest_stock(ticker_name, start_date)
        print("--- Backtest Statistics ---")
        print(stats)
        print("-------------------------")
    except NameError as e:
        print(f"Execution Error: A required class (like MultiBacktest or Strategy) was not defined by the LLM. Details: {{e}}")
    except Exception as e:
        print(f"An unexpected error occurred during final backtest execution: {{e}}")
'''

    python_code = re.sub(r'if __name__ == .__main__.:.*', '', python_code, flags=re.DOTALL).strip()
    python_code = python_code + "\n\n" + main_block
    print(f"Final Code with Injected Main:\n{python_code}")
    
    attempt = 0
    stdout_output = ""
    error_message = ""
    
    while attempt < MAX_RETRIES:
        stdout_output, stderr_output = run_code(python_code)
        
        current_error = ""
        if "Traceback (most recent call last):" in stderr_output or "Traceback (most recent call last):" in stdout_output or "An unexpected error occurred" in stderr_output or "An unexpected error occurred" in stdout_output :
            current_error = stderr_output if "Traceback" in stderr_output else stdout_output

        if not current_error:
            print(f"Strategy {strategy_id} executed successfully on attempt {attempt + 1}.")
            error_message = ""
            break
        
        attempt += 1
        error_message = current_error
        print(f"Error in Strategy {strategy_id}, Attempt {attempt}: \n{error_message}")

        if attempt >= MAX_RETRIES:
            break

        correction_prompt = f"""
        The following Python strategy code has an error:
        **Code:**
        ```python
        {python_code}
        ```
        **Error Message:**
        {error_message}
        Please fix the error and return only the corrected and complete Python code and do not repeat the earlier error in any of the code.
        """
        print("\n--- Sending request for code correction ---")
        corrected_response = get_llm_response(correction_prompt)
        python_code = extract_python_code(corrected_response)
        python_code = re.sub(r'if __name__ == .__main__.:.*', '', python_code, flags=re.DOTALL).strip()
        python_code = python_code + "\n\n" + main_block
        print(f"\nReceived Corrected Code (Attempt {attempt+1}):\n")


    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)
    print(f"Progress saved in '{OUTPUT_FILE}'.")


if __name__ == "__main__":
    nlp_query = '''
    Create a simplified yet slightly permissive multi-factor algorithmic trading strategy for Microsoft (MSFT), starting from July 1st, 2025.  
    The goal is to allow more frequent trades by relaxing trend, momentum, and volatility filters.  

    Core Components:

    1. **Trend Detection:**
    - Use SuperTrend (ATR=14, Multiplier=2.5) to define bullish/bearish regimes.
    - Confirm regime with EMA(100) slope (bullish if rising or flat, bearish if falling or flat).

    2. **Momentum Confirmation:**
    - **Buy:** SuperTrend bullish, EMA(20) > EMA(50), RSI(14) > 45, and MACD histogram positive or turning positive.
    - **Sell:** SuperTrend bearish, EMA(20) < EMA(50), RSI(14) < 55, and MACD histogram negative or turning negative.

    3. **Volatility Filter:**
    - Trade only if ATR(14) > 0.8 * SMA(ATR,100).
    '''

    ticker, start_date = extract_metadata_from_query(nlp_query)
    strategy_name = f"{ticker.replace('.', '_')}_{start_date}" 
    
    process_nlp_query(
        query=nlp_query, 
        strategy_id=strategy_name,
        ticker=ticker,
        start_date=start_date
    )

    print("\nBacktesting process completed.")