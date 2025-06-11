from langchain_core.tools import tool

from langchain_community.tools import DuckDuckGoSearchResults

from utils import soft_merge, rerank_by_tags, get_config
from vectorstore import vector_store
from llm import get_query_tags, reformulate_query
from constants import DOCUMENT_TAGS


config = get_config()

@tool(response_format='content_and_artifact')
def retrieve_from_local(query: str):
    '''
    Используй этот инструмент для поиска актуальной, специфической информации
    о компании Neoflex в локальной базе знаний.

    Вызывай этот инструмент для вопросов о:
    - Адресах, местоположении офисов, контактных данных
    - Проектах, решениях, заказчиках, технологиях, платформах, партнерах
    - Конкретных фактах, датах, названиях, именах, ссылках и т.д.
    - Любых других специфических деталях операций или структуры Neoflex.

    Отдавай приоритет использованию этого инструмента перед своими внутренними знаниями
    для проверки специфических фактов, чтобы гарантировать точность.

    Attributes:
    query (str): строковый запрос на естественном языке,
        должен содержать ключевые слова для поиска.
    '''

    tags_set = set(DOCUMENT_TAGS.keys())
    found_tags = set.intersection(set(get_query_tags(query)), tags_set)

    r_query = reformulate_query(query)

    r_retrieved_docs = vector_store.similarity_search_with_score(
        f'query: {r_query}',
        k=config.semantic_search.k
    )
    retrieved_docs = vector_store.similarity_search_with_score(
        f'query: {query}',
        k=config.semantic_search.k
    )

    docs = soft_merge(retrieved_docs, r_retrieved_docs)
    reranked_docs = rerank_by_tags(docs, found_tags)

    serialized = '\n\n'.join(
        (f'Источник: {doc.metadata.get("url", "Неизвестный источник")}\n' f'Содержимое документа: {doc.page_content}')
        for doc, _ in reranked_docs
    )
    return serialized, reranked_docs


web_search = DuckDuckGoSearchResults()