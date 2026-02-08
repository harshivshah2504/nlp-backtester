# verification_data_crew.py
import os
import re
import time
import subprocess
import sys
from backtesting_agent.openai import get_llm_response  
from backtesting_agent.extract_python_code import extract_python_code  


def run_code(python_code: str) -> tuple[str, str]:
    """Executes Python code in a subprocess and captures stdout/stderr."""
    try:        
        temp_script_path = "/home/R4/Harshiv/temp_script.py"
        with open(temp_script_path, 'w') as f:
            f.write(python_code)

        process = subprocess.run(
            [sys.executable, temp_script_path],
            capture_output=True,
            text=True,
            timeout=120,
            encoding='utf-8'
        )
        return process.stdout, process.stderr
    except subprocess.TimeoutExpired as e:
        return e.stdout or "", f"TimeoutError: Code execution exceeded 120 seconds.\n{e.stderr or ''}"
    except Exception as e:
        return "", f"RunnerError: Failed to execute code.\n{str(e)}"


def checker(python_code: str, selected_file_paths: list, MAX_RETRIES=10):
    attempt = 0
    stdout_output = ""
    temp_dir = "/home/R4/Harshiv/temp" 
    os.makedirs(temp_dir, exist_ok=True)

    timestamp = int(time.time())
    df_path = os.path.join(temp_dir, f"df_{timestamp}.csv")
    main_block = f'''
if __name__ == '__main__':
    try:
        # Define the plot file path for the script
        df_path = r"{df_path}"
        
        # --- FIX 4: Pass variables as correct types ---
        file_paths_arg = {selected_file_paths}

        # Call the agent-generated function
        df = run_analysis(
            file_paths_arg,
            df_path
        )
        print(df)
        print("--- EXECUTION SUCCESSFUL ---")

    except Exception as e:
        import traceback
        print(f"--- EXECUTION FAILED ---")
        print(traceback.format_exc())
'''

    python_code = re.sub(r'if __name__ == .__main__.:.*', '', python_code, flags=re.DOTALL).strip()
    python_code = python_code + "\n\n" + main_block
    error_message = ""

    while attempt < MAX_RETRIES:
        print(f"\n--- Verification Attempt {attempt + 1}/{MAX_RETRIES} ---")
        print(python_code)
        stdout_output, stderr_output = run_code(python_code)
        
        full_log = f"--- STDOUT ---\n{stdout_output}\n--- STDERR ---\n{stderr_output}"

        current_error = ""
        if "Traceback (most recent call last):" in stderr_output or "Traceback (most recent call last):" in stdout_output or "An unexpected error occurred" in stderr_output or "An unexpected error occurred" in stdout_output :
            current_error = stderr_output if "Traceback" in stderr_output else stdout_output


        if not current_error:
            print(f"Script executed successfully on attempt {attempt + 1}.")
            print(stderr_output)

            return {
                "status": "success",
                "log": full_log,
                "final_code": python_code,
                "df_path": df_path,
                "attempts_taken": attempt + 1
            }

        attempt += 1
        error_message = current_error
        print(f"Error encountered on Attempt {attempt}:\n{error_message}")

        if attempt >= MAX_RETRIES:
            print("Max retries reached. Failing.")
            break

        correction_prompt = f"""
        The following Python data analysis script has an error.
        
        **Rules:**
        1. The script MUST contain a function `run_analysis(plot_output_file='plot.png')`.
        2. All imports must be at the top.
        3. Do NOT include an `if __name__ == "__main__":` block.
        
        **Full Script (Code only, without main block):**
        ```python
        {python_code}
        ```
        
        **Error Message:**
        ```
        {error_message}
        ```
        
        Please fix the error in the script (imports and the `run_analysis` function).
        Return **only** the corrected, complete Python code block.
        """
        
        print("\n--- Sending request for code correction ---")
        corrected_response = get_llm_response(correction_prompt)
        

        python_code = extract_python_code(corrected_response) 
        

        python_code = python_code + "\n\n" + main_block
        print(f"\nReceived Corrected Code. Retrying...")


    return {
        "status": "failed",
        "error": error_message,
        "final_code": python_code,
        "attempts_taken": attempt,
        "log": full_log,
    }