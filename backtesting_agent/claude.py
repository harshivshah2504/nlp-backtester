import os
import anthropic
from dotenv import load_dotenv
from backtesting_agent.prompts import (
    GENERATE_STRATEGY_CODE_SYSTEM_MESSAGE, 
    GENERATE_BACKTEST_CODE_SYSTEM_MESSAGE, 
    GENERATE_BACKTEST_CODE_PROMPT_BACKTESTING, 
    GENERATE_BACKTEST_CODE_PROMPT_SYNAPSE
)

# Load API key
load_dotenv()
api_key = os.getenv("CLAUDE_API_KEY")

# Initialize Claude client
client = anthropic.Anthropic(api_key=api_key)

def get_llm_response(prompt, system_instruction=None):
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": GENERATE_BACKTEST_CODE_SYSTEM_MESSAGE})
    messages.append({"role": "user", "content": GENERATE_BACKTEST_CODE_PROMPT_BACKTESTING.format(prompt)})
    
    response = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=4096,
        messages=messages
    )
    
    return response.content[0].text