import sys

filepath = '/home/shudgai999/.gemini/antigravity-ide/brain/89f55dc5-436b-4262-8ee0-e019ca7ede4d/task.md'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('`[/]`', '`[x]`')
content = content.replace('`[ ]`', '`[x]`')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated tasks")
