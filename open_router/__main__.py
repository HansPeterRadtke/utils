#!/usr/bin/env python3
import argparse
import json
import os
import sys
import requests

TOKEN = os.getenv("OPENROUTER_KEY")

ALLOWED_PARAMS = {
    'temperature': float,
    'top_p': float,
    'presence_penalty': float,
    'frequency_penalty': float,
    'max_tokens': int,
    'safe_prompt': lambda x: str(x).lower() in ('1', 'true', 'yes')
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

def get_auth_info():
    if not TOKEN:
        print("[HINT] Please set the OPENROUTER_KEY environment variable.")
        print("[HINT] See README.md for environment setup instructions.")
        raise ValueError("[ERROR] OPENROUTER_KEY not found in environment")
    r = requests.get("https://openrouter.ai/api/v1/auth/key", headers={"Authorization": f"Bearer {TOKEN}"})
    r.raise_for_status()
    return r.json()

def get_credits():
    if not TOKEN:
        print("[HINT] Please set the OPENROUTER_KEY environment variable.")
        print("[HINT] See README.md for environment setup instructions.")
        raise ValueError("[ERROR] OPENROUTER_KEY not found in environment")
    r = requests.get("https://openrouter.ai/api/v1/credits", headers={"Authorization": f"Bearer {TOKEN}"})
    r.raise_for_status()
    return r.json()

def get_models():
    headers = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
    r = requests.get("https://openrouter.ai/api/v1/models", headers=headers)
    r.raise_for_status()
    return r.json()

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    p = argparse.ArgumentParser(description='OpenRouter CLI')
    p.add_argument('--config', '-c', default='config.txt')
    p.add_argument('--prompt_file', '-f', default='prompt.txt')
    p.add_argument('--prompt', '-p')
    p.add_argument('--token', '-t')
    p.add_argument('--model', '-m')
    for param in ALLOWED_PARAMS:
        if param == 'safe_prompt':
            p.add_argument(f'--{param}', action='store_true')
        else:
            p.add_argument(f'--{param}', type=ALLOWED_PARAMS[param])
    args = p.parse_args()

    config_path = os.path.join(script_dir, args.config)
    prompt_file_path = os.path.join(script_dir, args.prompt_file)
    output_path = os.path.join(script_dir, "output.txt")

    cfg = load_config(config_path)
    token = args.token or cfg.get('token') or TOKEN
    model = args.model or cfg.get('model', 'mistralai/mistral-7b-instruct:free')

    if not token:
        print("[HINT] Please set the OPENROUTER_KEY environment variable.")
        print("[HINT] See README.md for environment setup instructions.")
        sys.exit('API token missing (provide via --token, config.txt, or environment)')

    if args.prompt is not None:
        prompt = args.prompt
    else:
        if not os.path.exists(prompt_file_path):
            sys.exit('prompt not provided and prompt.txt not found')
        with open(prompt_file_path, 'r', encoding='utf-8') as f:
            prompt = f.read()

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