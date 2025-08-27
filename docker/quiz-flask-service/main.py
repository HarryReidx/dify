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

    # STEP 1: Convert radio-list to question-block (handles single choice and true/false)
    radio_pattern = re.compile(
        r'<ul class="radio-list"[^>]*data-question-id="([^"]+)"[^>]*>(.*?)</ul>(?:\s*</li>)?(?:\s*</ol>)?',
        re.MULTILINE | re.DOTALL
    )

    def convert_radio_question(match):
        question_id = match.group(1)
        content = match.group(2)

        # Extract question text from the first <li> that doesn't have class="option-item"
        question_text = ""

        # First try to find question text in <p> tags
        p_matches = re.findall(r'<p>([^<]+)</p>', content)
        if p_matches:
            question_text = p_matches[0].strip()
        else:
            # If no <p> tags, look for the first <li> without class="option-item"
            li_matches = re.findall(r'<li>([^<]+)</li>', content)
            if li_matches:
                question_text = li_matches[0].strip()

        # Extract all option items
        options = re.findall(r'<li class="option-item"[^>]*>.*?</li>', content, re.DOTALL)
        options_html = ''.join(options)

        if not question_text:
            question_text = "题目"

        return f'''<div class="question-block radio-question" data-question-id="{question_id}">
            <div class="question-text">{question_text}</div>
            <ul class="option-list radio-options">{options_html}</ul>
        </div>'''

    processed_html = radio_pattern.sub(convert_radio_question, processed_html)

    # STEP 1.2: Handle radio questions in ol format (similar to checkbox)
    radio_ol_pattern = re.compile(
        r'<ol>\s*<li>([^<]+)</li>\s*((?:<li class="option-item"[^>]*>.*?</li>\s*)+)</ol>',
        re.MULTILINE | re.DOTALL
    )

    def convert_radio_ol_question(match):
        question_text = match.group(1).strip()
        options_content = match.group(2)

        # Check if this contains radio inputs
        if 'type="radio"' in options_content:
            # Extract all option items
            options = re.findall(r'<li class="option-item"[^>]*>.*?</li>', options_content, re.DOTALL)
            options_html = ''.join(options)

            # Generate a unique question ID for radio grouping
            import time
            import random
            question_id = f"radio-question-{int(time.time() * 1000000)}-{random.randint(10000, 99999)}"

            # Update radio button names to use the same group
            import re as re_inner
            def update_radio_name(radio_match):
                return radio_match.group(0).replace('name="', f'name="{question_id}"')

            options_html = re_inner.sub(r'<input[^>]*type="radio"[^>]*name="[^"]*"[^>]*>', update_radio_name, options_html)

            return f'''<div class="question-block radio-question" data-question-id="{question_id}">
                <div class="question-text">{question_text}</div>
                <ul class="option-list radio-options">{options_html}</ul>
            </div>'''
        else:
            # Not a radio question, return original
            return match.group(0)

    processed_html = radio_ol_pattern.sub(convert_radio_ol_question, processed_html)

    # STEP 1.5: Convert checklist to question-block (handles multiple choice questions)
    # First, handle ol/ul that contains checkbox inputs (most common case)
    checkbox_ol_pattern = re.compile(
        r'<ol>\s*<li>([^<]+)</li>\s*((?:<li class="option-item"[^>]*>.*?</li>\s*)+)</ol>',
        re.MULTILINE | re.DOTALL
    )

    def convert_checkbox_ol_question(match):
        question_text = match.group(1).strip()
        options_content = match.group(2)

        # Check if this contains checkbox inputs
        if 'type="checkbox"' in options_content:
            # Extract all option items
            options = re.findall(r'<li class="option-item"[^>]*>.*?</li>', options_content, re.DOTALL)
            options_html = ''.join(options)

            return f'''<div class="question-block checklist-question">
                <div class="question-text">{question_text}</div>
                <ul class="option-list checklist">{options_html}</ul>
            </div>'''
        else:
            # Not a checkbox question, return original
            return match.group(0)

    processed_html = checkbox_ol_pattern.sub(convert_checkbox_ol_question, processed_html)

    # Then handle checklist within li elements
    li_checklist_pattern = re.compile(
        r'<li>\s*<p>([^<]+)</p>\s*<ul class="checklist"[^>]*>(.*?)</ul>\s*</li>',
        re.MULTILINE | re.DOTALL
    )

    def convert_li_checklist_question(match):
        question_text = match.group(1).strip()
        content = match.group(2)

        # Extract all option items
        options = re.findall(r'<li class="option-item"[^>]*>.*?</li>', content, re.DOTALL)
        options_html = ''.join(options)

        return f'''<div class="question-block checklist-question">
            <div class="question-text">{question_text}</div>
            <ul class="option-list checklist">{options_html}</ul>
        </div>'''

    processed_html = li_checklist_pattern.sub(convert_li_checklist_question, processed_html)

    # Finally handle standalone checklist (fallback)
    standalone_checklist_pattern = re.compile(
        r'<ul class="checklist"[^>]*>(.*?)</ul>(?:\s*</li>)?(?:\s*</ol>)?',
        re.MULTILINE | re.DOTALL
    )

    def convert_standalone_checklist_question(match):
        content = match.group(1)

        # Extract all option items
        options = re.findall(r'<li class="option-item"[^>]*>.*?</li>', content, re.DOTALL)
        options_html = ''.join(options)

        return f'''<div class="question-block checklist-question">
            <div class="question-text">题目</div>
            <ul class="option-list checklist">{options_html}</ul>
        </div>'''

    processed_html = standalone_checklist_pattern.sub(convert_standalone_checklist_question, processed_html)

    # STEP 2: Convert ol/li to question-block (handles multiple choice and fill-in-the-blank)
    ol_pattern = re.compile(r'<ol>(.*?)</ol>', re.MULTILINE | re.DOTALL)

    def convert_ol_questions(match):
        content = match.group(1)
        result = ""

        # Find li elements with nested ul
        li_pattern = re.compile(
            r'<li>\s*<p>([^<]+)</p>\s*<ul class="(checklist|textbox)"[^>]*>(.*?)</ul>\s*</li>',
            re.MULTILINE | re.DOTALL
        )

        for li_match in li_pattern.finditer(content):
            question_text = li_match.group(1).strip()
            list_class = li_match.group(2)
            options_content = li_match.group(3)

            # Extract option items
            options = re.findall(r'<li class="option-item[^"]*"[^>]*>.*?</li>', options_content, re.DOTALL)
            options_html = ''.join(options)

            result += f'''<div class="question-block">
                <div class="question-text">{question_text}</div>
                <ul class="option-list {list_class}">{options_html}</ul>
            </div>'''

        return result

    processed_html = ol_pattern.sub(convert_ol_questions, processed_html)

    # STEP 3: Handle remaining orphaned li elements with ul (not inside ol)
    orphaned_li_pattern = re.compile(
        r'<li>\s*<p>([^<]+)</p>\s*<ul class="(checklist|textbox)"[^>]*>(.*?)</ul>\s*</li>',
        re.MULTILINE | re.DOTALL
    )

    def convert_orphaned_li(match):
        question_text = match.group(1).strip()
        list_class = match.group(2)
        options_content = match.group(3)

        # Extract option items
        options = re.findall(r'<li class="option-item[^"]*"[^>]*>.*?</li>', options_content, re.DOTALL)
        options_html = ''.join(options)

        return f'''<div class="question-block">
            <div class="question-text">{question_text}</div>
            <ul class="option-list {list_class}">{options_html}</ul>
        </div>'''

    processed_html = orphaned_li_pattern.sub(convert_orphaned_li, processed_html)

    # STEP 4: Simple cleanup
    processed_html = re.sub(r'</li>\s*(?=<h[1-6])', '', processed_html)
    processed_html = re.sub(r'</ol>\s*(?=<h[1-6])', '', processed_html)
    processed_html = re.sub(r'<li>\s*<p>([^<]+)</p>\s*(?=<h[1-6])', '', processed_html)
    processed_html = re.sub(r'<li>\s*<p>([^<]+)</p>\s*(?=<div class="question-block")', '', processed_html)

    # Clean up extra whitespace
    processed_html = re.sub(r'\n\s*\n\s*\n+', '\n\n', processed_html)

    return processed_html

# 配置文件夹路径
UPLOAD_FOLDER = './markdown-quiz-files'
OUTPUT_FOLDER = 'data'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

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

        return jsonify({
            "message": f"保存成功\n查看链接http://127.0.0.1:5006/get_html/{filename}",
            "filename": filename,
            "url": f"http://127.0.0.1:5006/get_html/{filename}"
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
