# Basic Python Capstone — Magic Data Generator

A small CLI tool to generate artificial JSON data for testing and validation.

This repository provides a command-line program that reads a JSON schema and
generates JSON objects (one per line) into files or to stdout.

## Quick setup

- Requires Python 3.8+ (tested with newer 3.x versions).
- No external dependencies are required for basic usage.

Optional: create and activate a virtual environment (recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate   # zsh / bash

```

## Running the program

The project entrypoint is `main.py`, which instantiates the CLI `MagicGenerator`.
Use `python3 main.py --help` to see the available options.

Example: show help

```bash
python3 main.py --help
```

Example: generate files into `./output` using a schema file `schema.json`:

```bash
python3 main.py ./output --data_schema schema.json
```

Generate 5 files with 200 lines each using 2 processes:

```bash
python3 main.py ./output --data_schema schema.json --files_count 5 --data_lines 200 --multiprocessing 2
```

Print JSON lines to the console (no files):

```bash
python3 main.py . --data_schema schema.json --files_count 0 --data_lines 100
```

Provide the schema as an inline JSON string (use single quotes for zsh):

```bash
python3 main.py . --data_schema '{"id":"uuid","name":"rand(5)"}' --files_count 1 --data_lines 10
```

Clear the output directory before generating:

```bash
python3 main.py ./output --data_schema schema.json --clear_path
```

## Important options

- `--data_schema` (required): a path to a JSON schema file or a JSON string.
- `--files_count`: number of output files (use `0` to print to stdout).
- `--data_lines`: number of JSON lines per file / number of lines to print when `files_count=0`.
- `--multiprocessing`: how many worker processes to use (will be capped to available CPU count).
- `--clear_path`: remove existing files in the output directory before writing.

By default the program writes logs to `magicgenerator.log` in the project root. If
you want to inspect runtime errors or warnings, open that file:

```bash
less -R magicgenerator.log
```

## Schema file

Place your schema in `schema.json` (or pass the path). The schema format used by the
project describes fields and their generation rules. See `test_magicgenerator.py` for
examples of supported schema formats used in tests.

## Running tests

Run the test suite with pytest:

```bash
pytest -q
```

## Troubleshooting

- Exit code 2 or other failures: first run `python3 main.py --help` to confirm usage and
	inspect `magicgenerator.log` for error details.
- If you get errors parsing the schema, ensure the schema is valid JSON (or a valid
	path to a JSON file). Inline JSON strings must be quoted correctly for your shell.

If you want me to add example schema files or expand documentation for schema options,
tell me what generation features you rely on and I will add examples.

s