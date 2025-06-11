from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from utils import get_config


config = get_config()

# Создаем локальное векторное хранилище, к нему подключаем эмбеддинги E5
# (теперь от HuggingFace, ведь, как оказалось, Fastembeddings под капотом меняли E5 на другую модель).
# По идее, E5 должна хорошо подходить для смеси русского текста и английской терминологии,
# а еще показывает неплохие показатели.
embeddings = HuggingFaceEmbeddings(model_name=config.embeddings.model_name)

vector_store = Chroma(
    collection_name='documents',
    embedding_function=embeddings,
    persist_directory='./documents_chroma_db',
)