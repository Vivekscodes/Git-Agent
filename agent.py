import random
import time
from github import Github
import google.generativeai as genai
from dotenv import load_dotenv
import os
from openai import OpenAI

# Load environment variables
load_dotenv()
github_token = os.getenv("GITHUB_TOKEN")
gemini_api_key = os.getenv("GEMINI_API_KEY")
hf_token = os.getenv("HF_TOKEN")

# Validate environment variables
if not github_token:
    raise EnvironmentError("Missing GitHub token: 'GITHUB_TOKEN'")
if not gemini_api_key:
    raise EnvironmentError("Missing Gemini API key: 'GEMINI_API_KEY'")
if not hf_token:
    raise EnvironmentError("Missing HuggingFace API key: 'HF_TOKEN'")

model = genai.GenerativeModel("gemini-2.0-flash")

client = OpenAI(
    base_url="https://router.huggingface.co/together/v1",
    api_key=hf_token,
)
def authenticate_github(github_token):
    """
    Authenticate with GitHub using a personal access token.
    
    Args:
        github_token: GitHub personal access token
    
    Returns:
        Authenticated GitHub client
    """
    try:
        g = Github(github_token)
        user = g.get_user()
        print(f"Authenticated as {user.login}")
        return g
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return None

def show_repositories(github_token):
    """
    Display all repositories for the authenticated user.
    
    Args:
        github_token: GitHub personal access token
    """
    g = Github(github_token)
    user = g.get_user()
    repos = user.get_repos()
    
    if not repos:
        print("❌ No repositories found.")
        return
    
    
    for repo in repos:
        print(f"- {repo.name} (Stars: {repo.stargazers_count}, Forks: {repo.forks_count})")
    return repos

def select_repository(github_token):
    """
    Select a repository from the authenticated user's repositories.
    
    Args:
        github_token: GitHub personal access token
    
    Returns:
        Selected repository object
    """
    g = Github(github_token)
    user = g.get_user()
    repos = list(user.get_repos())
    
    if not repos:
        print("❌ No repositories found.")
        return None
    show_repositories(github_token)
    selected_repo=None
    print(f"select a repository by number (1-{len(repos)}): ")
    selected_index = int(input()) - 1

    if selected_index < 0 or selected_index >= len(repos):
        print("❌ Invalid selection. Selecting a random repository.")
        selected_repo=random.choice(repos)
    else:
        selected_repo = repos[selected_index]

    print(f"🔍 Selected repository: {selected_repo.name}")
    return selected_repo

def retry_revision(review, improved_code):
    attempts = 0
    while attempts < 2:
        revision_prompt = f"""
        Here is some feedback from a code review:
        {review}

        Previous improved code:
        ```python
        {improved_code}
        ```

        Please make necessary changes to the code based on the feedback.
        Return only the modified code (no explanation).
        """
        try:
            completion = client.chat.completions.create(
                model="mistralai/Mixtral-8x7B-Instruct-v0.1",
                messages=[
                    {
                        "role": "user",
                        "content": revision_prompt
                    }
                ]
            )
            improved_code = completion.choices[0].message.content.strip()
           
            review = judge_code(improved_code)
            if "Approve" in review:
                print("✅ Changes accepted by LLM Judge.")
                return improved_code, review
            else:
                print(f"❌ Attempt {attempts + 1} rejected. Retrying...")
        except Exception as e:
            print(f"🚨 Error during retry: {e}")
        attempts += 1
    return improved_code, review

def judge_code(improved_code, original_code=None):
    judge_prompt = f"""
    You are acting as a senior code reviewer.

    Original code:
    ```python
    {original_code}
    ```

    Improved code:
    ```python
    {improved_code}
    ```
    Check if the improved code is better than the original code.
    consider the following criteria:
    - Clarity and readability
    - Performance improvements
    - Bug fixes
    - Code quality (e.g., PEP 8 compliance for Python)
    
    Should this code be committed?
    Respond with either "[Approve]" or "[Reject]" and a short reason.
    """
    try:
        google_response = model.generate_content(judge_prompt)
        review = google_response.text.strip()
        print("👨‍⚖️ LLM Judge Review:\n", review)
        return review
    except Exception as e:
        print(f"❌ Error in judge_code: {e}")
        return "Reject: Error from LLM Judge"

