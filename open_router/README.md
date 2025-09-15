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

## Installation

1. Clone or place this folder inside your project.  
2. Ensure you have **Python 3.8+** installed.  
3. Install dependencies:
   ```bash
   pip install requests
   ```
4. Set your OpenRouter API key:
   ```bash
   export OPENROUTER_KEY="your_api_key_here"
   ```

---

## Usage

Run the CLI with:

```bash
python3 -m open_router --prompt "Hello AI!"
```

Or use a prompt file:

```bash
python3 -m open_router --prompt_file prompt.txt
```

Output will be written to **`output.txt`** inside this folder.

---

## Configuration

You can provide a `config.txt` in the same folder with default values.  
Example:

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
| `--config, -c`       | Path to config file (default: `config.txt`).                                                   |
| `--prompt, -p`       | Direct prompt string.                                                                          |
| `--prompt_file, -f`  | Path to prompt file (default: `prompt.txt`).                                                   |
| `--token, -t`        | API key (overrides environment/config).                                                        |
| `--model, -m`        | Model ID (default: `mistralai/mistral-7b-instruct:free`).                                      |
| `--temperature`      | Sampling temperature (float).                                                                  |
| `--top_p`            | Nucleus sampling probability mass (float).                                                     |
| `--presence_penalty` | Penalizes tokens already present in the text (float).                                          |
| `--frequency_penalty`| Penalizes frequent tokens (float).                                                              |
| `--max_tokens`       | Maximum number of tokens to generate (int).                                                    |
| `--safe_prompt`      | Use a "safe" system prompt to reduce harmful output (`--safe_prompt` flag, no value needed).   |

---

## Example

```bash
python3 -m open_router \
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
python3 -m open_router.tests.test_open_router
```

The test suite includes:
- Invalid token handling
