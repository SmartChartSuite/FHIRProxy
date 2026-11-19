"""Main function for FastAPI application"""

import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from api import api_router
from api_passthrough import api_passthrough_router
from logging_config import logger
from resourceHandler import resource_router
from util import deploy_url, log_level, passthrough_mode

logger.info("Logging configured at {}", log_level.upper())

# ========================== FastAPI variable ==========================
app_title: str = "FHIRProxy"
app_version: str = "0.1.0"
app = FastAPI(title=app_title, version=app_version, swagger_ui_parameters={"operationsSorter": "method"})

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        route = request.scope.get("route")
        route_path = getattr(route, "path", "unknown")
        logger.bind(method=request.method, route=route_path).exception("Unhandled request error")
        raise

    process_time = time.perf_counter() - start_time
    resource_type = request.path_params.get("resource_type")
    content_length = response.headers.get("content-length", "unknown")
    if resource_type:
        logger.info("Resource {} query took {:.2f} seconds and returned {} bytes", resource_type, process_time, content_length)
    else:
        logger.info("Request took {:.2f} seconds and returned {} bytes", process_time, content_length)
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
    app.include_router(api_router, tags=["Main API"])
    app.include_router(resource_router, tags=["FHIR Resources"])
else:
    logger.info("Starting up in passthrough mode...")
    app.include_router(api_passthrough_router, tags=["Main Passthrough API"])


# ========== Custom OpenAPI Things for Documentation Purposes ===========
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(title=app_title, version=app_version, routes=app.routes)
    openapi_schema["servers"] = [{"url": deploy_url}]
    return openapi_schema


app.openapi = custom_openapi
