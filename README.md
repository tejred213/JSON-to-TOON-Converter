# JSON <-> TOON Converter

Convert between JSON and [TOON](https://github.com/toon-format/spec) (Token-Oriented
Object Notation), an indentation-based format designed to represent JSON-like data
with fewer tokens — useful when passing structured data to an LLM.

## Structure

- `toonlib/` — core conversion library (`dumps`, `loads`), no dependencies
- `cli.py` — command-line converter built on `toonlib`
- `webapp/` — Flask web app with a paste-and-convert UI, also built on `toonlib`
- `tests/` — round-trip tests

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## CLI usage

```bash
python cli.py to-toon input.json -o output.toon
python cli.py to-json input.toon -o output.json
echo '{"a": 1, "b": [1,2,3]}' | python cli.py to-toon

# print a token/char comparison to stderr alongside the conversion
python cli.py to-toon input.json --stats
```

## Web app

```bash
python webapp/app.py
# open http://localhost:5050
```

The UI shows a live token/char comparison between the JSON and TOON forms of
whatever you convert, so you can see the savings directly.

Token counts are a heuristic (word/punctuation-run splitting), not the exact
tokenizer of any specific model — treat the percentage as directional, not
an exact billing figure.

### API endpoints

| Endpoint                | Body                                          | Use case                          |
|--------------------------|-----------------------------------------------|------------------------------------|
| `POST /api/to-toon`      | `{"input": "<json as a string>"}`             | Used by the web UI (textarea text) |
| `POST /api/to-json`      | `{"input": "<toon as a string>"}`             | Used by the web UI                 |
| `POST /api/convert/to-toon` | raw JSON body, `Content-Type: application/json` | Direct testing (Postman, curl)  |
| `POST /api/convert/to-json` | raw TOON body, `Content-Type: text/plain`       | Direct testing (Postman, curl)  |

If you paste JSON straight into Postman's body and hit send, use
`/api/convert/to-toon` — pasting it into `/api/to-toon` will fail because
that route expects the JSON re-encoded as a *string* inside `{"input": ...}`.
A ready-to-import collection covering both styles is in
`postman_collection.json`.

## Tests

```bash
pytest
```

## TOON format notes

- Objects: `key: value`, or `key:` followed by an indented block for nested objects.
- Primitive arrays: `key[n]: v1,v2,v3`
- Arrays of uniform objects: tabular form, `key[n]{field1,field2}:` followed by
  indented comma-separated rows.
- Non-uniform arrays: YAML-style `- ` list items.
- Strings are quoted only when needed (contain `,`, `:`, `{`, `}`, `[`, `]`, `#`,
  leading/trailing whitespace, or look like a number/boolean/null).

This is a from-scratch implementation of the common cases in the TOON spec.
Deeply nested arrays-of-arrays round-trip on a best-effort basis; see
`tests/test_converter.py` for what's covered.
