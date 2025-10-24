import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen, Request


def download_github_repo(repo_url: str) -> str:
    """
    Download a Git repository to a local directory.
    Prefers 'git clone' if Git is available; falls back to ZIP download for GitHub URLs.

    Args:
        repo_url: The HTTPS URL of the repository. Examples:
                  - https://github.com/owner/repo
                  - https://github.com/owner/repo.git
                  - https://dev.azure.com/org/project/_git/repo (Git clone only)

    Returns:
        The absolute path to the downloaded repository directory.

    Raises:
        ValueError: If the URL is invalid or unsupported.
        RuntimeError: If clone or download fails.
    """
    if not isinstance(repo_url, str) or not repo_url.strip():
        raise ValueError("repo_url must be a non-empty string.")

    repo_url = repo_url.strip()

    # Choose a base directory under user's Downloads (Windows-friendly), fallback to temp
    try:
        downloads = Path(r"codehub/repos/")
        base_dir = downloads if downloads.exists() else Path(tempfile.gettempdir())
    except Exception:
        base_dir = Path(tempfile.gettempdir())

    # Make a destination directory name from the repo URL (owner_repo_XXXX)
    parsed = urlparse(repo_url)
    name_hint = Path(parsed.path).stem or "repo"
    dest_dir = _unique_dir(base_dir, f"{name_hint}_repo")

    # 1) Try git clone first (best fidelity)
    if _has_git():
        try:
            _git_clone(repo_url, dest_dir)
            return str(dest_dir.resolve())
        except RuntimeError as e:
            # Fall back only for GitHub URLs; otherwise surface the error
            if "github.com" not in (parsed.netloc.lower()):
                raise

    # 2) Fallback to ZIP download for GitHub repositories
    if "github.com" in parsed.netloc.lower():
        try:
            _download_github_zip(repo_url, dest_dir)
            return str(dest_dir.resolve())
        except RuntimeError as e:
            # Clean up if partially created
            if dest_dir.exists():
                shutil.rmtree(dest_dir, ignore_errors=True)
            raise

    # If we reach here, the host is not supported for ZIP and git failed
    raise RuntimeError(
        "Failed to download the repository. Ensure Git is installed and the URL is accessible.\n"
        f"Attempted: git clone on '{parsed.netloc}', ZIP fallback only supported for GitHub."
    )


def _has_git() -> bool:
    """Return True if 'git' is available on PATH."""
    try:
        subprocess.run(["git", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception:
        return False


def _git_clone(repo_url: str, dest_dir: Path) -> None:
    """Clone the repo using git into dest_dir."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(["git", "clone", repo_url, str(dest_dir)], check=True)
    except subprocess.CalledProcessError as e:
        # Remove the created directory if clone failed
        if dest_dir.exists():
            shutil.rmtree(dest_dir, ignore_errors=True)
        raise RuntimeError(f"git clone failed: {e}") from e


def _download_github_zip(repo_url: str, dest_dir: Path) -> None:
    """
    Download a GitHub repository as ZIP by trying 'main' then 'master'.
    Extracts into dest_dir. No git history, just files.
    """
    owner, repo = _parse_github_owner_repo(repo_url)
    if not owner or not repo:
        raise ValueError("Invalid GitHub URL format. Expected https://github.com/<owner>/<repo>[.git]")

    dest_dir.mkdir(parents=True, exist_ok=True)

    # Try both common default branches
    branches = ["main", "master"]
    last_err = None
    for branch in branches:
        zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"
        try:
            _download_and_extract_zip(zip_url, dest_dir)
            return
        except Exception as e:
            last_err = e
            continue

    # If both branches failed, surface a helpful error
    raise RuntimeError(
        f"Could not download ZIP for '{owner}/{repo}'. Tried branches {branches}. "
        "If the default branch is different or the repo is private, consider installing Git and cloning, "
        "or provide a personal access token."
    ) from last_err


def _download_and_extract_zip(zip_url: str, dest_dir: Path) -> None:
    """Download a ZIP from zip_url and extract into dest_dir."""
    # Basic browser-like headers to avoid some blocks
    req = Request(zip_url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status} when fetching {zip_url}")
        tmp_zip = dest_dir / "repo.zip"
        with open(tmp_zip, "wb") as f:
            f.write(resp.read())

    # Extract
    with zipfile.ZipFile(tmp_zip, "r") as zf:
        zf.extractall(dest_dir)
    # Remove zip after extraction
    try:
        tmp_zip.unlink()
    except Exception:
        pass

    # If GitHub creates a top-level folder like 'repo-<branch>', flatten it
    _flatten_single_subdir(dest_dir)


def _flatten_single_subdir(dest_dir: Path) -> None:
    """If dest_dir contains exactly one directory, move its contents up and delete it."""
    entries = [p for p in dest_dir.iterdir()]
    if len(entries) == 1 and entries[0].is_dir():
        top = entries[0]
        for item in top.iterdir():
            shutil.move(str(item), dest_dir / item.name)
        shutil.rmtree(top, ignore_errors=True)


def _parse_github_owner_repo(repo_url: str):
    """Return (owner, repo) from a GitHub URL."""
    parsed = urlparse(repo_url)
    if "github.com" not in parsed.netloc.lower():
        return None, None
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        return None, None
    owner = parts[0]
    repo = parts[1]
    # Strip trailing .git if present
    if repo.endswith(".git"):
        repo = repo[:-4]
    return owner, repo


def _unique_dir(base_dir: Path, prefix: str) -> Path:
    """Create a unique directory under base_dir with a given prefix."""
    base_dir.mkdir(parents=True, exist_ok=True)
    for i in range(1, 10000):
        candidate = base_dir / f"{prefix}_{i}"
        if not candidate.exists():
            return candidate
    # Fallback to temp dir if somehow exhausted
    return Path(tempfile.mkdtemp(prefix=f"{prefix}_", dir=str(base_dir)))



if __name__ == "__main__":
    url = "https://github.com/sneha0509/final-year-project"  # example
    try:
        local_path = download_github_repo(url)
        print(f"Repository downloaded to: {local_path}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)