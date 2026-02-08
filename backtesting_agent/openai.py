import os
from openai import OpenAI  # Correct import
from dotenv import load_dotenv
from backtesting_agent.prompts import GENERATE_JSON_OUTPUT_SYSTEM_MESSAGE,GENERATE_STRATEGY_CODE_SYSTEM_MESSAGE, GENERATE_BACKTEST_CODE_SYSTEM_MESSAGE, GENERATE_BACKTEST_CODE_PROMPT_BACKTESTING, GENERATE_BACKTEST_CODE_PROMPT_MAIN
import pprint

# Load API key
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
client = OpenAI(api_key=api_key)



def get_llm_response(prompt, system_instruction=None):
    messages = []
    
    # Use provided system instruction or default
    if system_instruction is None:
        system_instruction = GENERATE_STRATEGY_CODE_SYSTEM_MESSAGE

    messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": GENERATE_BACKTEST_CODE_PROMPT_MAIN.format(prompt)})
    
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages
    )
    
    return response.choices[0].message.content


