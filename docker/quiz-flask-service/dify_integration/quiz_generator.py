"""
Quiz Generator Provider for Dify

This file should be copied to:
api/core/tools/builtin_tool/providers/quiz_generator/quiz_generator.py

Usage:
1. Copy this entire dify_integration directory to api/core/tools/builtin_tool/providers/
2. Rename dify_integration to quiz_generator
3. Restart Dify service
"""

from core.tools.builtin_tool.provider import BuiltinToolProviderController


class QuizGeneratorProvider(BuiltinToolProviderController):
    def _validate_credentials(self, credentials: dict) -> None:
        """
        Validate the credentials for Quiz Generator
        
        :param credentials: the credentials
        """
        quiz_service_url = credentials.get('quiz_service_url')
        if not quiz_service_url:
            raise ValueError('Quiz Service URL is required')
        
        if not quiz_service_url.startswith(('http://', 'https://')):
            raise ValueError('Quiz Service URL must start with http:// or https://')
