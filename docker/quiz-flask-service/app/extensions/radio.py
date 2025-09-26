# stolen from: https://github.com/FND/markdown-checklist
# -*- coding: utf-8 -*-

import re
import markdown
from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor
from markdown.postprocessors import Postprocessor
import time
import random


class RadioExtension(Extension):
    def extendMarkdown(self, md):
        md.preprocessors.register(RadioPreprocessor(md), 'radio', 175)
        md.postprocessors.register(RadioPostprocessor(md), 'radio', 175)


class RadioPreprocessor(Preprocessor):
    def run(self, lines):
        new_lines = []
        for line in lines:
            # Convert radio button syntax to markdown list
            if re.match(r'^\s*-\s*\([x ]\)', line):
                new_lines.append(line)
            else:
                new_lines.append(line)
        return new_lines


class RadioPostprocessor(Postprocessor):
    def run(self, text):
        # Pattern to match both ul and ol lists containing radio buttons
        list_pattern = re.compile(
            r'<(ul|ol)>\s*((?:<li>.*?</li>\s*)+)</\1>',
            re.MULTILINE | re.DOTALL
        )
        
        def process_list(match):
            list_tag = match.group(1)
            list_content = match.group(2)
            
            # Check if this list contains radio buttons
            if not re.search(r'\(\s*[x ]\s*\)', list_content):
                return match.group(0)  # Not a radio list, return unchanged
            
            # Split into individual list items
            items = re.findall(r'<li>(.*?)</li>', list_content, re.DOTALL)
            
            result_parts = []
            current_question = None
            current_options = []
            
            i = 0
            while i < len(items):
                item_content = items[i].strip()
                
                # Remove <p> tags from content for easier processing
                clean_content = re.sub(r'</?p[^>]*>', '', item_content)
                
                # Check if this item contains a radio button
                radio_match = re.search(r'\(\s*([x ])\s*\)\s*(.+)', clean_content)
                
                if radio_match:
                    # This is a radio option
                    state = radio_match.group(1).strip()
                    caption = radio_match.group(2).strip()
                    
                    if current_question is None:
                        # No current question, this shouldn't happen but handle gracefully
                        current_question = "题目"
                    
                    # Generate question ID if we don't have one
                    if not hasattr(self, '_current_question_id'):
                        self._current_question_id = f"radio-question-{int(time.time() * 1000000)}-{random.randint(10000, 99999)}"
                    
                    option_html = render_item(caption, state.lower() == 'x', self._current_question_id)
                    current_options.append(option_html)
                    
                else:
                    # This is a question text
                    if current_question is not None and current_options:
                        # We have a previous question with options, output it
                        question_id = f"radio-question-{int(time.time() * 1000000)}-{random.randint(10000, 99999)}"
                        result_parts.append(self._create_question_block(current_question, current_options, question_id))
                        current_options = []
                    
                    # Extract question text
                    question_text = clean_content
                    current_question = question_text.strip()
                    
                    # Generate new question ID for this question
                    self._current_question_id = f"radio-question-{int(time.time() * 1000000)}-{random.randint(10000, 99999)}"
                
                i += 1
            
            # Handle the last question if any
            if current_question is not None and current_options:
                question_id = f"radio-question-{int(time.time() * 1000000)}-{random.randint(10000, 99999)}"
                result_parts.append(self._create_question_block(current_question, current_options, question_id))
            
            return ''.join(result_parts)
        
        return list_pattern.sub(process_list, text)
    
    def _create_question_block(self, question_text, options, question_id):
        options_html = ''.join(options)
        return f'''<div class="question-block radio-question" data-question-id="{question_id}">
            <div class="question-text">{question_text}</div>
            <ul class="option-list radio-options">{options_html}</ul>
        </div>'''


def render_item(caption, checked, question_id=None):
    # 保存正确答案信息但不预选
    correct = "1" if checked else "0"
    fake = "0" if checked else "1"

    # Generate a unique name for radio group if not provided
    if question_id is None:
        question_id = f"radio-{int(time.time() * 1000)}-{random.randint(1000, 9999)}"

    # Generate completely unique ID for each option
    unique_id = f"radio_{question_id}_{int(time.time() * 1000)}_{random.randint(10000, 99999)}"

    # 不预选任何选项，让用户自己选择
    # checked_attr = ' checked="checked"' if checked else ''

    return f"<li class=\"option-item\">" \
           f"<input type=\"radio\" name=\"{question_id}\" data-question=\"{fake}\" data-content=\"{correct}\" id=\"{unique_id}\" />" \
           f"<label for=\"{unique_id}\">{caption.strip()}</label>" \
           f"</li>"


def makeExtension(**kwargs):
    return RadioExtension(**kwargs)