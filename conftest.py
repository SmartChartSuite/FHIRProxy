import os

for name, value in {
    "CLIENT_ID": "test-client",
    "SCOPE": "test-scope",
    "FHIR_URL": "http://127.0.0.1:9",
    "FHIR_AUTH": "Bearer test-token",
}.items():
    os.environ.setdefault(name, value)
