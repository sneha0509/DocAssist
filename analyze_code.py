import os
import json
import re
import ast
from pathlib import Path
from datetime import datetime
from typing import Tuple, List, Dict, Optional

# -------- CONFIG --------
REPO_DIR = r"C:\AI\DocAssist\working\ai-docreviewer"  # change to your repo folder
OUTPUT_JSON = r"C:\AI\DocAssist\result\metadata.json"

# File types we will process
LANG_BY_EXT = {
    ".py": "python",
    ".php": "php",
    ".js": "js",
    ".jsx": "js",   # treat JSX as JS for function/class names
    ".ts": "js",    # treat TS as JS (names only)
    ".tsx": "js",
    ".ipynb": "ipynb",  # Jupyter notebooks
}
# ------------------------


def read_text(path: Path) -> str:
    """Read file text safely."""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def count_lines(content: str) -> int:
    """Count logical lines in content."""
    return len(content.splitlines()) if content else 0


def count_chars(content: str) -> int:
    """Count characters."""
    return len(content) if content else 0


def iso_mtime(path: Path) -> str:
    """Return last modified timestamp ISO string."""
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).isoformat()
    except Exception:
        return ""


def rel_to_root(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except Exception:
        return str(path)


# ---------- Python extraction (AST) ----------
def extract_python_symbols(content: str) -> Tuple[List[str], List[str], List[str]]:
    """Return (functions, classes, imports) using Python AST; only top-level names."""
    funcs, classes, imports = [], [], []
    try:
        tree = ast.parse(content)
        # module-level funcs/classes
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                funcs.append(node.name)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
        # imports (walk)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend([a.name for a in node.names])
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for a in node.names:
                    imports.append(f"{mod}.{a.name}" if mod else a.name)
    except SyntaxError:
        pass
    # dedupe preserve order
    imports = list(dict.fromkeys(imports))
    return funcs, classes, imports


# ---------- PHP extraction (regex) ----------
def extract_php_symbols(content: str) -> Tuple[List[str], List[str], List[str], List[str]]:
    """
    Return (functions, classes, uses, includes) from PHP using regex.
    - function name()  (handles optional & before name)
    - class/interface/trait names
    - use statements
    - include/require(_once)
    """
    # Remove common comment blocks to reduce false positives
    content_no_comments = re.sub(r"/\*.*?\*/", "", content, flags=re.S)
    content_no_comments = re.sub(r"//.*?$", "", content_no_comments, flags=re.M)
    content_no_comments = re.sub(r"#.*?$", "", content_no_comments, flags=re.M)

    func_pat = re.compile(r"\bfunction\s+&?\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(", re.M)
    class_pat = re.compile(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)\b", re.M)
    iface_pat = re.compile(r"\binterface\s+([A-Za-z_][A-Za-z0-9_]*)\b", re.M)
    trait_pat = re.compile(r"\btrait\s+([A-Za-z_][A-Za-z0-9_]*)\b", re.M)

    functions = func_pat.findall(content_no_comments)
    classes = class_pat.findall(content_no_comments) + iface_pat.findall(content_no_comments) + trait_pat.findall(content_no_comments)

    uses = re.findall(r"\buse\s+([A-Za-z_\\][A-Za-z0-9_\\]*(?:\s+as\s+\w+)?)\s*;", content_no_comments)
    includes = re.findall(r"""\b(?:include|include_once|require|require_once)\s*\(\s*[^'"]+['"]\s*\)\s*;""", content_no_comments)

    # Deduplicate while preserving order
    functions = list(dict.fromkeys(functions))
    classes = list(dict.fromkeys(classes))
    uses = list(dict.fromkeys(uses))
    includes = list(dict.fromkeys(includes))
    return functions, classes, uses, includes


# ---------- JavaScript/TypeScript extraction (regex) ----------
def extract_js_symbols(content: str) -> Tuple[List[str], List[str], List[str]]:
    """
    Return (functions, classes, imports) from JS/TS using regex.
    Captures:
      - function name(...)
      - export function name(...)
      - const/let/var name = function(...)
      - const/let/var name = (...) => ...
      - class ClassName
      - import ... from 'mod', require('mod'), bare import 'mod'
    """
    # Remove simple comment styles to reduce noise
    content_no_block = re.sub(r"/\*.*?\*/", "", content, flags=re.S)
    content_nc = re.sub(r"//.*?$", "", content_no_block, flags=re.M)

    functions: List[str] = []
    classes: List[str] = []
    imports: List[str] = []

    # function declarations
    functions += re.findall(r"\bfunction\s+([A-Za-z_$][\w$]*)\s*\(", content_nc)
    # exported function declarations
    functions += re.findall(r"\bexport\s+function\s+([A-Za-z_$][\w$]*)\s*\(", content_nc)
    # variable-assigned function expressions
    functions += re.findall(r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?function\b", content_nc)
    # variable-assigned arrow functions
    functions += re.findall(r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\([^\)]*\)\s*=>", content_nc)
    # exported variable-assigned arrow functions
    functions += re.findall(r"\bexport\s+(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\([^\)]*\)\s*=>", content_nc)

    # classes
    classes += re.findall(r"\bclass\s+([A-Za-z_$][\w$]*)\b", content_nc)

    # imports / requires (capture the whole statement for now)
    imports += re.findall(r"""import\s+[^'"]+['"]""", content_nc)   # import X from 'mod'
    imports += re.findall(r"""import\s*['"][^'"]+['"]""", content_nc)  # bare import 'mod'
    imports += re.findall(r"""require\(\s*['"][^'"]+['"]\s*\)""", content_nc)  # require('mod')

    # Deduplicate while preserving order
    functions = list(dict.fromkeys(functions))
    classes = list(dict.fromkeys(classes))
    imports = list(dict.fromkeys(imports))
    return functions, classes, imports


# ---------- Notebook (.ipynb) extraction ----------
def extract_ipynb_symbols(text: str) -> Tuple[List[str], List[str], Dict[str, Optional[int]]]:
    """
    Parse a .ipynb as JSON, collect code cells, and heuristically extract
    Python functions/classes from concatenated code. Also returns cell counts.
    """
    functions: List[str] = []
    classes: List[str] = []
    stats = {"nb_num_code_cells": None, "nb_num_markdown_cells": None, "nb_kernel_language": None}

    try:
        nb = json.loads(text)
    except Exception:
        return functions, classes, stats

    cells = nb.get("cells", [])
    code_cells = [c for c in cells if c.get("cell_type") == "code"]
    md_cells = [c for c in cells if c.get("cell_type") == "markdown"]
    stats["nb_num_code_cells"] = len(code_cells)
    stats["nb_num_markdown_cells"] = len(md_cells)
    stats["nb_kernel_language"] = (
        nb.get("metadata", {}).get("kernelspec", {}).get("language")
        or nb.get("metadata", {}).get("language_info", {}).get("name")
    )

    concat_code = "\n\n".join("".join(c.get("source", [])) for c in code_cells)
    py_funcs, py_classes, _imports = extract_python_symbols(concat_code)
    functions = py_funcs
    classes = py_classes
    return functions, classes, stats


def extract_symbols_for_file(path: Path, lang: str, content: str):
    """Dispatch to language-specific extractor."""
    if lang == "python":
        funcs, classes, imports = extract_python_symbols(content)
        return funcs, classes, {"imports": imports}
    elif lang == "php":
        funcs, classes, uses, includes = extract_php_symbols(content)
        return funcs, classes, {"imports": uses, "includes": includes}
    elif lang == "js":
        funcs, classes, imports = extract_js_symbols(content)
        return funcs, classes, {"imports": imports}
    elif lang == "ipynb":
        funcs, classes, stats = extract_ipynb_symbols(content)
        return funcs, classes, {"nb_stats": stats}
    else:
        return [], [], {}


def get_file_metadata(path: Path, root: Path) -> dict:
    """Build the metadata object with the required (and helpful) fields."""
    ext = path.suffix.lower()
    lang = LANG_BY_EXT.get(ext)
    content = read_text(path)

    funcs, classes, extras = extract_symbols_for_file(path, lang, content) if lang else ([], [], {})
    num_lines = count_lines(content)
    num_chars = count_chars(content)

    data = {
        "file_name": os.path.basename(str(path)),
        "file_path": str(path.resolve()),
        "relative_path": rel_to_root(path, root),
        "extension": ext,
        "language": lang,
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "last_modified": iso_mtime(path),
        "num_lines": num_lines,
        "num_characters": num_chars,
        "num_functions": len(funcs),
        "num_classes": len(classes),
        "functions": funcs,
        "classes": classes,
    }

    # Attach extras per language
    if "imports" in extras:
        data["imports"] = extras["imports"]
    if "includes" in extras:
        data["includes"] = extras["includes"]
    if "nb_stats" in extras:
        data.update(extras["nb_stats"])

    return data


def is_target_code_file(path: Path) -> bool:
    """Return True if file extension indicates Python/PHP/JS/Notebook."""
    return path.is_file() and path.suffix.lower() in LANG_BY_EXT


def main():
    repo_path = Path(REPO_DIR).resolve()
    if not repo_path.exists():
        print(f"[ERROR] Directory not found: {repo_path}")
        return

    results = []
    for file_path in repo_path.rglob("*"):
        if is_target_code_file(file_path):
            results.append(get_file_metadata(file_path, repo_path))

    # Ensure output folder exists
    out_path = Path(OUTPUT_JSON)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)

    print(f"[INFO] Metadata extracted for {len(results)} files.")
    print(f"[INFO] JSON saved at: {out_path}")


if __name__ == "__main__":
    main()