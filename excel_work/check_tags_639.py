import sys
from html.parser import HTMLParser

class MyHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []

    def handle_starttag(self, tag, attrs):
        if tag not in ['input', 'br', 'hr', 'img', 'meta', 'link', 'path']:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag not in ['input', 'br', 'hr', 'img', 'meta', 'link', 'path']:
            if not self.stack:
                print(f"Error: closing tag </{tag}> with empty stack")
                sys.exit(1)
            last = self.stack.pop()
            if last != tag:
                print(f"Error: unmatched tag </{tag}>, expected </{last}>")
                sys.exit(1)

parser = MyHTMLParser()
with open('resources/views/client_639.blade.php', 'r', encoding='utf-8') as f:
    parser.feed(f.read())

if parser.stack:
    print(f"Error: unclosed tags {parser.stack}")
else:
    print("Tags are balanced!")
