import subprocess, re, sys, os, uuid, threading, shutil
from pathlib import Path
from datetime import datetime

def run_code(code, index):
    code = re.sub(r"```python\s*([\s\S]*?)\s*```", r"\1", code)
    
    # Create a dedicated temp directory if it doesn't exist
    temp_dir = Path("./temp_executions")
    temp_dir.mkdir(exist_ok=True)
    
    # Create unique subdirectory for this execution using thread ID and random UUID
    thread_id = threading.get_ident()
    unique_id = uuid.uuid4().hex[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = temp_dir / f"run_{index}_{timestamp}_{thread_id}_{unique_id}"
    run_dir.mkdir(exist_ok=True)
    
    # Define file paths in the temp directory
    script_filename = run_dir / "temp_script.py"
    output_filename = run_dir / "output.txt"
    error_filename = run_dir / "error.txt"
    
    try:
        # Write the code to the script file
        with open(script_filename, "w", encoding="utf-8") as script_file:
            script_file.write(code)
            
        # Redirect output to files
        with open(output_filename, "w") as out_file, open(error_filename, "w") as err_file:
            result = subprocess.run([sys.executable, str(script_filename)], 
                                    stdout=out_file, 
                                    stderr=err_file, 
                                    text=True, 
                                    timeout=None)
                                    
        # Read outputs
        with open(output_filename, "r") as out_file:
            stdout = out_file.read().strip()
            print("Output:\n", stdout)
            
        with open(error_filename, "r") as err_file:
            stderr = err_file.read().strip()
            if stderr:
                print("Errors:\n", stderr)
            
    except Exception as e:
        print(f"Unexpected Error: {e}")
        
    finally:
        # Clean up - remove the entire run directory
        try:
            shutil.rmtree(run_dir)
            
            # If temp_dir is empty, remove it too
            if not any(temp_dir.iterdir()):
                shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Error cleaning up temporary files: {e}")
                    
    return code