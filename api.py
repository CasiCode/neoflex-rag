from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


app = FastAPI()


class Question(BaseModel):
    session_id: str
    question: str


class SourceDocument(BaseModel):
    source: str
    snippet: str


class Answer(BaseModel):
    answer: str
    source_documents: list[SourceDocument]
    session_id: str


process_input_message_func = None

def set_process_function(func):
    global process_input_message_func
    process_input_message_func = func


@app.post('/ask', response_model=Answer)
def ask_question(q: Question):
    if process_input_message_func is None:
        raise HTTPException(status_code=503, detail="Server cannot process requests")

    try:
        response = process_input_message_func(q.session_id, q.question)
    except:
        raise HTTPException(status_code=503, detail="Server cannot process requests")
        
    return Answer(
        answer=response['answer'],
        source_documents=response['source_documents'],
        session_id=response['session_id']
    )