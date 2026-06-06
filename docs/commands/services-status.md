# services status

Show launchd install/running state for all managed services.

## Usage

```bash
openbase-coder services status
```

Output includes whether each service is:

- `not installed`
- `running (pid ...)`
- `loaded (not running, last exit: ...)`
