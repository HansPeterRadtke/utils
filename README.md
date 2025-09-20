# hanspeterradtke-utils

This repository contains general-purpose Python utility modules. Each module is self-contained and includes its own `README.md` with detailed usage instructions.

---

## Installation

Clone the repository and install in editable mode:

```
git clone https://github.com/HansPeterRadtke/utils.git
cd utils
pip install -e .
```

This installs the utilities under the namespace `hanspeterradtke.utils`, allowing direct usage or import.

---

## Modules

### [open_router](./hanspeterradtke/utils/open_router/README.md)
Command-line interface to the OpenRouter API. Allows sending prompts to language models, fetching credits, listing models, and includes debugging and file-based prompt construction.

### [parser](./hanspeterradtke/utils/parser/README.md)
Extracts Python code blocks from markdown-style text, especially used to parse OpenRouter responses and test outputs.

### [table_reader](./hanspeterradtke/utils/table_reader/README.md)
CLI tool to explore structured data in JSON (list-of-dicts) or Pandas DataFrame `.pkl` files. Offers filtering, slicing, and descriptive statistics.

---

## Usage

Each module can be run as a standalone CLI:

```
python3 -m hanspeterradtke.utils.<module>
```

Examples:
- `python3 -m hanspeterradtke.utils.open_router --prompt "Hello"`
- `python3 -m hanspeterradtke.utils.parser`
- `python3 -m hanspeterradtke.utils.table_reader data.json --list-columns`

Refer to each module’s README (linked above) for full details on configuration, parameters, and test execution.

---

## License

MIT