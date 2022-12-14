'''Main function for FastAPI application'''

import logging

from collections import defaultdict

from fastapi import FastAPI, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from util import log_level
from models import CustomFormatter
from api import api_router
from resourceHandler import resource_router

logger: logging.Logger = logging.getLogger('main')
logger.setLevel(logging.INFO)
ch: logging.StreamHandler = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(CustomFormatter())
logger.addHandler(ch)

if log_level == 'DEBUG':
    logger.info('Logging level is being set to DEBUG')
    logger.setLevel(logging.DEBUG)
    ch.setLevel(logging.DEBUG)
    logger.addHandler(ch)
else:
    logger.info('Logging level is at INFO')

# Handle some fhir.resources warnings
fhir_logger = logging.getLogger('fhir.resources')
fhir_logger.setLevel(logging.ERROR)
fhir_logger.addHandler(ch)

# ========================== FastAPI variable ==========================
app = FastAPI(title='FHIRProxy', version='0.0.1', swagger_ui_parameters={'operationsSorter': 'method'})

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ================= App Validation Error Override ======================
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    reformatted_message = defaultdict(list)
    for pydantic_error in exc.errors():
        loc, msg = pydantic_error["loc"], pydantic_error["msg"]
        filtered_loc = loc[1:] if loc[0] in ("body", "query", "path") else loc
        try:
            field_string = ".".join(filtered_loc)  # nested fields with dot-notation
        except TypeError:  # Handles malformed JSON (extra comma)
            return JSONResponse({'detail': 'Something was malformed in your request body'}, 400)
        reformatted_message[field_string].append(msg)

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=jsonable_encoder(
            {"detail": "Invalid request", "errors": reformatted_message}
        ),
    )


# ========================== Routers inclusion =========================
app.include_router(api_router, tags=['Main API'])
app.include_router(resource_router, tags=['FHIR Resources'])
