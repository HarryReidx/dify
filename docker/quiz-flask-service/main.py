from flask import Flask, request, send_from_directory, jsonify
from flask_cors import CORS
import os
import markdown
import time
import logging
import threading
import re
from jinja2 import Environment, PackageLoader, select_autoescape

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests

# Thread lock for file operations
file_lock = threading.Lock()


def post_process_quiz_html(html):
    """
    Post-process the HTML to fix quiz structure issues
    """
    # Remove horizontal rules (hr tags) that separate questions
    processed_html = re.sub(r'<hr\s*/?>', '', html)

    # Step 1: Handle radio questions (single choice) - fix radio button grouping
    radio_pattern = re.compile(
        r'<div class="question-block radio-question"[^>]*>\s*'
        r'<div class="question-text">([^<]+)</div>\s*'
        r'<ul class="option-list radio-options">(.*?)</ul>\s*'
        r'</div>',
        re.MULTILINE | re.DOTALL
    )

    def fix_radio_question(match):
        question_text = match.group(1).strip()
        options_content = match.group(2)
        
        # Generate unique question ID for radio grouping
        import time
        import random
        question_id = f"radio-question-{int(time.time() * 1000000)}-{random.randint(10000, 99999)}"
        
        # Update all radio buttons to use the same name (group)
        def update_radio_name(radio_match):
            return re.sub(r'name="[^"]*"', f'name="{question_id}"', radio_match.group(0))
        
        fixed_options = re.sub(r'<input[^>]*type="radio"[^>]*>', update_radio_name, options_content)
        
        return f'''<div class="question-block radio-question" data-question-id="{question_id}">
            <div class="question-text">{question_text}</div>
            <ul class="option-list radio-options">{fixed_options}</ul>
        </div>'''

    processed_html = radio_pattern.sub(fix_radio_question, processed_html)

    # Step 2: Handle checkbox questions (multiple choice) - convert ol/li to question-blocks
    # Pattern to match the entire ol block containing checkbox questions
    ol_pattern = re.compile(
        r'<ol>\s*(.*?)\s*</ol>',
        re.MULTILINE | re.DOTALL
    )

    def convert_ol_to_questions(match):
        ol_content = match.group(1)
        
        # Split content into individual questions and their options
        # Look for question text followed by option items
        questions = []
        current_question = None
        current_options = []
        
        # Split by li tags and process each
        li_items = re.findall(r'<li[^>]*>(.*?)</li>', ol_content, re.DOTALL)
        
        for li_content in li_items:
            # Check if this li contains a checkbox input (it's an option)
            if 'type="checkbox"' in li_content:
                current_options.append(f'<li class="option-item">{li_content}</li>')
            else:
                # This is a question text
                if current_question and current_options:
                    # Save previous question
                    questions.append((current_question, current_options))
                
                # Start new question
                # Extract text from p tag if present, otherwise use the content directly
                question_match = re.search(r'<p>([^<]+)</p>', li_content)
                if question_match:
                    current_question = question_match.group(1).strip()
                else:
                    current_question = re.sub(r'<[^>]+>', '', li_content).strip()
                current_options = []
        
        # Don't forget the last question
        if current_question and current_options:
            questions.append((current_question, current_options))
        
        # Convert each question to a question-block
        result = ""
        for question_text, options in questions:
            options_html = ''.join(options)
            result += f'''<div class="question-block checklist-question">
                <div class="question-text">{question_text}</div>
                <ul class="option-list checklist">{options_html}</ul>
            </div>'''
        
        return result

    processed_html = ol_pattern.sub(convert_ol_to_questions, processed_html)

    # Clean up extra whitespace
    processed_html = re.sub(r'\n\s*\n\s*\n+', '\n\n', processed_html)

    return processed_html

# 配置文件夹路径
UPLOAD_FOLDER = './markdown-quiz-files'
OUTPUT_FOLDER = 'data'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

# 配置服务器地址和端口
QUIZ_SERVICE_HOST = os.environ.get('QUIZ_SERVICE_HOST', '127.0.0.1')
QUIZ_SERVICE_PORT = os.environ.get('QUIZ_SERVICE_PORT', '5006')
QUIZ_SERVICE_PROTOCOL = os.environ.get('QUIZ_SERVICE_PROTOCOL', 'http')

# 确保文件夹存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


@app.route('/upload_markdown', methods=['POST'])
def upload_markdown():
    try:
        # Get content from request
        content = request.get_data(as_text=True)
        logger.info(f"Received content length: {len(content) if content else 0}")

        if not content or content.strip() == "":
            return jsonify({"error": "Invalid input: content is empty"}), 400

        # Use thread lock to prevent concurrent file operations
        with file_lock:
            """Render quiz in Markdown format to HTML."""
            extensions = [
                "tables", "app.extensions.checkbox", "app.extensions.radio",
                "app.extensions.textbox"
            ]

            try:
                html = markdown.markdown(content,
                                       extensions=extensions,
                                       output_format="html5")

                # Post-process HTML to fix list structure issues
                html = post_process_quiz_html(html)

            except Exception as e:
                logger.error(f"Markdown conversion error: {e}")
                return jsonify({"error": f"Markdown conversion failed: {str(e)}"}), 500

            try:
                env = Environment(loader=PackageLoader('app', 'static'),
                                autoescape=select_autoescape(['html', 'xml']))
                javascript = env.get_template('app.js').render()
                test_html = env.get_template('base.html').render(content=html,
                                                               javascript=javascript)
                test_html = env.get_template('wrapper.html').render(content=test_html)
            except Exception as e:
                logger.error(f"Template rendering error: {e}")
                return jsonify({"error": f"Template rendering failed: {str(e)}"}), 500

            # Generate unique filename
            filename = str(int(time.time() * 1000))  # Use milliseconds for better uniqueness
            file_path = os.path.join(OUTPUT_FOLDER, f"{filename}.html")

            try:
                with open(file_path, "w+", encoding='utf-8') as f:
                    f.write(test_html)
                logger.info(f"Successfully saved file: {filename}.html")
            except Exception as e:
                logger.error(f"File write error: {e}")
                return jsonify({"error": f"File write failed: {str(e)}"}), 500

        # 构建可访问的URL
        quiz_url = f"{QUIZ_SERVICE_PROTOCOL}://{QUIZ_SERVICE_HOST}:{QUIZ_SERVICE_PORT}/get_html/{filename}"

        return jsonify({
            "message": f"保存成功\n查看链接{quiz_url}",
            "filename": filename,
            "url": quiz_url
        }), 200

    except Exception as e:
        logger.error(f"Unexpected error in upload_markdown: {e}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route('/get_html/<filename>', methods=['GET'])
def get_html(filename):
    try:
        # Sanitize filename
        if not filename.endswith('.html'):
            filename += '.html'

        # Prevent directory traversal attacks
        filename = os.path.basename(filename)

        file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)

        if not os.path.exists(file_path):
            logger.warning(f"File not found: {filename}")
            return jsonify({"error": "File not found"}), 404

        logger.info(f"Serving file: {filename}")
        return send_from_directory(app.config['OUTPUT_FOLDER'], filename)

    except Exception as e:
        logger.error(f"Error serving file {filename}: {e}")
        return jsonify({"error": f"Error serving file: {str(e)}"}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": time.time()}), 200


if __name__ == '__main__':
    app.run(debug=True, port=5006, host='0.0.0.0')