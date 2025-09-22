# OpenRouter CLI

This folder provides a **command-line client (CLI)** for interacting with the [OpenRouter API](https://openrouter.ai/).  
It allows you to send prompts to large language models, retrieve responses, and check account information.

---

## Features

- Send chat prompts to OpenRouter models.
- Load prompts from a file or directly from the command line.
- Configure defaults via `config.txt` or environment variables.
- Supports model selection and generation parameters.
- Provides helper functions to check:
  - API key authentication
  - Remaining credits
  - Available models

---

## Installation (Editable Mode)

This CLI is intended to be installed in **editable mode** so it can be used from anywhere on your system:

```bash
pip install -e .
```

Make sure you're inside the repository root when running the command.

---

## Usage

Run the CLI from **anywhere**:

```bash
python3 -m hpr.utils.open_router --prompt "Hello AI!"
```

Or use a prompt file:

```bash
python3 -m hpr.utils.open_router --prompt_file prompt.txt
```

Output will be written to **`output.txt`** in your current working directory.

---

## Configuration

You can place a `config.txt` in **any directory** where you're running the CLI.

The CLI looks for this file in the **current working directory**, or you can specify a custom path using `--config`.

Example contents:
```
token=YOUR_API_KEY
model=mistralai/mistral-7b-instruct:free
temperature=0.7
top_p=0.9
max_tokens=512
```

---

## Command-Line Arguments

| Option               | Description                                                                                   |
|----------------------|-----------------------------------------------------------------------------------------------|
| `--config, -c`       | Path to config file (default: `./config.txt` in current directory).                           |
| `--prompt, -p`       | Direct prompt string.                                                                          |
| `--prompt_file, -f`  | Path to prompt file (default: `prompt.txt`).                                                   |
| `--token, -t`        | API key (overrides environment/config).                                                        |
| `--model, -m`        | Model ID (default: `mistralai/mistral-7b-instruct:free`).                                      |
| `--temperature`      | Sampling temperature (float).                                                                  |
| `--top_p`            | Nucleus sampling probability mass (float).                                                     |
| `--presence_penalty` | Penalizes tokens already present in the text (float).                                          |
| `--frequency_penalty`| Penalizes frequent tokens (float).                                                              |
| `--max_tokens`       | Maximum number of tokens to generate (int).                                                    |

---

## Example

```bash
python3 -m hpr.utils.open_router \
  --prompt "Write a haiku about Raspberry Pi." \
  --model openai/gpt-3.5-turbo \
  --temperature 0.8 \
  --max_tokens 100
```

This will send the request and save the result into `output.txt`.

---

## Tests

Run tests from repo root:

```bash
python3 -m hpr.utils.open_router.tests.test_open_router
```

The test suite includes:
- Invalid token handling
