# GitHub AI Code Improvement Agent

An intelligent Python agent that automatically improves code quality in your GitHub repositories using AI models. The agent selects random files from your repositories, analyzes them, applies improvements, and commits the changes back to GitHub after validation.

## Features

- 🤖 **AI-Powered Code Improvement**: Uses Mixtral-8x7B model to enhance code quality
- 👨‍⚖️ **Intelligent Code Review**: Gemini 2.0 Flash model acts as a code reviewer
- 🔄 **Automatic Retry Logic**: Attempts to fix rejected improvements
- 📂 **Smart File Selection**: Filters and prioritizes important code files
- ⚡ **Multiple AI Providers**: Integrates GitHub, Google Gemini, and HuggingFace APIs
- 🛡️ **Safety First**: Validates all changes before committing

## Prerequisites

- Python 3.7+
- GitHub Personal Access Token
- Google Gemini API Key
- HuggingFace API Token

## Installation

1.**Clone this repository**
```bash
git clone <repository-url>
cd github-ai-agent
```

2.**Installing required Dependencies**
```bash
pip install PyGithub google-generativeai python-dotenv openai
```

3.**create a .env file**
GITHUB_TOKEN=your_github_personal_access_token
GEMINI_API_KEY=your_gemini_api_key
HF_TOKEN=your_huggingface_token

4. **Run the agent**
   ``` bash
   python agent.py
   ```