def get_all_files(repo, path="", max_files=100, timeout=20):
    """
    Get files from repository with limits to prevent timeouts.

    Args:
        repo: GitHub repository object
        path: Starting path to search
        max_files: Maximum number of files to retrieve
        timeout: Maximum time in seconds to spend fetching files

    Returns:
        List of file content objects
    """
    start_time = time.time()
    all_files = []

    try:
        contents = repo.get_contents(path)
        while contents and len(all_files) < max_files:
            file_content = contents.pop(0)
            if file_content.type == "dir":
                contents.extend(repo.get_contents(file_content.path))
            else:
                all_files.append(file_content)
            
            if time.time() - start_time > timeout:
                print(f"⏱️ File fetch timeout after {len(all_files)} files")
                break
    except Exception as e:
        print(f"⚠️ Error fetching files: {e}")

    return all_files

def is_important_file(file_path):
    """
    Check if the file is important based on its path.
    """
    path_lower = file_path.lower()
    skip_patterns = [
        '/test/', 'test_', '_test', 
        '/tests/', 
        '.config.', 'config.', 
        '.gitignore', 
        'readme', '.md',
        '.env', '.env.', 
        'setup.py',
        '/docs/', '/examples/',
        '/node_modules/',
        '/venv/', '/env/',
        '.min.js', '.min.css'
    ]
    for pattern in skip_patterns:
        if pattern in path_lower:
            return False
    return True

def select_important_file(files):
    """
    Filter files by importance.
    
    Args:
        files: List of file content objects
        
    Returns:
        List of important file content objects
    """
    code_files = [f for f in files if f.name.endswith((".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp"))]
    if not code_files:
        return []
    
    important_files = []
    for file in code_files:
        if is_important_file(file.path):
            important_files.append(file)
        else:
            print(f"❌ Skipping file: {file.path}")
    return important_files

def run_agent(github_token, gemini_api_key):
    g = Github(github_token)
    if(authenticate_github(github_token)):
        print("✅ GitHub authentication successful.")
    else:
        print("❌ GitHub authentication failed.")
        return
    genai.configure(api_key=gemini_api_key)

    user = g.get_user()
    repos = list(user.get_repos())
    if not repos:
        print("❌ No repositories found.")
        return
    print("📂 Available repositories:")
    repo=select_repository(github_token)

    files = get_all_files(repo)
    important_files = select_important_file(files)
    
    if not important_files:
        print("❌ No suitable code files found.")
        return
    
    target_file = random.choice(important_files)
    print(f"📄 Selected file: {target_file.path}")

    original_code = target_file.decoded_content.decode("utf-8")

    print("🤖 Asking AI to improve the code...")
    prompt = f"""
    You are a code editor assistant. Make small improvements to the code below, like:
    - Adding comments
    - Better variable names
    - Simplifying logic (if minor)
    - Finding bugs and fixing them
    - Adding type hints
    - Improving performance

    

    Don't change the core logic. Return only the modified code.

    Code:
    {original_code}
    """
    
    try:
        completion = client.chat.completions.create(
            model="mistralai/Mixtral-8x7B-Instruct-v0.1",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.5,
            max_tokens=1000,
        )
        improved_code = completion.choices[0].message.content.strip()
     

        review = judge_code(improved_code, original_code)

        if "Approve" in review:
            print("✅ Committing changes to GitHub...")
            repo.update_file(
                path=target_file.path,
                message="Minor changes",
                content=improved_code,
                sha=target_file.sha
            )
            print("✅ Commit successful.")
        else:
            print("❌ Changes rejected by LLM Judge.")
            improved_code, final_review = retry_revision(review, improved_code)
            if "Approve" in final_review:
                repo.update_file(
                    path=target_file.path,
                    message="Minor Code Changes",
                    content=improved_code,
                    sha=target_file.sha
                )
                print("✅ Commit successful after revision.")
            else:
                print("❌ All attempts rejected. Manual review required.")
                
    except Exception as e:
        print(f"⚠️ Error during code improvement: {e}")
        return

if __name__ == "__main__":
    run_agent(github_token, gemini_api_key)