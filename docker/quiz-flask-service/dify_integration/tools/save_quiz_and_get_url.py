"""
Quiz Generator Tool for Dify

This file should be copied to:
api/core/tools/builtin_tool/providers/quiz_generator/tools/save_quiz_and_get_url.py

Usage:
1. Copy this entire dify_integration directory to api/core/tools/builtin_tool/providers/
2. Rename dify_integration to quiz_generator
3. Restart Dify service
"""

import logging
import requests
from typing import Any, Generator, Optional
from urllib.parse import urljoin

# These imports will work when the file is in the correct Dify location
try:
    from core.tools.builtin_tool.tool import BuiltinTool
    from core.tools.entities.tool_entities import ToolInvokeMessage
    from core.tools.errors import ToolInvokeError
except ImportError:
    # Fallback for when running outside of Dify
    class BuiltinTool:
        def create_text_message(self, text):
            return {"type": "text", "message": text}
    
    class ToolInvokeMessage:
        pass
    
    class ToolInvokeError(Exception):
        pass

logger = logging.getLogger(__name__)


class SaveQuizAndGetUrlTool(BuiltinTool):
    def _invoke(
        self,
        user_id: str,
        tool_parameters: dict[str, Any],
        conversation_id: Optional[str] = None,
        app_id: Optional[str] = None,
        message_id: Optional[str] = None,
    ) -> Generator[ToolInvokeMessage, None, None]:
        """
        Save quiz content and get URL
        
        :param user_id: the user id
        :param tool_parameters: the tool parameters
        :param conversation_id: the conversation id
        :param app_id: the app id
        :param message_id: the message id
        :return: the result
        """
        try:
            # Get quiz content from parameters
            content = tool_parameters.get('content', '')
            if not content:
                raise ToolInvokeError("Quiz content is required")
            
            # Get quiz service URL from credentials
            quiz_service_url = self.runtime.credentials.get('quiz_service_url', 'http://127.0.0.1:5006')
            
            # Ensure URL ends with /
            if not quiz_service_url.endswith('/'):
                quiz_service_url += '/'
            
            # Construct the upload endpoint
            upload_url = urljoin(quiz_service_url, 'upload_markdown')
            
            # Prepare request with proper headers and timeout
            headers = {
                'Content-Type': 'text/plain; charset=utf-8',
                'User-Agent': 'Dify-Quiz-Generator/1.0'
            }
            
            # Make the request with timeout and error handling
            try:
                response = requests.post(
                    upload_url,
                    data=content.encode('utf-8'),
                    headers=headers,
                    timeout=30,  # 30 second timeout
                    verify=False  # For local development, disable SSL verification
                )
                response.raise_for_status()
                
                # Parse response
                result = response.json()
                message = result.get('message', 'Quiz saved successfully')
                
                yield self.create_text_message(message)
                
            except requests.exceptions.Timeout:
                raise ToolInvokeError("Request to quiz service timed out. Please check if the service is running.")
            except requests.exceptions.ConnectionError:
                raise ToolInvokeError(f"Cannot connect to quiz service at {quiz_service_url}. Please check if the service is running.")
            except requests.exceptions.HTTPError as e:
                raise ToolInvokeError(f"HTTP error from quiz service: {e}")
            except requests.exceptions.RequestException as e:
                raise ToolInvokeError(f"Request error: {e}")
            except ValueError as e:
                raise ToolInvokeError(f"Invalid response from quiz service: {e}")
                
        except ToolInvokeError:
            raise
        except Exception as e:
            logger.exception(f"Unexpected error in save_quiz_and_get_url: {e}")
            raise ToolInvokeError(f"Unexpected error: {str(e)}")


# Standalone function for testing outside of Dify
def save_quiz_standalone(content: str, quiz_service_url: str = 'http://127.0.0.1:5006') -> dict:
    """
    Standalone function to save quiz content and get URL
    Can be used for testing without Dify
    """
    if not quiz_service_url.endswith('/'):
        quiz_service_url += '/'
    
    upload_url = urljoin(quiz_service_url, 'upload_markdown')
    
    headers = {
        'Content-Type': 'text/plain; charset=utf-8',
        'User-Agent': 'Quiz-Generator-Standalone/1.0'
    }
    
    response = requests.post(
        upload_url,
        data=content.encode('utf-8'),
        headers=headers,
        timeout=30
    )
    response.raise_for_status()
    
    return response.json()


if __name__ == "__main__":
    # Test the standalone function
    test_content = """# 测试试卷

1. 这是单选题？
- (x) 正确答案
- ( ) 错误答案

2. 这是多选题？
- [x] 正确答案1
- [x] 正确答案2
- [ ] 错误答案

3. 这是判断题。
- (x) 正确
- ( ) 错误"""
    
    try:
        result = save_quiz_standalone(test_content)
        print("测试成功:", result)
    except Exception as e:
        print("测试失败:", e)
