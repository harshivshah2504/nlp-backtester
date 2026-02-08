import google.generativeai as genai
from backtesting_agent.prompts import GENERATE_JSON_OUTPUT_SYSTEM_MESSAGE,GENERATE_STRATEGY_CODE_SYSTEM_MESSAGE, GENERATE_BACKTEST_CODE_SYSTEM_MESSAGE, GENERATE_BACKTEST_CODE_PROMPT_BACKTESTING, GENERATE_BACKTEST_CODE_PROMPT_MAIN
import pprint

genai.configure(api_key="AIzaSyBaeoOHkRKRAbT806u8ZGeJ1bCabAamMCI")
# for model in genai.list_models():
#         pprint.pprint(model)


def get_llm_response(prompt):
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=GENERATE_STRATEGY_CODE_SYSTEM_MESSAGE
    )
    response = model.generate_content([GENERATE_BACKTEST_CODE_PROMPT_MAIN.format(prompt)])
    return response.text


def get_llm_metadata(prompt):
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=GENERATE_JSON_OUTPUT_SYSTEM_MESSAGE
    )
    response = model.generate_content(prompt)
    return response.text


