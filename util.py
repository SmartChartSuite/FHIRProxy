import os

log_level: str = os.environ.get('LOG_LEVEL', 'INFO')
client_id: str = os.environ['CLIENT_ID']
scope: str = os.environ['SCOPE']
fhir_url: str = os.environ['FHIR_URL']
private_key_file: str | None = os.environ.get('PRIVATE_KEY_FILE')
public_key_file: str | None = os.environ.get('PUBLIC_KEY_FILE')
private_key_text: str | None = os.environ.get('PRIVATE_KEY')
public_key_text: str | None = os.environ.get('PUBLIC_KEY')

if public_key_text and public_key_file:
    public_key = public_key_text
elif public_key_file:
    with open(public_key_file, 'r') as fo:
        public_key: str = fo.read()
elif public_key_text:
    public_key = public_key_text

if private_key_text and private_key_file:
    print('Using PRIVATE_KEY variable')
    private_key = private_key_text
    print(private_key)
elif private_key_file:
    print('Using PRIVATE_KEY_FILE variable')
    with open(private_key_file, 'r') as fo:
        private_key: str = fo.read()
elif private_key_text:
    print('Using PRIVATE_KEY variable')
    private_key = private_key_text

if fhir_url[-1] != '/':
    fhir_url += '/'