import os
import logging


logger: logging.Logger = logging.getLogger('main.util')

log_level: str = os.environ.get('LOG_LEVEL', 'INFO')
client_id: str = os.environ['CLIENT_ID']
scope: str = os.environ['SCOPE']
fhir_url: str = os.environ['FHIR_URL']
fhir_auth: str | None = os.environ.get('FHIR_AUTH')
private_key_file: str | None = os.environ.get('PRIVATE_KEY_FILE')
public_key_file: str | None = os.environ.get('PUBLIC_KEY_FILE')
private_key_text: str | None = os.environ.get('PRIVATE_KEY')
public_key_text: str | None = os.environ.get('PUBLIC_KEY')
deploy_url: str = os.environ.get('DEPLOY_URL', 'http://localhost:8080')
capability_statement: str = os.environ.get('CAPABILITY_STATEMENT', 'EPIC_R4_STANDARD')
passthrough_mode_str: str  = os.environ.get('PASSTHROUGH_MODE', 'False')

if capability_statement == 'EPIC_R4_STANDARD':
    capability_statement_file = 'epic_r4_metadata_edited.json'
else:
    capability_statement_file = 'epic_r4_metadata_edited.json'

if public_key_text and public_key_file:
    public_key = public_key_text
elif public_key_file:
    with open(public_key_file, 'r') as fo:
        public_key: str | None = fo.read()
elif public_key_text:
    public_key = public_key_text
else:
    public_key = None

if private_key_text and private_key_file:
    logger.debug('Using PRIVATE_KEY variable')
    private_key = private_key_text
elif private_key_file:
    logger.debug('Using PRIVATE_KEY_FILE variable')
    with open(private_key_file, 'r') as fo:
        private_key: str | None = fo.read()
elif private_key_text:
    logger.debug('Using PRIVATE_KEY variable')
    private_key = private_key_text
else:
    private_key = None

if fhir_url[-1] != '/':
    fhir_url += '/'

if passthrough_mode_str.lower() == 'true':
    passthrough_mode = True
else:
    passthrough_mode = False