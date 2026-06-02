with open('test.js', 'r') as f:
    text = f.read()

stack = []
for i, c in enumerate(text):
    if c == '{': stack.append(('{', i))
    elif c == '(': stack.append(('(', i))
    elif c == '[': stack.append(('[', i))
    elif c == '}':
        if stack and stack[-1][0] == '{': stack.pop()
        else: print(f"Unexpected }} at index {i}, context: {text[i-20:i+20]}"); break
    elif c == ')':
        if stack and stack[-1][0] == '(': stack.pop()
        else: print(f"Unexpected ) at index {i}, context: {text[i-20:i+20]}"); break
    elif c == ']':
        if stack and stack[-1][0] == '[': stack.pop()
        else: print(f"Unexpected ] at index {i}, context: {text[i-20:i+20]}"); break

if stack:
    print(f"Unclosed braces: {[(c, text[i-10:i+20]) for c, i in stack]}")
