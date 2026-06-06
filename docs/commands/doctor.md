# doctor

Validate Openbase local runtime health and security settings.

## Usage

```bash
openbase-coder doctor
```

## Checks Performed

- Installation file presence (`installation.json`)
- launchd service install/running state
- Listening ports and bind addresses
- Required credentials in `.env`
- Detection of known insecure defaults for some keys

## Required Environment Keys

- `OPENBASE_CODER_CLI_SECRET_KEY`
- `OPENBASE_CODER_CLI_API_TOKEN`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `ANTHROPIC_API_KEY`
