#!/usr/bin/env python3
"""
AI Task Automation Script

This script processes GitHub issues labeled with 'ai-task' and generates
code changes using OpenAI. It creates pull requests with the suggested changes.

Usage:
    python .github/scripts/ai_task.py

Environment Variables:
    GITHUB_TOKEN: GitHub API token for repository access
    OPENAI_API_KEY: OpenAI API key for AI assistance
    ISSUE_NUMBER: GitHub issue number
    ISSUE_TITLE: GitHub issue title
    ISSUE_BODY: GitHub issue body content
    REPOSITORY: GitHub repository (owner/repo)
"""

import json
import logging

import requests
from openai import OpenAI

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class GitHubAPI:
    """GitHub API client for repository operations."""

    def __init__(self, token: str, repository: str):
        self.token = token
        self.repository = repository
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        self.base_url = "https://api.github.com"

    def get_issue(self, issue_number: int) -> dict:
        """Fetch issue details from GitHub."""
        url = f"{self.base_url}/repos/{self.repository}/issues/{issue_number}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def create_pull_request(self, title: str, body: str, head: str, base: str = "main") -> dict:
        """Create a pull request."""
        url = f"{self.base_url}/repos/{self.repository}/pulls"
        data = {
            "title": title,
            "body": body,
            "head": head,
            "base": base,
        }
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

    def create_branch(self, branch_name: str, base_sha: str) -> dict:
        """Create a new branch."""
        url = f"{self.base_url}/repos/{self.repository}/git/refs"
        data = {
            "ref": f"refs/heads/{branch_name}",
            "sha": base_sha,
        }
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

    def get_main_branch_sha(self) -> str:
        """Get the SHA of the main branch."""
        url = f"{self.base_url}/repos/{self.repository}/git/refs/heads/main"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()["object"]["sha"]


class AITaskProcessor:
    """Processes AI tasks and generates code suggestions."""

    def __init__(self, openai_api_key: str):
        self.client = OpenAI(api_key=openai_api_key)

    def analyze_issue(self, issue_data: dict) -> dict:
        """Analyze GitHub issue and generate development plan."""
        issue_content = f"""
Title: {issue_data['title']}
Body: {issue_data['body']}
Labels: {[label['name'] for label in issue_data.get('labels', [])]}
"""

        prompt = f"""
You are a senior software engineer analyzing a GitHub issue for the SRG RM Copilot project.
This is a Python package for Wheelhouse data ETL with AI automation capabilities.

Issue to analyze:
{issue_content}

Please provide:
1. A clear understanding of what needs to be implemented
2. Technical approach and architecture decisions
3. List of files that need to be created or modified
4. Step-by-step implementation plan
5. Testing strategy
6. Any potential risks or considerations

Format your response as JSON with the following structure:
{{
    "summary": "Brief summary of the task",
    "approach": "Technical approach description",
    "files_to_modify": ["list", "of", "files"],
    "implementation_plan": ["step 1", "step 2", "..."],
    "testing_strategy": "How to test this feature",
    "risks": ["potential", "risks"],
    "estimated_complexity": "low|medium|high"
}}
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a senior software engineer specializing in Python development and ETL systems."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )

            analysis_text = response.choices[0].message.content
            return json.loads(analysis_text)

        except Exception as e:
            logger.error(f"Error analyzing issue: {e}")
            return {
                "summary": "Failed to analyze issue",
                "approach": "Manual implementation required",
                "files_to_modify": [],
                "implementation_plan": ["Review issue manually"],
                "testing_strategy": "Standard testing practices",
                "risks": ["AI analysis failed"],
                "estimated_complexity": "unknown"
            }

    def generate_code_diff(self, analysis: dict, current_codebase: dict[str, str]) -> dict[str, str]:
        """Generate code changes based on analysis."""
        if not analysis.get("files_to_modify"):
            return {}

        changes = {}

        for file_path in analysis["files_to_modify"]:
            current_content = current_codebase.get(file_path, "")

            prompt = f"""
Based on this analysis:
Summary: {analysis['summary']}
Approach: {analysis['approach']}
Implementation Plan: {analysis['implementation_plan']}

Current content of {file_path}:
{current_content}

Please provide the updated code for this file that implements the required changes.
Return only the complete file content, properly formatted."""

            try:
                response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are a senior software engineer. Generate complete, working code."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=3000
                )

                changes[file_path] = response.choices[0].message.content

            except Exception as e:
                logger.error(f"Error generating code for {file_path}: {e}")
                changes[file_path] = f"# Error generating code: {e}\n{current_content}"

        return changes
