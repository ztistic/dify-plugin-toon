# Dify TOON Converter Plugin

**Author:** [EFT](https://github.com/ztistic)
**Repo:** [dify-plugin-toon](https://github.com/ztistic/dify-plugin-toon)
**Version:** 1.0.0
**Type:** tool

## Description

This Dify plugin converts data between **JSON** and **TOON** (Token-Oriented
Object Notation), a compact, human-readable serialization format designed for
LLM prompts. By removing redundant quotes, braces and repeated keys, TOON
typically reduces token usage by **30-60%** compared to JSON, which lowers
cost and leaves more context window for actual content.

Conversion is powered by [toon-format](https://pypi.org/project/toon-format/),
the **official Python implementation** of the TOON specification. It passes
every official conformance fixture and guarantees lossless round-trips
(`loads(dumps(data)) == data`) for every JSON-compatible value, including
nested structures and tabular arrays with nested field groups.

- TOON specification: <https://github.com/toon-format/spec>
- Related plugin request: [langgenius/dify-plugins#1619](https://github.com/langgenius/dify-plugins/issues/1619)

## Requirements

- Dify 1.14.2 or later

No network connection or external service is required: conversion runs
locally in the plugin runtime, with no endpoint to configure and no
credentials to provide.

## Installation

1. From Dify Marketplace: search "TOON Converter" in the Plugins page and install.
2. Or install from a local `.difypkg`: Plugins -> Install Plugin -> Via Local File.

## Tools

### JSON to TOON

Convert a JSON string into TOON format. Returns a JSON message containing the
TOON output together with compression statistics.

| Parameter    | Type     | Required | Description                                             |
|--------------|----------|----------|---------------------------------------------------------|
| `json_input` | `string` | `Yes`    | The JSON string to convert                              |
| `delimiter`  | `select` | `No`     | Field delimiter: `comma` (default), `tab` or `pipe`     |

Output message fields:

| Field               | Description                                       |
|---------------------|---------------------------------------------------|
| `toon`              | The converted TOON string                         |
| `original_chars`    | Character count of the input JSON                 |
| `toon_chars`        | Character count of the TOON output                |
| `compression_ratio` | Saved fraction, e.g. `0.6` means 60% smaller      |
| `savings_percent`   | Same value as percentage, e.g. `60.0`             |

Example input:

```json
{"name": "Alice", "age": 30, "active": true}
```

Example output (message text):

```json
{
  "toon": "name: Alice\nage: 30\nactive: true",
  "original_chars": 44,
  "toon_chars": 32,
  "compression_ratio": 0.2727,
  "savings_percent": 27.27
}
```

Uniform arrays of objects are encoded in tabular form: field names are
declared once in the header and each element becomes one compact row.

### TOON to JSON

Convert a TOON string back into a pretty-printed JSON string
(`ensure_ascii=false`, 2-space indent). The delimiter is auto-detected from
tabular headers, as the TOON specification requires. Round-tripping
JSON -> TOON -> JSON preserves the data.

| Parameter    | Type     | Required | Description                |
|--------------|----------|----------|----------------------------|
| `toon_input` | `string` | `Yes`    | The TOON string to convert |

## Error Handling

Both tools validate their input and return friendly English error messages
instead of raising raw exceptions:

- Empty input: `Error: ... is empty. Please provide a ... string to convert.`
- Invalid JSON: `JSON parsing failed: ...`
- Invalid TOON: `TOON parsing failed: ...`
- Unsupported value during encoding: `TOON encoding failed: ...`

## Privacy

All conversion happens in-memory inside the plugin runtime. No data is
collected, logged, stored or transmitted anywhere. See
[PRIVACY.md](./PRIVACY.md) for details.

## Development

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

Package with the [Dify Plugin CLI](https://github.com/langgenius/dify-plugin-daemon/releases):

```bash
dify plugin package . -o dify-plugin-toon-1.0.0.difypkg
```

## License

[MIT](./LICENSE)
