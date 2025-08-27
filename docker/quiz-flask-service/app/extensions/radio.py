# stolen from: https://github.com/FND/markdown-checklist/blob/master/markdown_checklist/extension.py
import re

from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor
from markdown.postprocessors import Postprocessor


def makeExtension(configs=None):
    if configs is None:
        return RadioExtension()
    else:
        return RadioExtension(configs=configs)


class RadioExtension(Extension):

    def __init__(self, **kwargs):
        self.config = {
            "list_class": ["radio-list", "class name to add to the list element"],
            "render_item": [render_item, "custom function to render items"]
        }
        super().__init__(**kwargs)

    def extendMarkdown(self, md, md_globals):
        list_class = self.getConfig("list_class")
        renderer = self.getConfig("render_item")
        postprocessor = RadioPostprocessor(list_class, renderer, md)
        md.postprocessors.add("radio", postprocessor, ">raw_html")


class RadioPostprocessor(Postprocessor):
    """
    adds checklist class to list element
    """

    list_pattern = re.compile(r"(<[uo]l>\s*<li[^>]*>\s*\([ Xx]\))", re.MULTILINE | re.DOTALL)
    item_pattern = re.compile(r"<li[^>]*>\s*\(([ Xx])\)\s*(.*?)</li>", re.MULTILINE | re.DOTALL)
    # Also handle items that are wrapped in <p> tags
    p_item_pattern = re.compile(r"<li[^>]*>\s*<p[^>]*>\s*\(([ Xx])\)\s*(.*?)</p>\s*</li>", re.MULTILINE | re.DOTALL)

    def __init__(self, list_class, render_item, *args, **kwargs):
        self.list_class = list_class
        self.render_item = render_item
        self.question_counter = 0
        self.current_question_id = None
        super().__init__(*args, **kwargs)

    def run(self, html):
        import time
        import random

        # Find all lists that contain radio options
        radio_list_pattern = re.compile(r'<[uo]l>.*?</[uo]l>', re.MULTILINE | re.DOTALL)

        def process_potential_radio_list(match):
            list_content = match.group(0)

            # Check if this list contains radio options
            if re.search(r'\([xX ]\)', list_content):
                # Generate unique question ID for this list
                question_id = f"radio-question-{int(time.time() * 1000000)}-{random.randint(10000, 99999)}"

                # Convert to ul with class
                if "<ol>" in list_content:
                    list_content = list_content.replace('<ol>', f'<ul class="{self.list_class}" data-question-id="{question_id}">')
                    list_content = list_content.replace('</ol>', '</ul>')
                else:
                    list_content = re.sub(r'<ul>', f'<ul class="{self.list_class}" data-question-id="{question_id}">', list_content)

                # Convert radio items
                list_content = re.sub(r'<li>\s*\(([xX ])\)\s*(.*?)</li>',
                                    lambda m: self._convert_item_with_id(m, question_id),
                                    list_content)
                list_content = re.sub(r'<li>\s*<p>\s*\(([xX ])\)\s*(.*?)</p>\s*</li>',
                                    lambda m: self._convert_p_item_with_id(m, question_id),
                                    list_content)

                return list_content

            return list_content

        html = re.sub(radio_list_pattern, process_potential_radio_list, html)
        return html

    def _convert_list(self, match):
        list_tag = match.group(1)
        self.question_counter += 1
        import time
        import random
        self.current_question_id = f"radio-question-{self.question_counter}-{int(time.time() * 1000)}-{random.randint(1000, 9999)}"

        # Always convert to ul to avoid numbering
        if "<ul>" in list_tag:
            return list_tag.replace("<ul>", f"<ul class=\"{self.list_class}\" data-question-id=\"{self.current_question_id}\">")
        elif "<ol>" in list_tag:
            return list_tag.replace("<ol>", f"<ul class=\"{self.list_class}\" data-question-id=\"{self.current_question_id}\">")
        return list_tag

    def _convert_item(self, match):
        state, caption = match.groups()
        # Use the current question ID for all items in the same list
        return self.render_item(caption.strip(), state != " ", self.current_question_id)

    def _convert_p_item(self, match):
        state, caption = match.groups()
        # Use the current question ID for all items in the same list
        return self.render_item(caption.strip(), state != " ", self.current_question_id)

    def _convert_item_with_id(self, match, question_id):
        state, caption = match.groups()
        checked = state.lower() == 'x'
        return self.render_item(caption.strip(), checked, question_id)

    def _convert_p_item_with_id(self, match, question_id):
        state, caption = match.groups()
        checked = state.lower() == 'x'
        return self.render_item(caption.strip(), checked, question_id)


def render_item(caption, checked, question_id=None):
    correct = "1" if checked else "0"
    fake = "0" if checked else "1"

    # Generate a unique name for radio group if not provided
    if question_id is None:
        import time
        import random
        question_id = f"radio-{int(time.time() * 1000)}-{random.randint(1000, 9999)}"

    # Generate completely unique ID for each option
    import time
    import random
    unique_id = f"radio_{question_id}_{int(time.time() * 1000)}_{random.randint(10000, 99999)}"

    return f"<li class=\"option-item\">" \
           f"<input type=\"radio\" name=\"{question_id}\" data-question=\"{fake}\" data-content=\"{correct}\" id=\"{unique_id}\" />" \
           f"<label for=\"{unique_id}\">{caption.strip()}</label>" \
           f"</li>"
