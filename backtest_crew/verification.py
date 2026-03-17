from backtesting_agent.extract_python_code import extract_python_code
from runner import run_code
import contextlib
import io
import os
import re
import pickle
import time
import tempfile
from pathlib import Path

# Import the multi-model LLM manager
from llm_manager import generate_with_fallback, TaskType, get_manager

# System prompt optimized for error fixing
ERROR_FIX_SYSTEM_PROMPT = """You are an expert Python debugger specializing in quantitative trading code.
Your task is to fix errors in backtesting strategy code.

Rules:
1. Return ONLY the corrected Python code, no explanations
2. Do not add markdown formatting or code blocks
3. Keep all existing functionality intact
4. Fix only the error mentioned, don't refactor unrelated code
5. Ensure the code is syntactically correct and runnable"""


def checker(python_code, ticker, start_date, end_date=None, MAX_RETRIES=10):
    attempt = 0
    strategy_id = 1
    stdout_output = ""
    
    # Get the LLM manager for tracking usage
    llm_manager = get_manager(verbose=True)

    # Use a writable temp directory for local runs and hosted platforms like Render.
    temp_dir = Path(tempfile.gettempdir()) / "backtest_crew"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Unique filenames per run
    timestamp = int(time.time())
    bt_file = str(temp_dir / f"temp_bt_{timestamp}.html")
    stats_file = str(temp_dir / f"temp_stats_{timestamp}.pkl")

    # Format end_date for the main block (None becomes 'None' string for Python code)
    end_date_str = f'"{end_date}"' if end_date else 'None'

    # Main block for execution
    main_block = f'''
if __name__ == '__main__':
    start_date = "{start_date}"
    end_date = {end_date_str}
    try:
        bt = MultiBacktest(Strategy, cash=100000, commission=0.00005, margin=1/100, fail_fast=False, bt_file = r"{bt_file}", stats_file = r"{stats_file}")
        ticker_name = f"{ticker}"
        stats = bt.backtest_stock(ticker_name, start_date, end_date)
        print("--- Backtest Statistics ---")
        print(stats)
        print("-------------------------")
    except NameError as e:
        print(f"Execution Error: A required class (like MultiBacktest or Strategy) was not defined by the LLM. Details: {{e}}")
    except Exception as e:
        print(f"An unexpected error occurred during final backtest execution: {{e}}")
'''

    python_code = extract_python_code(python_code)
    python_code = re.sub(r'if __name__ == .__main__.:.*', '', python_code, flags=re.DOTALL).strip()
    python_code = python_code + "\n\n" + main_block

    python_code = re.sub(r'def\s+add_buy_trade\s*\(.*?\):.*?(\n\s+[^\n]*)*', '', python_code, flags=re.DOTALL)
    python_code = re.sub(r'def\s+add_sell_trade\s*\(.*?\):.*?(\n\s+[^\n]*)*', '', python_code, flags=re.DOTALL)

    error_message = ""

    while attempt < MAX_RETRIES:
        stdout_output, stderr_output = run_code(python_code)
        current_error = ""
        if "Traceback (most recent call last):" in stderr_output or "Traceback (most recent call last):" in stdout_output or "An unexpected error occurred" in stderr_output or "An unexpected error occurred" in stdout_output :
            current_error = stderr_output if "Traceback" in stderr_output else stdout_output

        if not current_error:
            print(f"Strategy {strategy_id} executed successfully on attempt {attempt + 1}.")
            
            # Print LLM usage stats
            stats = llm_manager.get_stats()
            print(f"\n[LLM Stats] Total tokens: {stats['total_tokens']}, Estimated cost: ${stats['total_cost']:.4f}")
            
            return {
                "status": "success",
                "strategy_id": strategy_id,
                "output": stdout_output,
                "final_code": python_code,
                "stats_file": stats_file,
                "fig_file": bt_file,
                "attempts_taken": attempt + 1,
                "llm_stats": stats
            }

        
        attempt += 1
        error_message = current_error
        print(f"Error in Strategy {strategy_id}, Attempt {attempt}: \n{error_message}")

        if attempt >= MAX_RETRIES:
            break

        # Use the multi-model LLM manager with fallback for error fixing
        correction_prompt = f"""Fix the following Python strategy code error:

**Error Message:**
{error_message}

**Code:**
```python
{python_code}
```

Return only the corrected and complete Python code."""

        print("\n--- Sending request for code correction (using multi-model fallback) ---")
        
        try:
            # Use ERROR_FIXING task type which uses cost-effective models with fallback
            corrected_response, metadata = llm_manager.generate(
                task_type=TaskType.ERROR_FIXING,
                prompt=correction_prompt,
                system_prompt=ERROR_FIX_SYSTEM_PROMPT,
            )
            
            print(f"[LLM] Used {metadata['provider']}/{metadata['model']} - {metadata['total_tokens']} tokens")
            
            python_code = extract_python_code(corrected_response)
            python_code = re.sub(r'if __name__ == .__main__.:.*', '', python_code, flags=re.DOTALL).strip()
            python_code = python_code + "\n\n" + main_block
            print(f"\nReceived Corrected Code (Attempt {attempt+1}):\n")
            
        except Exception as e:
            print(f"[LLM] Error during correction: {e}")
            # Continue with unchanged code to exhaust retries
            continue

    # Print final LLM usage stats
    stats = llm_manager.get_stats()
    print(f"\n[LLM Stats] Total tokens: {stats['total_tokens']}, Estimated cost: ${stats['total_cost']:.4f}")

    return {
        "status": "failed",
        "strategy_id": strategy_id,
        "error": error_message,
        "final_code": python_code,
        "attempts_taken": attempt,
        "llm_stats": stats
    }
