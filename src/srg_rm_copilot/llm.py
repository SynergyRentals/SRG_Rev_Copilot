"""
OpenAI integration utility for AI-powered features.

This module provides a clean interface to OpenAI's API for use in
development automation and other AI-powered features.
"""

import logging
from typing import Any, Dict, List, Optional

from openai import OpenAI

from .config import Config

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for LLM-related errors."""
    pass


class LLMClient:
    """Client for interacting with OpenAI's API."""
    
    def __init__(self, config: Config):
        """
        Initialize the LLM client.
        
        Args:
            config: Configuration object containing OpenAI settings
        """
        self.config = config
        
        if not config.openai_api_key:
            logger.warning("OpenAI API key not configured. AI features will be disabled.")
            self.client = None
        else:
            self.client = OpenAI(api_key=config.openai_api_key)
            logger.info("OpenAI client initialized successfully")
    
    def is_available(self) -> bool:
        """
        Check if the LLM client is available for use.
        
        Returns:
            True if client is properly configured, False otherwise
        """
        return self.client is not None
    
    def generate_completion(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """
        Generate a text completion using OpenAI's chat API.
        
        Args:
            prompt: The user prompt to send
            system_message: Optional system message to set context
            model: Model to use (defaults to config.openai_model)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters for the API
            
        Returns:
            Generated text response
            
        Raises:
            LLMError: If the client is not available or API call fails
        """
        if not self.is_available():
            raise LLMError("OpenAI client is not available. Check API key configuration.")
        
        if model is None:
            model = self.config.openai_model
        
        # Prepare messages
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        try:
            logger.debug(f"Generating completion with model {model}")
            
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            content = response.choices[0].message.content
            
            # Log token usage
            if hasattr(response, 'usage'):
                usage = response.usage
                logger.debug(f"Token usage - prompt: {usage.prompt_tokens}, "
                           f"completion: {usage.completion_tokens}, "
                           f"total: {usage.total_tokens}")
            
            return content
            
        except Exception as e:
            logger.error(f"Error generating completion: {e}")
            raise LLMError(f"Failed to generate completion: {e}")
    
    def analyze_code(
        self,
        code: str,
        language: str = "python",
        analysis_type: str = "review"
    ) -> str:
        """
        Analyze code using AI.
        
        Args:
            code: Code to analyze
            language: Programming language
            analysis_type: Type of analysis (review, optimize, debug, etc.)
            
        Returns:
            Analysis results
        """
        system_message = f"""You are a senior software engineer specializing in {language} development.
        Provide a thorough {analysis_type} of the given code, focusing on:
        - Code quality and best practices
        - Potential bugs or security issues
        - Performance considerations
        - Maintainability and readability
        - Suggestions for improvement
        
        Be specific and actionable in your feedback."""
        
        prompt = f"Please {analysis_type} this {language} code:\n\n```{language}\n{code}\n```"
        
        return self.generate_completion(
            prompt=prompt,
            system_message=system_message,
            temperature=0.1,
            max_tokens=2000
        )
    
    def generate_tests(
        self,
        code: str,
        language: str = "python",
        framework: str = "pytest"
    ) -> str:
        """
        Generate test cases for given code.
        
        Args:
            code: Code to generate tests for
            language: Programming language
            framework: Testing framework to use
            
        Returns:
            Generated test code
        """
        system_message = f"""You are a senior software engineer specializing in {language} testing.
        Generate comprehensive test cases using {framework} for the given code.
        Include:
        - Happy path tests
        - Edge case tests
        - Error condition tests
        - Mock usage where appropriate
        
        Follow best practices for {framework} and write clean, maintainable test code."""
        
        prompt = f"Generate {framework} tests for this {language} code:\n\n```{language}\n{code}\n```"
        
        return self.generate_completion(
            prompt=prompt,
            system_message=system_message,
            temperature=0.1,
            max_tokens=3000
        )
    
    def explain_error(
        self,
        error_message: str,
        code_context: Optional[str] = None,
        language: str = "python"
    ) -> str:
        """
        Explain an error message and provide solutions.
        
        Args:
            error_message: The error message to explain
            code_context: Optional code context where error occurred
            language: Programming language
            
        Returns:
            Error explanation and solutions
        """
        system_message = f"""You are a helpful debugging assistant for {language} development.
        Explain errors clearly and provide actionable solutions."""
        
        prompt = f"Explain this {language} error and provide solutions:\n\nError: {error_message}"
        
        if code_context:
            prompt += f"\n\nCode context:\n```{language}\n{code_context}\n```"
        
        return self.generate_completion(
            prompt=prompt,
            system_message=system_message,
            temperature=0.1,
            max_tokens=1500
        )
    
    def generate_documentation(
        self,
        code: str,
        language: str = "python",
        doc_type: str = "docstring"
    ) -> str:
        """
        Generate documentation for code.
        
        Args:
            code: Code to document
            language: Programming language
            doc_type: Type of documentation (docstring, readme, api, etc.)
            
        Returns:
            Generated documentation
        """
        system_message = f"""You are a technical writer specializing in {language} documentation.
        Generate clear, comprehensive {doc_type} documentation following best practices."""
        
        prompt = f"Generate {doc_type} documentation for this {language} code:\n\n```{language}\n{code}\n```"
        
        return self.generate_completion(
            prompt=prompt,
            system_message=system_message,
            temperature=0.1,
            max_tokens=2000
        )
    
    def suggest_improvements(
        self,
        code: str,
        focus_area: str = "general",
        language: str = "python"
    ) -> str:
        """
        Suggest improvements for code.
        
        Args:
            code: Code to improve
            focus_area: Area to focus on (performance, readability, security, etc.)
            language: Programming language
            
        Returns:
            Improvement suggestions
        """
        system_message = f"""You are a senior software engineer and code mentor.
        Provide specific, actionable suggestions to improve the code,
        focusing on {focus_area} aspects."""
        
        prompt = f"Suggest improvements for this {language} code (focus: {focus_area}):\n\n```{language}\n{code}\n```"
        
        return self.generate_completion(
            prompt=prompt,
            system_message=system_message,
            temperature=0.2,
            max_tokens=2000
        )
