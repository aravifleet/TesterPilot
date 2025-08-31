import os
import subprocess
import sys
import shutil
from urllib.parse import urlparse
import tempfile
import time
import tkinter as tk
from tkinter import messagebox
import threading

# -------------------- Setup & Configuration --------------------
# This is a temporary directory where the GitHub repository will be cloned.
# Using a temp directory ensures a clean environment each time the app runs.
TEMP_REPO_DIR = os.path.join(tempfile.gettempdir(), "smartbot_temp_repo")

# -------------------- Helper Utilities for Repo Handling --------------------
def is_valid_github_repo(url: str) -> bool:
    """
    Validates if a given URL is a valid GitHub repository URL.
    This prevents the application from trying to clone invalid links.
    """
    url = (url or "").strip()
    parsed = urlparse(url)
    # Check if the URL uses http/https and points to github.com
    if parsed.scheme not in ("http", "https") or parsed.netloc not in ("github.com", "www.github.com"):
        return False
    # A valid repo path should have at least an owner and a repo name (e.g., 'owner/repo')
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    return len(parts) >= 2

def clone_repo(repo_url: str) -> str:
    """
    Clones a GitHub repository into the temporary directory.
    If the directory already exists, it is removed and recreated to ensure a fresh clone.
    Returns the path to the cloned repository on success, otherwise an empty string.
    """
    dest_dir = os.path.abspath(TEMP_REPO_DIR)
    
    # Remove existing directory to ensure a clean slate
    if os.path.exists(dest_dir):
        try:
            shutil.rmtree(dest_dir)
        except Exception:
            # Fallback in case of a permission error or lock
            dest_dir = os.path.join(tempfile.gettempdir(), f"smartbot_temp_repo_{int(time.time())}")

    try:
        # Use subprocess to run the git clone command
        subprocess.run(["git", "clone", repo_url, dest_dir], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    except subprocess.CalledProcessError:
        # Return an empty string if the clone command fails
        return ""
    return dest_dir

def list_repo_files(repo_path: str) -> list:
    """
    Recursively lists all relevant files in the cloned repository,
    ignoring common system and build directories.
    This provides a clean list of files for the user to select from.
    """
    skip_dirs = {".git", ".vscode", "__pycache__", "node_modules", ".idea"}
    found = []
    # os.walk traverses the directory tree
    for root, dirs, files in os.walk(repo_path):
        # Modify dirs in-place to exclude unwanted directories from the search
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for f in files:
            found.append(os.path.relpath(os.path.join(root, f), repo_path))
    return sorted(found)

def detect_framework(repo_path: str) -> str:
    """
    Attempts to detect the testing framework used in the repository.
    It does this by searching for common keywords within the files.
    This is crucial for determining the correct command to run the tests.
    """
    files = list_repo_files(repo_path)
    joined_content = ""
    for f in files:
        ext = os.path.splitext(f)[1]
        # Focus on files that are likely to contain framework keywords
        if ext in (".py", ".js", ".ts", ".json", ".xml"):
            try:
                with open(os.path.join(repo_path, f), "r", encoding="utf-8", errors="ignore") as file:
                    joined_content += file.read().lower()
            except Exception:
                continue
    
    # Check for specific frameworks based on keywords and file types
    if "cypress" in joined_content:
        return "cypress"
    if "playwright" in joined_content:
        return "playwright"
    if "selenium" in joined_content and any(f.endswith(".java") for f in files):
        return "selenium-java"
    if "selenium" in joined_content and any(f.endswith(".py") for f in files):
        return "selenium-python"
    
    return "unknown"

# -------------------- Command Execution in a Thread --------------------
def run_command_thread(cmd, cwd, output_widget):
    """
    Executes a subprocess command in a separate thread.
    This is essential to prevent the GUI from freezing while the command is running.
    The output is streamed back to the GUI's text widget.
    """
    def target():
        try:
            # Popen allows for streaming the output in real-time
            proc = subprocess.Popen(
                cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                universal_newlines=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            if proc.stdout:
                for line in iter(proc.stdout.readline, ''):
                    output_widget.insert(tk.END, line)
                    output_widget.see(tk.END) # Auto-scroll to the bottom
            proc.wait()
        except Exception as e:
            output_widget.insert(tk.END, f"Error running command: {e}\n")

    thread = threading.Thread(target=target, daemon=True)
    thread.start()

# -------------------- Tkinter GUI Application --------------------
class QAChatbotGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("QA Automation Runner")
        self.geometry("700x500")

        self.repo_path = None
        self.framework = "unknown"
        self.files = []

        # UI elements setup
        self.create_widgets()

    def create_widgets(self):
        """Creates and packs all the widgets for the GUI."""
        # Frame for URL input
        url_frame = tk.Frame(self)
        url_frame.pack(pady=5)
        tk.Label(url_frame, text="GitHub Repo URL:").pack(side=tk.LEFT, padx=5)
        self.url_entry = tk.Entry(url_frame, width=60)
        self.url_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(url_frame, text="Clone & Analyze", command=self.clone_and_detect).pack(side=tk.LEFT)

        # Frame for output area
        output_frame = tk.Frame(self)
        output_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.output = tk.Text(output_frame, height=15, bg="#2d2d2d", fg="#ffffff", font=("Consolas", 10))
        self.output.pack(fill=tk.BOTH, expand=True)

        # Frame for file list and run button
        file_frame = tk.Frame(self)
        file_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        tk.Label(file_frame, text="Select a file to run:").pack()
        self.file_listbox = tk.Listbox(file_frame)
        self.file_listbox.pack(fill=tk.BOTH, expand=True)
        tk.Button(self, text="Run Selected Test", command=self.run_selected_file).pack(pady=5)

    def clone_and_detect(self):
        """Handles the main process of cloning and analyzing the repository."""
        url = self.url_entry.get().strip()
        if not is_valid_github_repo(url):
            messagebox.showerror("Error", "Invalid GitHub URL")
            return
        
        self.output.delete(1.0, tk.END)
        self.output.insert(tk.END, f"Cloning repo {url}...\n")
        self.update() # Force GUI update to show the message

        self.repo_path = clone_repo(url)
        if not self.repo_path:
            self.output.insert(tk.END, "Failed to clone repo. Please check the URL and your internet connection.\n")
            return
        
        self.framework = detect_framework(self.repo_path)
        self.output.insert(tk.END, f"Success! Detected framework: {self.framework}\n")

        self.files = list_repo_files(self.repo_path)
        self.file_listbox.delete(0, tk.END)
        for f in self.files:
            self.file_listbox.insert(tk.END, f)
        
        if not self.files:
            self.output.insert(tk.END, "No test files found. Make sure the repository contains relevant files.\n")

    def run_selected_file(self):
        """Determines the correct command to run the selected file and executes it."""
        if not self.repo_path:
            messagebox.showerror("Error", "No repository has been cloned yet.")
            return

        selected_indices = self.file_listbox.curselection()
        if not selected_indices:
            messagebox.showerror("Error", "Please select a file to run.")
            return

        file_to_run = self.files[selected_indices[0]]
        abs_file = os.path.join(self.repo_path, file_to_run)
        
        self.output.insert(tk.END, f"Running {file_to_run}...\n")
        self.update()
        
        # Determine command based on detected framework
        cmd = []
        if self.framework in ("playwright", "selenium-python"):
            # This is the corrected command. It uses the specific test runner
            # and passes the file path as an argument.
            cmd = ["pytest", abs_file]
        elif self.framework == "cypress":
            cmd = ["npx", "cypress", "run", "--spec", abs_file]
        elif self.framework == "selenium-java":
            cmd = ["mvn", "clean", "test"] # Maven typically runs all tests, not a single file
        elif abs_file.endswith(".py"):
            # This is the fallback for generic Python scripts
            python_executable = getattr(sys, "_base_executable", sys.executable)
            cmd = [python_executable, abs_file]

        if cmd:
            # Run the command in a separate thread to keep the GUI responsive
            run_command_thread(cmd, cwd=self.repo_path, output_widget=self.output)

# -------------------- Run Application --------------------
if __name__ == "__main__":
    try:
        app = QAChatbotGUI()
        app.mainloop()
    except tk.TclError:
        print("Error: A graphical display is required to run this application.")
        print("The application cannot be run in a terminal or headless environment.")
        print("Please ensure you are running it in a desktop environment with a display.")
        sys.exit(1)
