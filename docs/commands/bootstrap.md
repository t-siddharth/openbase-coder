# bootstrap

Run a plugin-declared bootstrapper by name.

## Usage

```bash
openbase-coder bootstrap BOOTSTRAPPER_NAME [OPTIONS]
```

## Options

| Option | Description |
|---|---|
| `--params TEXT` | JSON object string of parameters |
| `--params-file TEXT` | Path to JSON file containing parameters |

## Examples

### Inline JSON

```bash
openbase-coder bootstrap django-app \
  --params '{"target_dir":"/path/to/project","name":"billing"}'
```

### Params file

```bash
openbase-coder bootstrap django-app --params-file ./bootstrap.json
```

## Behavior

- Resolves `BOOTSTRAPPER_NAME` across all installed plugins
- Fails if unknown
- Fails if ambiguous across multiple plugins
- Executes the plugin's Python bootstrap handler
- Prints JSON result to stdout

## Input Requirements

- `--params`/`--params-file` must be a JSON object
- Use either `--params` or `--params-file` (not both)

## Discover Available Names

```bash
openbase-coder plugins bootstrappers
```
