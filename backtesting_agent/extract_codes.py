import os
import re
import json


def clean_english_text(text):
    """
        Removes non-English characters except numerals while keeping structure.
    """

    return re.sub(r"[^\x00-\x7F]+", " ", text) 


def extract_pinescript_from_md(md_file):
    """
        Extracts strategy key, code, and English content from an MD file.
    """

    with open(md_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract strategy key from URL
    match = re.search(r"https://www\.fmz\.com/strategy/(\d+)", content)
    strategy_key = match.group(1) if match else None

    # Extract code blocks
    code_blocks = re.findall(r"```(.*?)\n```", content, re.DOTALL)
    code_text = "\n".join(code_blocks) if code_blocks else None

    # Remove code blocks before cleaning English content
    cleaned_content = re.sub(r"```.*?\n```", "", content, flags=re.DOTALL)

    # Keep only English text & numbers
    english_content = clean_english_text(cleaned_content).strip()
    assert len(english_content) > 20

    return strategy_key, code_text, english_content


def process_strategies_folder(folder_path):
    """
        Extracts and saves PineScript code from all markdown files in a folder.
    """

    extracted_strategies = {}
    print(len(os.listdir(folder_path)))
    for filename in os.listdir(folder_path):
        if filename.endswith(".md") and filename != 'README.md':
            file_path = os.path.join(folder_path, filename)
            strategy_key, extracted_code, eng_content = extract_pinescript_from_md(file_path)

            if extracted_code:
                extracted_strategies[strategy_key] = {'code': extracted_code, 'description': eng_content}
                # print(f"Extracted code from {filename}")
            else:
                print(f"Not Extracted code from {filename}")

    return extracted_strategies

# Folder path where Markdown files are stored
strategies_folder = "strategies"

# Extract all strategies
strategies_data = process_strategies_folder(strategies_folder)
# print(strategies_data.keys())

# Save extracted strategies as a JSON file for later use
with open("extracted_strategies.json", "w", encoding="utf-8") as f:
    json.dump(strategies_data, f, ensure_ascii=False, indent=4)

print("Extraction complete. Data saved to extracted_strategies.json")
