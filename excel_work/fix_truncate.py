import sys
import re

files = ['206', '225', '276', '444', '639']
for client in files:
    filepath = f'resources/views/client_{client}.blade.php'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Find the fetch line in clearAllData
    # It looks like: const response = await fetch('/api/waybills/truncate?client_code=225', {
    # Or for 206: const response = await fetch('/api/waybills/truncate', {
    
    pattern = r"fetch\('/api/waybills/truncate(\?client_code=\d+)?'"
    replacement = f"fetch('/api/waybills/truncate?client_code={client}'"
    
    if re.search(pattern, content):
        content = re.sub(pattern, replacement, content)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed truncate for {filepath}")
    else:
        print(f"Could not find truncate in {filepath}")
