


# from langchain.prompts import PromptTemplate
# from langchain_core.runnables import RunnableSequence
# from langchain_openai import ChatOpenAI  # ✅ Modern replacement

# from dotenv import load_dotenv
# import os

# # Load environment variables from .env
# load_dotenv()

# def load_groq_model() -> ChatOpenAI:
#     """
#     Load the Groq-hosted LLaMA model via OpenAI-compatible API.
#     """
#     return ChatOpenAI(
#         openai_api_key=os.getenv("OPENAI_API_KEY"),
#         openai_api_base=os.getenv("OPENAI_API_BASE"),
#         model_name=os.getenv("OPENAI_API_MODEL", "llama3-8b-8192"),
#         temperature=0.7,
#         max_tokens=512
#     )

# def create_agent(prompt_template: PromptTemplate, model=None) -> RunnableSequence:
#     """
#     Create an agent using LangChain's recommended Runnable pipeline style.
#     """
#     if model is None:
#         model = load_groq_model()
#     return prompt_template | model  # ✅ Runnable: Prompt → LLM


from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
from langchain_core.runnables.base import Runnable
import google.generativeai as genai
import os
import time
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

class GeminiAgent:
    def __init__(self, model_name="gemini-2.0-flash"):
        self.model_name = model_name
        self.gemini = genai.GenerativeModel(model_name)

    def call_gemini(self, prompt, retries=5, delay=41, temperature=0):
        for attempt in range(retries):
            try:
                response = self.gemini.generate_content(prompt, generation_config={"temperature": temperature})

                if not response.candidates:
                    print("No candidates returned. Skipping chunk.")
                    return ""

                if response.candidates[0].finish_reason == "RECITATION":
                    print("Chunk blocked due to recitation. Skipping.")
                    return ""

                if hasattr(response, "text"):
                    return response.text.strip()
                elif hasattr(response, "parts"):
                    return "".join([p.text for p in response.parts])
                else:
                    return str(response)

            except Exception as e:
                if "requires the response to contain a valid `Part`" in str(e) or "finish_reason" in str(e):
                    print("Chunk blocked by Gemini (recitation/copyright). Skipping.")
                    return ""
                else:
                    print(f"Gemini API call error: {e}. Retrying in {delay} seconds (Attempt {attempt + 1}/{retries})...")
                    time.sleep(delay)
                    delay *= 2

        print("All retries failed. Skipping this chunk.")
        return ""

def create_agent(prompt_template: PromptTemplate, temperature=0):
    """
    Create a callable agent that formats the prompt and calls Gemini.
    """
    gemini_agent = GeminiAgent()

    class GeminiLangChainAgent:
        def invoke(self, input_data):
            prompt = prompt_template.format(**input_data)
            return {"text": gemini_agent.call_gemini(prompt, temperature=temperature)}

    return GeminiLangChainAgent()
