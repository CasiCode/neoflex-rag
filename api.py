from typing import Callable, Optional

from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from langchain_core.exceptions import (
    LangChainError,
    APIConnectionError,
    APIError,
    RateLimitError,
)


class LocalAPIException(Exception):
    def __init__(self, details: str):
        self.details = details


class ExternalAPIException(Exception):
    def __init__(self, details: str):
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


class RequestHandler:
    def __init__(self):
        self._process_func: Optional[Callable] = None
    
    def set_process_function(self, func: Callable):
        if not callable(func):
            raise ValueError('Process function must be callable')
        self._process_func = func
    
    def process_request(self, session_id: str, question: str):
        if self._process_func is None:
            raise LocalAPIException(detail='No process function registered on server.')
        
        try:
            response = self._process_func(session_id, question)
            required_keys = {'answer', 'source_documents', 'session_id'}
            if not all(key in response for key in required_keys):
                raise ExternalAPIException(detail='Bad response format.')
            return response
        
        except APIConnectionError as e:
            raise ExternalAPIException(f'Connection error: {str(e)}')
        except RateLimitError as e:
            raise ExternalAPIException(f'Rate limit exceeded: {str(e)}')
        except APIError as e:
            raise ExternalAPIException(f'OpenAI API error: {str(e)}')
        except LangChainError as e:
            raise ExternalAPIException(f'LangChain error: {str(e)}')
        except Exception as e:
            raise ExternalAPIException(f'Unexpected error: {str(e)}')
        

app = FastAPI()
request_handler = RequestHandler()


def get_handler():
    return request_handler

@app.exception_handler(LocalAPIException)
def local_api_exception_handler(exception: LocalAPIException):
    return JSONResponse(
        status_code=503,
        content={'message': f'Oops! Local API did something... {exception.details}'}
    )

@app.exception_handler(ExternalAPIException)
def external_api_exception_handler(exception: ExternalAPIException):
    status_code = 503
    if 'Rate limit exceeded' in exception.details:
        status_code = 429
    if 'Connection error' in exception.details:
        status_code = 504
    return JSONResponse(
        status_code=status_code,
        content={'message': f'Oops! External API did something... {exception.details}'}
    )

@app.post('/ask', response_model=Answer)
def ask_question(q: Question, handler: RequestHandler = Depends(get_handler)):
    response = handler.process_request(q.session_id, q.question)
    return Answer(
        answer=response['answer'],
        source_documents=response['source_documents'],
        session_id=response['session_id']
    )

def set_process_function(func: Callable):
    request_handler.set_process_function(func)