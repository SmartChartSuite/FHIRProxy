'''Main function for FastAPI application'''

import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from api import api_router
from api_passthrough import api_passthrough_router
from models import CustomFormatter
from resourceHandler import resource_router
from util import deploy_url, log_level, passthrough_mode

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
app_title: str = 'FHIRProxy'
app_version: str = '0.1.0'
app = FastAPI(title=app_title, version=app_version, swagger_ui_parameters={'operationsSorter': 'method'})

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    if "resource_type" in request.path_params:
        logger.info(f'Resource {request.path_params["resource_type"]} query took {process_time:.2f} seconds and has a size of {response.headers["content-length"]} bytes')
    else:
        logger.info(f'Request took {process_time:.2f} seconds and has a size of {response.headers["content-length"]} bytes')
    return response

# ================= App Validation Error Override ======================
# @app.exception_handler(RequestValidationError)
# async def validation_exception_handler(request, exc):
#     reformatted_message = defaultdict(list)
#     for pydantic_error in exc.errors():
#         loc, msg = pydantic_error["loc"], pydantic_error["msg"]
#         filtered_loc = loc[1:] if loc[0] in ("body", "query", "path") else loc
#         try:
#             field_string = ".".join(filtered_loc)  # nested fields with dot-notation
#         except TypeError:  # Handles malformed JSON (extra comma)
#             return JSONResponse({'detail': 'Something was malformed in your request body'}, 400)
#         reformatted_message[field_string].append(msg)

#     return JSONResponse(
#         status_code=status.HTTP_400_BAD_REQUEST,
#         content=jsonable_encoder(
#             {"detail": "Invalid request", "errors": reformatted_message}
#         ),
#     )


# ========================== Routers inclusion =========================
if not passthrough_mode:
    app.include_router(api_router, tags=['Main API'])
    app.include_router(resource_router, tags=['FHIR Resources'])
else:
    logger.info('Starting up in passthrough mode...')
    app.include_router(api_passthrough_router, tags=['Main Passthrough API'])

# ========== Custom OpenAPI Things for Documentation Purposes ===========
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title= app_title,
        version= app_version,
        routes = app.routes
    )
    openapi_schema["servers"] = [{"url": deploy_url}]
    return openapi_schema

app.openapi = custom_openapi