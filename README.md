# hanspeterradtke-utils

This repository contains general-purpose Python utility modules.  
Each module is self-contained and has its own `README.md` inside its folder for details.

---

## Installation

### 1. Working directly on this repository

Clone and install in editable mode:

```bash
git clone https://github.com/HansPeterRadtke/utils.git
cd utils
pip install -e .
```

This will install the package locally as `hanspeterradtke.utils`, so you can develop and test the modules.

---

### 2. Using this repository in another project

To integrate these utilities into another project, add this repository as a dependency.

**With `pyproject.toml`:**

```toml
[project]
dependencies = [
  "hanspeterradtke-utils @ git+https://github.com/HansPeterRadtke/utils.git"
]
```

**Or with `requirements.txt`:**

```
hanspeterradtke-utils @ git+https://github.com/HansPeterRadtke/utils.git
```

When you install your main project, pip will automatically fetch and install this utils repository.

---

## Usage in Python

The modules are available under the namespace `hanspeterradtke.utils`.

Example:

```python
import hanspeterradtke.utils.open_router as sut

client = sut.Client()
```

You can import directly from submodules as well:

```python
from hanspeterradtke.utils.parser import extract_python
```

In test scripts, you may alias imports (e.g. `sut`) for readability and consistency.

---

## Module Documentation

Each module has its own `README.md` inside its folder with details on usage, features, and tests.

---

## License

MIT