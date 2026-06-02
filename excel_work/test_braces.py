import sys

def check_braces(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    stack = []
    lines = content.split('\n')
    
    for line_idx, line in enumerate(lines):
        # Extremely basic brace counting (ignores strings/comments for a rough check)
        for char_idx, char in enumerate(line):
            if char in '{[(':
                stack.append((char, line_idx + 1))
            elif char in '}])':
                if not stack:
                    print(f"Error: unmatched {char} at line {line_idx + 1}")
                    return
                top, top_line = stack.pop()
                pairs = {'}': '{', ']': '[', ')': '('}
                if pairs[char] != top:
                    print(f"Error: mismatched {top} (line {top_line}) and {char} (line {line_idx + 1})")
                    return

    if stack:
        print("Unmatched opening brackets:")
        for b, l in stack:
            print(f"  {b} at line {l}")
    else:
        print("All matched!")

check_braces('test.js')
