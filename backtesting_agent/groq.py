import os
from groq import Groq
from dotenv import load_dotenv
from backtesting_agent.prompts import GENERATE_STRATEGY_CODE_SYSTEM_MESSAGE, GENERATE_BACKTEST_CODE_SYSTEM_MESSAGE, GENERATE_BACKTEST_CODE_PROMPT_BACKTESTING, GENERATE_BACKTEST_CODE_PROMPT_SYNAPSE, GENERATE_JSON_OUTPUT_SYSTEM_MESSAGE

# Load API key from .env
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

# Configure Groq API
client = Groq(api_key=api_key)

def get_llm_response(prompt, system_instruction=None):
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": GENERATE_BACKTEST_CODE_SYSTEM_MESSAGE})
    messages.append({"role": "user", "content": GENERATE_BACKTEST_CODE_PROMPT_SYNAPSE.format(prompt)})
    
    chat_completion = client.chat.completions.create(
        messages=messages,
        model="qwen/qwen3-32b",
    )
    return chat_completion.choices[0].message.content



def get_llm_metadata(prompt):
    messages = []
    messages.append({"role": "user", "content": GENERATE_JSON_OUTPUT_SYSTEM_MESSAGE})
    
    chat_completion = client.chat.completions.create(
        messages=messages,
        model="qwen/qwen3-32b",
    )
    return chat_completion.choices[0].message.content

