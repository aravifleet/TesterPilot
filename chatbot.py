import re
from urllib.parse import urlparse
import subprocess
import os


def list_repo_files(repo_path: str) -> list:
    """Walk all repo files and list them"""
    repo_path = os.path.abspath(repo_path)
    found = []
    skip_dirs = {".git", ".vscode", "__pycache__"}
    
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for fname in files:
            rel = os.path.relpath(os.path.join(root, fname), repo_path)
            found.append(rel)

    if not found:
        print("\n📂 Repository is empty (no files found).")
    else:
        print("\n📂 Files found in repository:")
        for p in sorted(found):
            print("  -", p)

    return found


def clone_repo(repo_url: str, dest_dir: str = "temp_repo") -> str:
    """Clone the repository URL into dest_dir"""
    repo_url = (repo_url or "").strip()
    if not repo_url:
        raise ValueError("Empty repository url")

    dest_dir = os.path.abspath(dest_dir)
    if os.path.exists(dest_dir):
        raise FileExistsError(f"Destination already exists {dest_dir}")

    try:
        subprocess.run(["git", "clone", repo_url, dest_dir], check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"'git clone' failed: {e}") from e

    return dest_dir


def is_valid_github_repo(url):
    """Validate GitHub repo link"""
    url = (url or "").strip()
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        return False
    if parsed.netloc not in ("github.com", "www.github.com"):
        return False

    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) < 2:
        return False

    owner, repo = parts[0], parts[1]
    if not owner or not repo:
        return False

    return True


def owner_repo_from(url):
    """Extract owner and repo from GitHub URL"""
    parsed = urlparse(url.strip())
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    owner, repo = parts[0], parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    return owner, repo

def detect_framework(files: list) -> str:
    """Detect whether repo uses Selenium (Java/Python), Playwright (Python), or Cypress."""
    for f in files:
        f_low = f.lower()

        # Selenium Python
        if f_low.endswith(".py") and "selenium" in open(f, errors="ignore").read().lower():
            return "selenium-python"

        # Selenium Java
        if f_low.endswith(".java") and "selenium" in open(f, errors="ignore").read().lower():
            return "selenium-java"

        # Playwright Python
        if f_low.endswith(".py") and "playwright" in open(f, errors="ignore").read().lower():
            return "playwright-python"

        # Cypress
        if f_low.endswith((".js", ".ts")) and "cypress" in open(f, errors="ignore").read().lower():
            return "cypress"

    return "unknown"



def chatbot():
    print("Hello user!!! welcome to QA chatbot!!!")
    print("I will help you with running test scripts from github repository")

    while True:
        repo_link = input("Please enter the valid github repository link: ").strip()
        if is_valid_github_repo(repo_link):
            owner, repo = owner_repo_from(repo_link)
            print(f"\nThank you for providing the repository link {repo_link}")
            print(f" owner : {owner} , repo : {repo}")

            try:
                repo_path = clone_repo(repo_link, "temp_repo")
                print(f"\nRepository successfully cloned into {repo_path}")

                # 👉 List repo files here
                files = list_repo_files(repo_path)

            except FileExistsError as e:
                print(f"\n⚠️ {e}")
                # 👉 Even if already exists, list the files
                repo_path = "temp_repo"
                files = list_repo_files(repo_path)

            except RuntimeError as e:
                print(f"\n❌ Cloning failed: {e}")
                break

            # 👉 Detect framework here (after we have `files`)
            framework = detect_framework([os.path.join(repo_path, f) for f in files])
            print(f"\n🔍 Detected framework: {framework}")
            break

        else:
            print("\n That doesn't look like a valid GitHub repository link.")
            print("   Expected format: https://github.com/<owner>/<repo>")
            print("   Example: https://github.com/yourname/yourrepo\n")
            print("Please try again.\n")

            



if __name__ == "__main__":
    chatbot()
