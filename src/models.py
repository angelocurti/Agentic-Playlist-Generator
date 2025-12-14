from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_perplexity import ChatPerplexity
from src.config import GOOGLE_API_KEY, PPLX_API_KEY

ORCH_MODEL = "gemini-2.5-flash"
PPLX_MODEL = "sonar"        


# Replace Google models with Anthropic equivalents
llm_orch = ChatGoogleGenerativeAI(model=ORCH_MODEL, api_key=GOOGLE_API_KEY)
llm_input = ChatPerplexity(temperature=0, model="sonar")
llm_search = ChatPerplexity(temperature=0.4, model="sonar")
llm_output = ChatGoogleGenerativeAI(model=ORCH_MODEL, api_key=GOOGLE_API_KEY)