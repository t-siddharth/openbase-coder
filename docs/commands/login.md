# login

Authenticate to Openbase cloud in your browser.

## Usage

```bash
openbase-coder login
```

## Flow

1. Opens the Openbase web login in your browser.
2. Waits for the local OAuth callback.
3. Exchanges the authorization code for access/refresh tokens.
4. Stores tokens in `~/.openbase/auth.json`.

## Backend URL

Uses `OPENBASE_CODER_CLI_WEB_BACKEND_URL` if set.
Default: `https://app.openbase.cloud`.
