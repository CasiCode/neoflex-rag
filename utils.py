import yaml
from box import Box


# Загрузчик конфига из yaml файла в объект
def get_config():
    with open('config.yaml', 'r') as f:
        config_dict = yaml.safe_load(f)
    return Box(config_dict)

config = get_config()


def load_prompt(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# Больше не используется в связи с переходом на ChromaDB, у которой другая скор-система
def normalize_similarity_score(scored_docs, lo, hi):
    '''
    Нормализует скоры семантического поиска на интервал [0, 1].
    Это сильно удобнее, чем компактный интервал [0.7, 1], в котором по умолчанию лежат скоры для E5

    Args:
      scored_docs: список пар документ-скор.
      lo: минимум скора для модели эмбеддингов.
      hi: максимум скора для модели эмбеддингов.

    Returns:
      Список документов с нормализованными скорами.
    '''

    result = [
        (doc, (score - lo) / (hi - lo))
        for doc, score in scored_docs
    ]
    return result


def soft_merge(lhs_docs, rhs_docs):
    '''
    "Мягко" объединяет два спика документов:
    Удаляет все документы, у которых скор хуже среднего, соединяет списки вместе и
    сортирует.
    Если какие-то документы окажутся настолько релевантными, что перетянут в свою сторону средний скор,
    то функция может вернуть меньше, чем K документов. Это поведение ожидаемо - идея в том,
    что вылетевшие документы в таком случае не будут мешать модели работать с самыми релевантыми.

    Args:
      lhs_docs: первый список документов.
      rhs_docs: второй список документов.

    Returns:
      K лучших документов, где K - длина наибольшего списка.
    '''

    res_len = max(len(lhs_docs), len(rhs_docs))


    # lhs_docs = normalize_similarity_score(
    #     lhs_docs, config.embeddings.score_lo, config.embeddings.score_hi)
    # rhs_docs = normalize_similarity_score(
    #     rhs_docs, config.embeddings.score_lo, config.embeddings.score_hi)


    lhs_mean = sum([score for _, score in lhs_docs]) / len(lhs_docs) if lhs_docs else 0
    rhs_mean = sum([score for _, score in rhs_docs]) / len(rhs_docs) if rhs_docs else 0
    lhs_docs = [(doc, score) for doc, score in lhs_docs if score <= lhs_mean]
    rhs_docs = [(doc, score) for doc, score in rhs_docs if score <= rhs_mean]

    docs = sorted(lhs_docs+rhs_docs, key=lambda x: x[1], reverse=False) # Меньше скор - лучше
    unique_docs = {doc.page_content: (doc, score) for doc, score in docs}.values()
    unique_docs = list(unique_docs)

    return unique_docs[:res_len]

def rerank_by_tags(
    docs, target_tags, boost=config.rerank.boost,
    filter_irrelevant=False, threshold=config.rerank.threshold
):
    '''
    Принимает на вход список документов, сравнивает их теги с целевыми
    и подтягивает скор докуметов в зависимости от количества совпадений.
    При filter_irrelevant = True отсекает явный мусор.

    Args:
      docs: список документов.
      target_tags: искомые теги.
      boost: увеличение сходства за каждое совпадение.
      filter_irrelevant: флаг фильтрации документов.
      threshold: порог фильтрации.

    Returns:
      отсортированный по скорам массив документов.

    Raises:
      ConnectionError: If no available port is found.
    '''

    reranked = []

    if not target_tags:
        reranked = docs.sort(key=lambda x: x[1], reverse=False)
    else:
        try:
            target = {t.lower() for t in target_tags if isinstance(t, str)}
        except:
            target = set([])
        for doc, score in docs:
            doc_tags = doc.metadata.get('tags', '')
            doc_tags_lo = doc_tags.lower()
            tags = set(doc_tags_lo.split())

            matches = len(target & tags)
            adjusted_score = max(0.0, score - boost * matches)
            reranked.append((doc, adjusted_score))

    #reranked_normalized = normalize_similarity_score(
    #    reranked, config.embeddings.score_lo, config.embeddings.score_hi)
    reranked = reranked.sort(key=lambda x: x[1], reverse=False)

    if filter_irrelevant:
        reranked = [
            (doc, score)
            for doc, score in reranked if score < threshold
            ]

    return reranked