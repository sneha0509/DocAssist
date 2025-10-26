import os
import json
import clone_repo as cr
import iterate as it
import analyze_code as ac
import analyze_code as anc
import ai_analyzer as aa
from pathlib import Path

def download_repo(url: str) -> str:
    """
    Clones the repo and returns the repository folder name (last path component).
    Example full path: C:\\AI\\DocAssist\\codehub\\repos\\final-year-project_repo_6
    Returns: final-year-project_repo_6
    """
    try:
        local_path = cr.download_github_repo(url)
        # Use os.path to be robust across OS/path variants
        return os.path.basename(os.path.normpath(local_path))
    except Exception as e:
        print(f"Error: {e}")
        return "error"

def iterate_repo(src_dir: str) -> str:
    """
    Copies code files from src_dir to WORKING_ROOT and returns destination path.
    """
    try:
        WORKING_ROOT = r"codehub/destination"
        dest = it.copy_code_files(src_dir, WORKING_ROOT)
        print(f"Code files copied to: {dest}")
        return dest
    except Exception as e:
        print(f"Error: {e}")
        return "error"
    
def documentation_generation(project_name: str) -> str:
    """
    Analyzes metadata and generates documentation.
    """
    try:
        output_file = r"codehub/documents/"+project_name+"_generated_documentation.txt"
        SRC_DIR = r"codehub/extract/metadata.json"
        aa.analyse_metadata(output_file,SRC_DIR)
    except Exception as e:
        print(f"Error: {e}")   

def intial_setup():
    """
    Initial setup for directories.
    """
    try:
        base_path = Path(r"codehub")
        repos_path = base_path / "repos"
        destination_path = base_path / "destination"
        extract_path = base_path / "extract"
        extract_document = base_path / "documents"

        # Create directories if they don't exist
        repos_path.mkdir(parents=True, exist_ok=True)
        destination_path.mkdir(parents=True, exist_ok=True)
        extract_path.mkdir(parents=True, exist_ok=True)
        extract_document.mkdir(parents=True, exist_ok=True)

        print(f"Directories set up at: {base_path.resolve()}")
    except Exception as e:
        print(f"Error during initial setup: {e}") 


def main():
    repo_url = "https://github.com/Ak55073/Bharatiya"
    
    # Use a raw string literal for Windows paths
    intial_setup()
    # 1) If you want to derive the folder name from a fresh clone, uncomment:
    project_name = download_repo(repo_url)
    if project_name == "error":
        print("Error downloading repository.")
        return
    print(f"Project name: {project_name}")
    #-----------------------------------------------------
    # 2)Otherwise, use the given absolute path:
    project_path = r"C:\AI\DocAssist\codehub\repos\\"+project_name
    src_dir = project_path
    result = iterate_repo(src_dir)
    if result == "error":
        print("Error in iterating repository.")
        return
    project_name=result.split("\\")[-1]
   # If you need just the repo folder name from the absolute path:
    repo_folder = os.path.basename(os.path.normpath(src_dir))
    print(f"Repo folder: {repo_folder}")
#   #  -----------------------------------------------------
    # #3) Analyze code files and extract metadata
    REPO_DIR = r"codehub/destination/"+project_name  # change to your repo folder
    OUTPUT_JSON = r"codehub/extract/metadata.json"

    repo_path = Path(REPO_DIR).resolve()
    if not repo_path.exists():
        print(f"[ERROR] Directory not found: {repo_path}")
        return

    results = []
    for file_path in repo_path.rglob("*"):
        if ac.is_target_code_file(file_path):
            results.append(ac.get_file_metadata(file_path, repo_path))

    # Ensure output folder exists
    out_path = Path(OUTPUT_JSON)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)

    print(f"[INFO] Metadata extracted for {len(results)} files.")
    print(f"[INFO] JSON saved at: {out_path}")

# #------------------------------------------
# # 4) Analyze metadata and generate documentation
    doc_build=documentation_generation(project_name)
    if doc_build == "error":
        print("Error in documentation generation.")
        return
    

if __name__ == "__main__":
    main()