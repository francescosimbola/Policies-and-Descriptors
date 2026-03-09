from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.api import router
from src.models import ValidationError
from src.utility.logger import get_logger

app = FastAPI(
    title='LLM Engine API',
    description='**LLM Engine** is a service responsible to manage requests from the Computational Governance Platform to validate resources using natural language text to sent to the LLMs.\n\n# Register a LLM Engine\n\nOnce you set up the parameters necessary to connect to the APIs of an LLM, when you create a policy in Witboost, you can select the LLM Engine to use for the evaluation. \n\nWhen you select LLM Engine, you will be able to provide the prompt written in natural language which provides the instructions to the LLM for the evaluation of the resource.\n',  # noqa: E501
    version='0.1',
)

logger = get_logger()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.error(exc)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=jsonable_encoder(ValidationError(error=str(exc)))
    )

app.include_router(router)