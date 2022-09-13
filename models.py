import logging
from pydantic import BaseModel


class CustomFormatter(logging.Formatter):

    grey: str = "\x1b[38;21m"
    green: str = "\x1b[32m"
    yellow: str = "\x1b[33m"
    red: str = "\x1b[31m"
    bold_red: str = "\x1b[31;1m"
    reset: str = "\x1b[0m"
    format: str = '{asctime}   {levelname:8s} --- {name}: {message}'

    FORMATS: dict[int, str] = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: green + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record) -> str:
        log_fmt: str = self.FORMATS.get(record.levelno)
        formatter: logging.Formatter = logging.Formatter(log_fmt, '%m/%d/%Y %I:%M:%S %p', style='{')
        return formatter.format(record)


class JWK(BaseModel):
    kid: str
    kty: str = 'RSA'
    n: str
    e: str


class JWKS(BaseModel):
    keys: list[JWK]
