# tools/code_execution_tool.py
from crewai.tools import BaseTool
import subprocess
import os

class CodeExecutionTool(BaseTool):
    name: str = "Code Execution & Verification Tool"
    description: str = "Executes a string of Python code in a subprocess and returns the stdout and stderr. Use this to verify that the generated backtesting script is runnable and free of syntax errors."

    def _run(self, python_code: str) -> str:
        """Executes the Python code and captures the output."""
        script_filename = "temp_strategy_crewai.py"
        with open(script_filename, "w", encoding="utf-8") as f:
            f.write(python_code)

        try:
            result = subprocess.run(
                ["python3", script_filename],
                capture_output=True,
                text=True,
                timeout=60 # Add a timeout to prevent infinite loops
            )

            if result.returncode != 0:
                return f"Execution failed with error:\n---\nSTDOUT:\n{result.stdout}\n---\nSTDERR:\n{result.stderr}\n---"

            return f"Execution successful. Final backtest output:\n---\n{result.stdout}\n---"

        except subprocess.TimeoutExpired:
            return "Execution failed: The script took too long to run and was terminated."
        except Exception as e:
            return f"An unexpected exception occurred during execution: {str(e)}"
        finally:
            if os.path.exists(script_filename):
                os.remove(script_filename)