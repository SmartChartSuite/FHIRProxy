# FHIRProxy

## Environment Variables Needed for Deploy

```
LOG_LEVEL=<whats the minimum level of logging you want displayed. Default is INFO>
CLIENT_ID=<Client ID where the app is registered as a backend system>
SCOPE=<SMARTonFHIR scope for the application>
FHIR_URL=<FHIR URL that you will be proxying>
PUBLIC_KEY=<string quoted public key with the trailing \n>
PRIVATE_KEY=<string quoted private key with the trailing \n>"
CAPABILITY_STATEMENT=<options currently are EPIC_R4_STANDARD, you can pass in a file path too to the modified CapabilityStatement as described in the FHIR Search Helper Documentation>
DEPLOY_URL=<URL where the app will be deployed. Default is http://localhost:8080>
```

## Passthrough Mode

FHIR Proxy also supports passthrough mode, where it will immediately forward the request to the FHIR_URL in the environment variables and return the response to the client. You set it by defining `PASSTHROUGH_MODE=TRUE` in the environment variables. To support testing, passthrough mode also supports a `FHIR_AUTH` environment variable, where you can define the authentication for the FHIR_URL if it is not an OAuth 2.0 workflow. This will eventually be expanded to be allowed in regular mode, but it currently does not work.