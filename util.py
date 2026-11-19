import os

from logging_config import logger


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        logger.critical("Missing required environment variable: {}", name)
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _read_key_file(path: str, variable_name: str) -> str:
    try:
        with open(path, "r") as file:
            return file.read()
    except OSError as exc:
        logger.bind(variable=variable_name).opt(exception=exc).critical("Unable to read configured key file")
        raise RuntimeError(f"Unable to read {variable_name}") from exc

log_level: str = os.environ.get("LOG_LEVEL", "INFO")
client_id: str = _required_env("CLIENT_ID")
scope: str = _required_env("SCOPE")
fhir_url: str = _required_env("FHIR_URL").strip()
if not fhir_url:
    raise RuntimeError("FHIR_URL must not be empty")
fhir_auth: str | None = os.environ.get("FHIR_AUTH")
private_key_file: str | None = os.environ.get("PRIVATE_KEY_FILE")
public_key_file: str | None = os.environ.get("PUBLIC_KEY_FILE")
private_key_text: str | None = os.environ.get("PRIVATE_KEY")
public_key_text: str | None = os.environ.get("PUBLIC_KEY")
deploy_url: str = os.environ.get("DEPLOY_URL", "http://localhost:8080")
capability_statement: str = os.environ.get("CAPABILITY_STATEMENT", "EPIC_R4_STANDARD")
passthrough_mode_str: str = os.environ.get("PASSTHROUGH_MODE", "False")

if capability_statement == "EPIC_R4_STANDARD":
    capability_statement_file = "epic_r4_metadata_edited.json"
else:
    capability_statement_file = "epic_r4_metadata_edited.json"

if public_key_text and public_key_file:
    public_key = public_key_text
elif public_key_file:
    public_key: str | None = _read_key_file(public_key_file, "PUBLIC_KEY_FILE")
elif public_key_text:
    public_key = public_key_text
else:
    public_key = None

if private_key_text and private_key_file:
    logger.debug("Using PRIVATE_KEY variable")
    private_key = private_key_text
elif private_key_file:
    logger.debug("Using PRIVATE_KEY_FILE variable")
    private_key: str | None = _read_key_file(private_key_file, "PRIVATE_KEY_FILE")
elif private_key_text:
    logger.debug("Using PRIVATE_KEY variable")
    private_key = private_key_text
else:
    private_key = None

if fhir_url[-1] != "/":
    fhir_url += "/"

if passthrough_mode_str.lower() == "true":
    passthrough_mode = True
else:
    passthrough_mode = False
