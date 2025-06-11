from typing_extensions import List

from langchain_core.documents import Document
from langchain_core.messages import SystemMessage

from langgraph.graph import MessagesState, StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver

from tools import retrieve_from_local, web_search
from utils import load_prompt, get_config
from llm import llm


config = get_config()


class State(MessagesState):
    context: List[Document]


# Роут на ретривер либо генерация прямого ответа
def query_or_respond(state: MessagesState):
    prompt = [SystemMessage(content=load_prompt('prompts/qr-prompt.txt'))] + state['messages']
    llm_with_tools = llm.bind_tools([retrieve_from_local, web_search])
    response = llm_with_tools.invoke(prompt)
    return {'messages': [response]}


tools = ToolNode([retrieve_from_local, web_search])


# Гененирует итоговый ответ по результатам обращения к тулзам
def generate(state: MessagesState):
    recent_tool_msgs = []
    for message in reversed(state['messages']):
        if message.type == 'tool':
            recent_tool_msgs.append(message)
        else:
            break

    tool_msgs = recent_tool_msgs[::-1]

    docs_content = '\n\n'.join(
        doc.page_content
        for tool_msg in tool_msgs
        if tool_msg.artifact
        for doc, _ in tool_msg.artifact
    )
    if not docs_content:
        docs_content = 'Контекст отсутствует'
    system_message_content = (
        f"{load_prompt('prompts/generate-prompt.txt')}"
        f'{docs_content}'
    )
    conversation_msgs = [
        message
        for message in state['messages']
        if message.type in ('human', 'system')
        or (message.type == 'ai' and not message.tool_calls)
    ]
    prompt = [SystemMessage(system_message_content)] + conversation_msgs
    # may be a good idea to add prefixes to previous msgs or some introduction line

    response = llm.invoke(prompt)
    context = []

    for tool_msg in tool_msgs:
        if tool_msg.artifact is not None:
            context.extend(tool_msg.artifact)

    return {'messages': [response], 'context': context}


graph_builder = StateGraph(State)

# Добавляем ноды в граф
graph_builder.add_node(query_or_respond)
graph_builder.add_node(tools)
graph_builder.add_node(generate)

# Добавляем роут на ретривер
graph_builder.set_entry_point('query_or_respond')
graph_builder.add_conditional_edges(
    'query_or_respond',
    tools_condition,
    {END: END, 'tools': 'tools'}
)
graph_builder.add_edge('tools', 'generate')
graph_builder.add_edge('generate', END)

# Добавляем чекпоинтер, чтобы хранить MessagesState
memory = MemorySaver()
graph = graph_builder.compile(checkpointer=memory)

# Игрушечный конфиг
config = {'configurable': {'thread_id': 'abc123'}}


def process_input_message(session_id: str, input_message: str):
    '''
    Обрабатывает пойманное на API сообщение.

    Args:
      session_id: id сессии.
      input_message: сообщение, передающееся в граф

    Returns:
      ответ модели, источники, id сессии. Согласуется с pydantic-моделью ответа.
    '''

    response = graph.invoke(
        {'messages': [{'role': 'user', 'content': input_message}], 'context': []},
        stream_mode='values',
        config=config
    )

    # Парсим ответ от модельки
    src = []
    if response.get('context') and len(response['context']) > 0:
        for doc in response['context']:
            if isinstance(doc, dict):
                src.append({
                    'source': doc['link'],
                    'snippet': doc['snippet']
                })
            if isinstance(doc, tuple):
                src.append({
                    'source': doc[0].metadata.get('source', 'unknown'),
                    'snippet': (f'score: {doc[1]} ' + doc[0].page_content[:150] + '...')\
                        .encode('utf-8', errors='ignore').decode('utf-8')
                    # добавил скор в вывод для наглядности
                })
            else: src.append({
                'source': 'unknown',
                'snippet': f'Были получены неожиданные результаты поиска: {type(doc)}'
                })

    return {
        'answer': response['messages'][-1].content
        if response.get('messages') else "Ответ не получен.",
        'source_documents': src,
        'session_id': session_id
    }