import re

def extract_python_code(response_text):
    matches = re.findall(r"```python\s*([\s\S]*?)\s*```", response_text)
    
    if matches:
        return "\n".join(matches)

    return response_text