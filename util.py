import os

log_level: str = os.environ.get('LOG_LEVEL', 'INFO')
client_id: str = os.environ['CLIENT_ID']
scope: str = os.environ['SCOPE']
fhir_url: str = os.environ['FHIR_URL']
private_key_file: str = os.environ['PRIVATE_KEY_FILE']
public_key_file: str = os.environ['PUBLIC_KEY_FILE']

if fhir_url[-1] != '/':
    fhir_url += '/'