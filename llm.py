import getpass
import os

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai.chat_models import ChatOpenAI

from utils import load_prompt, get_config


config = get_config()

if not os.environ.get('OPENROUTER_API_KEY'):
  os.environ['OPENROUTER_API_KEY'] = getpass.getpass('Enter API key for OpenRouter: ')

if not os.environ.get('OPENROUTER_BASE_URL'):
  os.environ['OPENROUTER_BASE_URL'] = 'https://openrouter.ai/api/v1'


# В качестве LLM выбрана gpt-4.1-nano.
# Дешевая, быстрая модель, поддерживающая тулзы - это важно.
llm = ChatOpenAI(
  openai_api_key=os.environ.get('OPENROUTER_API_KEY'),
  openai_api_base=os.environ.get('OPENROUTER_BASE_URL'),
  model_name=config.model.name,
  temperature=config.model.temperature
)


# Обращается к LLM, чтобы извлечь подходящие теги из пользовательского запроса.
def get_query_tags(user_query: str):
    prompt = load_prompt('prompts/tag-getter-prompt.txt')
    f_prompt = prompt.format(user_query=user_query)
    response = llm.invoke(f_prompt)

    tags = []
    try:
        res = response.content.strip()
        if res[0] == '[' and res[-1] == ']':
            tags = eval(response.content.strip())
    except:
        pass
    return tags


# Обращается к LLM, чтобы та переформулировала запрос.
def reformulate_query(user_query: str):
    user_query = user_query[:config.reformulate.max_length]

    prompt = [
        SystemMessage(content=(
            load_prompt('prompts/reformulation-prompt.txt')
        )),
        HumanMessage(content=user_query)
    ]
    response = llm.invoke(prompt)
    try:
        return response.content.strip() or user_query
    except:
        return user_query