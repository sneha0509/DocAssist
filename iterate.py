import os
import re
import shutil
from pathlib import Path

# --- CONFIG: extend if needed ---
CODE_EXTENSIONS = {
    # Programming languages
    ".py", ".ipynb",
    ".js", ".jsx", ".ts", ".tsx",
    ".java", ".kt", ".kts", ".groovy",
    ".c", ".h", ".cpp", ".cxx", ".hpp", ".hh", ".cc",
    ".go", ".rs",
    ".rb", ".php",
    ".cs", ".vb", ".fs",
    ".swift", ".m", ".mm",
    ".scala",
    ".pl", ".r",

    # Shell / scripts
    ".sh", ".bash", ".zsh",
    ".ps1", ".psm1",
    ".cmd", ".bat",

    # Data / config commonly used in codebases
    ".sql",
    ".yml", ".yaml", ".toml",
    ".json",
    ".xml",
    ".ini", ".cfg", ".conf",

    # Build tools
    ".gradle", ".sbt", ".mk",
}

# Special name-only matches (no extension)
NAME_ONLY_CODE = {"Dockerfile", "Makefile"}

# Common binary/non-code to skip
NON_CODE_BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".ico",
    ".pdf",
    ".zip", ".rar", ".7z", ".tar", ".gz",
    ".mp3", ".wav", ".flac", ".mp4", ".mkv", ".mov", ".avi",
    ".exe", ".dll",
    ".ttf", ".otf", ".woff", ".woff2",
    ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
}


def is_probably_text(file_path: Path, sample_bytes: int = 1024) -> bool:
    """
    Naive binary check: read a small chunk and look for NUL bytes.
    Helps avoid copying obvious binaries.
    """
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(sample_bytes)
        return b"\x00" not in chunk
    except Exception:
        # If unreadable, treat as non-text
        return False


def has_code_markers(file_path: Path, sample_chars: int = 2000) -> bool:
    """
    Look for typical code markers in the first ~2KB:
      - Shebangs (#!), imports, common keywords or braces.
    Used for extension-less/ambiguous files.
    """
    if not is_probably_text(file_path):
        return False

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            head = f.read(sample_chars)
    except Exception:
        return False

    head_lower = head.lower()

    # Shebang or typical import lines
    if head.startswith("#!") or "from " in head_lower or "import " in head_lower:
        return True

    markers = [
        "def ", "class ", "public ", "private ", "package ",
        "function ", "=>", "println", "console.log",
        "var ", "let ", "const ",
        "if (", "for (", "while (", "{", "}",
        "using ", "namespace ",
        # XML build/config
        "<project", "<configuration", "<properties>", "<dependencies>",
        # SQL
        "select ", "create table", "insert into", "alter table",
        # CI/CD YAML
        "pipeline:", "stages:", "jobs:", "steps:",
    ]
    return any(m in head_lower for m in markers) or any(m in head for m in markers)


def is_code_file(file_path: Path) -> bool:
    """
    Decide if a file is code-like by:
      1) Special name-only matches (Dockerfile, Makefile)
      2) Extension whitelist (CODE_EXTENSIONS)
      3) Avoid known binary extensions
      4) Content heuristics for extension-less or uncommon types
    """
    basename = file_path.name
    if basename in NAME_ONLY_CODE:
        return True

    ext = file_path.suffix.lower()

    if ext in NON_CODE_BINARY_EXTS:
        return False

    if ext in CODE_EXTENSIONS:
        return is_probably_text(file_path)

    # For extension-less or uncommon extensions, try content markers
    return has_code_markers(file_path)


def derive_repo_name_from_folder(folder_name: str) -> str:
    """
    Derive a clean repo name from a source folder.
    Examples:
      Javascript-Game_repo_1 -> Javascript-Game
      my-repo -> my-repo
    """
    # Remove a trailing pattern like _repo_<digits>
    m = re.match(r"^(.*?)(?:_repo_\d+)$", folder_name)
    return m.group(1) if m else folder_name


def copy_code_files(src_repo_dir: str, working_root: str) -> str:
    """
    Walk the repo at src_repo_dir, copy only 'code files' into:
        working_root / <repo_name> / <preserved relative structure>

    Returns the destination root path.
    """
    src = Path(src_repo_dir).resolve()
    if not src.exists():
        raise FileNotFoundError(f"Source repo directory not found: {src}")

    repo_name = derive_repo_name_from_folder(src.name)
    dest_root = Path(working_root).resolve() / repo_name
    dest_root.mkdir(parents=True, exist_ok=True)

    for path in src.rglob("*"):
        if path.is_file():
            rel = path.relative_to(src)
            dest_file = dest_root / rel

            if is_code_file(path):
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest_file)

    return str(dest_root)


if __name__ == "__main__":
    # --- CHANGE PATHS if needed ---
    SRC_DIR = r"C:\AI\DocAssist\final-year-project_repo_1"
    WORKING_ROOT = r"C:\AI\DocAssist\working"

    dest = copy_code_files(SRC_DIR, WORKING_ROOT)
    print(f"Code files copied to: {dest}")