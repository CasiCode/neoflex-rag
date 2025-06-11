from typing import Callable, Optional

from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from graph import process_input_message


# Исключение на стороне FastAPI
class LocalAPIException(Exception):
    def __init__(self, details: str):
        self.status_code = 503
        self.details = details


# Исключение на стороне OpenAI
class ExternalAPIException(Exception):
    def __init__(self, details: str):
        self.status_code = 421
        self.details = details


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


# Обработчик запросов
# По сути, обертка над _process_func, обрабатывающая исключения
class RequestHandler:
    def __init__(self):
        self._process_func: Optional[Callable] = None
    
    def set_process_function(self, func: Callable):
        if not callable(func):
            raise ValueError('Process function must be callable')
        self._process_func = func
    
    def process_request(self, session_id: str, question: str):
        if self._process_func is None:
            raise LocalAPIException(details='No process function registered on server.')
        
        try:
            response = self._process_func(session_id, question)
            required_keys = {'answer', 'source_documents', 'session_id'}
            if not all(key in response for key in required_keys):
                raise ExternalAPIException(details='Bad response format.')
            return response
        except Exception as e:
            raise ExternalAPIException(f'Unexpected error: {str(e)}')
        

app = FastAPI()
request_handler = RequestHandler()
request_handler.set_process_function(process_input_message)

def get_handler():
    return request_handler

@app.exception_handler(LocalAPIException)
def local_api_exception_handler(request: Request, exc: LocalAPIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={'message': f'Oops! Local API did something... {exc.details}'}
    )

@app.exception_handler(ExternalAPIException)
def external_api_exception_handler(request: Request, exc: ExternalAPIException):
    status_code = exc.status_code
    return JSONResponse(
        status_code=status_code,
        content={'message': f'Oops! External API did something... {exc.details}'}
    )

@app.post('/ask', response_model=Answer)
def ask_question(q: Question, handler: RequestHandler = Depends(get_handler)):
    response = handler.process_request(q.session_id, q.question)
    return Answer(
        answer=response['answer'],
        source_documents=response['source_documents'],
        session_id=response['session_id']
    )

#def set_process_function(func: Callable):
#    request_handler.set_process_function(func)