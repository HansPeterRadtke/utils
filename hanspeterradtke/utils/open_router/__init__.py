#!/usr/bin/env python3
import argparse
import json
import os
import sys
import requests

ALLOWED_PARAMS = {
    'temperature': float,
    'top_p': float,
    'presence_penalty': float,
    'frequency_penalty': float,
    'max_tokens': int,
}

def load_config(path):
    cfg = {}
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    k, v = line.split('=', 1)
                    cfg[k.strip().lower()] = v.strip()
    return cfg

def cast_param(name, value):
    caster = ALLOWED_PARAMS.get(name)
    if caster:
        try:
            return caster(value)
        except Exception:
            pass
    return value

def resolve_token(config_path=None, cli_token=None):
    cfg = load_config(config_path) if config_path else {}
    return cli_token or cfg.get('token') or os.getenv("OPENROUTER_KEY")

def get_auth_info(token=None, config_path=None):
    token = resolve_token(config_path, token)
    if not token:
        sys.exit("[ERROR] No API token found")
    r = requests.get("https://openrouter.ai/api/v1/auth/key", headers={"Authorization": f"Bearer {token}"})
    r.raise_for_status()
    return r.json()

def get_credits(token=None, config_path=None):
    token = resolve_token(config_path, token)
    if not token:
        sys.exit("[ERROR] No API token found")
    r = requests.get("https://openrouter.ai/api/v1/credits", headers={"Authorization": f"Bearer {token}"})
    r.raise_for_status()
    return r.json()

def get_models(token=None, config_path=None, outfile="models.json"):
    token = resolve_token(config_path, token)
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    r = requests.get("https://openrouter.ai/api/v1/models", headers=headers)
    r.raise_for_status()
    data = r.json()
    try:
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        sys.stderr.write(f"[ERROR] Failed to write models to {outfile}: {e}\n")
        return None
    return outfile

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    p = argparse.ArgumentParser(description='OpenRouter CLI')
    p.add_argument('--config', '-c', default='config.txt')
    p.add_argument('--prompt_file', '-f', default='prompt.txt')
    p.add_argument('--prompt', '-p')
    p.add_argument('--token', '-t')
    p.add_argument('--model', '-m')
    p.add_argument('--files', nargs='+', help='List of file paths to include in the prompt')
    p.add_argument('--dump_prompt', help='Path to write the full constructed prompt for debugging')
    p.add_argument('--debug_prompt', action='store_true', help='Print the full constructed prompt before sending')
    p.add_argument('--get_credits', action='store_true', help='Call get_credits() and exit')
    p.add_argument('--get_models', nargs='?', const='models.json', help='Call get_models() and write output to file (default: models.json)')
    for param in ALLOWED_PARAMS:
        p.add_argument(f'--{param}', type=ALLOWED_PARAMS[param])
    args = p.parse_args()

    config_path = os.path.join(script_dir, args.config)

    # handle special flags
    if args.get_credits:
        print(get_credits(token=args.token, config_path=config_path))
        return

    if args.get_models:
        outfile = args.get_models if isinstance(args.get_models, str) else 'models.json'
        result = get_models(token=args.token, config_path=config_path, outfile=outfile)
        if result:
            print(f"[INFO] Models written to {result}")
        return

    prompt_file_path = os.path.join(script_dir, args.prompt_file)
    output_path      = os.path.join(script_dir, "output.txt")

    cfg   = load_config(config_path)
    token = args.token or cfg.get('token') or os.getenv("OPENROUTER_KEY")
    model = args.model or cfg.get('model', 'mistralai/mistral-7b-instruct:free')

    # Build base prompt content
    if args.prompt is not None:
        prompt_content = args.prompt
    else:
        if not os.path.exists(prompt_file_path):
            sys.exit('prompt not provided and prompt.txt not found')
        with open(prompt_file_path, 'r', encoding='utf-8') as f:
            prompt_content = f.read()

    # Handle file list inclusion
    file_list_content = ""
    if args.files is not None:
        for fpath in args.files:
            if not os.path.exists(fpath):
                sys.exit(f"[ERROR] File not found: {fpath}")
            if not os.path.isfile(fpath):
                sys.exit(f"[ERROR] Not a file: {fpath}")
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    file_data = f.read()
            except Exception as e:
                sys.exit(f"[ERROR] Failed to read file {fpath}: {e}")

            file_list_content += f"Filename: {fpath}\n```\n{file_data}\n```\n\n"

    # Final prompt = file list first, then actual prompt
    prompt = file_list_content + "\n" + prompt_content

    # Debug / dump prompt if requested
    if args.debug_prompt:
        print("[DEBUG] Final constructed prompt:\n")
        print(prompt)
    if args.dump_prompt:
        try:
            with open(args.dump_prompt, 'w', encoding='utf-8') as dbg:
                dbg.write(prompt)
        except Exception as e:
            sys.stderr.write(f"[ERROR] Failed to write dump_prompt file: {e}\n")

    if not token:
        print("[HINT] Please set the OPENROUTER_KEY environment variable.")
        print("[HINT] See README.md for environment setup instructions.")
        sys.exit('API token missing (provide via --token, config.txt, or environment)')

    payload = {
        'model': model,
        'messages': [{'role': 'user', 'content': prompt}]
    }

    for param in ALLOWED_PARAMS:
        val = getattr(args, param)
        if val is None and param in cfg:
            val = cast_param(param, cfg[param])
        if val is not None:
            payload[param] = val

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    r = requests.post(
        'https://openrouter.ai/api/v1/chat/completions',
        headers=headers,
        data=json.dumps(payload)
    )

    if r.status_code != 200:
        sys.stderr.write(f'HTTP {r.status_code}: {r.text}\n')
        sys.exit(1)

    data = r.json()
    try:
        with open(output_path, "w", encoding="utf-8") as out:
            out.write(data['choices'][0]['message']['content'])
    except Exception:
        with open(output_path, "w", encoding="utf-8") as out:
            out.write(json.dumps(data, indent=2))

if __name__ == '__main__':
    main()