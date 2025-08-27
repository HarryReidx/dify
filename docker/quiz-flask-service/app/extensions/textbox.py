# stolen from: https://github.com/FND/markdown-checklist/blob/master/markdown_checklist/extension.py
import re

from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor
from markdown.postprocessors import Postprocessor


def makeExtension(configs=None):
    if configs is None:
        return TextboxExtension()
    else:
        return TextboxExtension(configs=configs)


class TextboxExtension(Extension):

    def __init__(self, **kwargs):
        self.config = {
            "list_class": ["textbox", "class name to add to the list element"],
            "render_item": [render_item, "custom function to render items"]
        }
        super().__init__(**kwargs)

    def extendMarkdown(self, md, md_globals):
        list_class = self.getConfig("list_class")
        renderer = self.getConfig("render_item")
        postprocessor = TextboxPostprocessor(list_class, renderer, md)
        md.postprocessors.add("textbox", postprocessor, ">raw_html")


class TextboxPostprocessor(Postprocessor):
    """
    adds textbox class to list element
    """

    list_pattern = re.compile(r"(<[uo]l>\s*<li[^>]*>\s*[Rr]:=)", re.MULTILINE | re.DOTALL)
    item_pattern = re.compile(r"<li[^>]*>\s*([Rr]:=)\s*(.*?)</li>", re.MULTILINE | re.DOTALL)
    # Also handle items that are wrapped in <p> tags
    p_item_pattern = re.compile(r"<li[^>]*>\s*<p[^>]*>\s*([Rr]:=)\s*(.*?)</p>\s*</li>", re.MULTILINE | re.DOTALL)

    def __init__(self, list_class, render_item, *args, **kwargs):
        self.list_class = list_class
        self.render_item = render_item
        super().__init__(*args, **kwargs)

    def run(self, html):
        html = re.sub(self.list_pattern, self._convert_list, html)
        html = re.sub(self.item_pattern, self._convert_item, html)
        html = re.sub(self.p_item_pattern, self._convert_p_item, html)
        return html

    def _convert_list(self, match):
        list_tag = match.group(1)
        # Always convert to ul to avoid numbering
        if "<ul>" in list_tag:
            return list_tag.replace("<ul>", f"<ul class=\"{self.list_class}\">")
        elif "<ol>" in list_tag:
            return list_tag.replace("<ol>", f"<ul class=\"{self.list_class}\">")
        return list_tag

    def _convert_item(self, match):
        state, caption = match.groups()
        return self.render_item(caption.strip(), state != " ")

    def _convert_p_item(self, match):
        state, caption = match.groups()
        return self.render_item(caption.strip(), state != " ")


def render_item(caption: str, value):
    # the correct answer next to another false one are saved in an attribute such as meta-data written backwards.
    correct = caption.strip()[::-1]
    fake = "".join([c + 's' for c in correct])

    # Generate completely unique ID for textbox
    import time
    import random
    import uuid
    unique_id = f"textbox_{int(time.time() * 1000000)}_{random.randint(100000, 999999)}_{uuid.uuid4().hex[:8]}"

    return f"<li class=\"option-item textbox-item\">" \
           f"<input type=\"text\" data-content=\"{correct}\" data-question=\"{fake}\" " \
           f"placeholder=\"请输入正确答案\" class=\"form-control text-input\" id=\"{unique_id}\" />" \
           f"</li>"
