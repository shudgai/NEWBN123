import os
import re

clients = ['206', '225', '276', '282', '444', '639']

for code in clients:
    filepath = f"resources/views/client_{code}.blade.php"
    if not os.path.exists(filepath):
        continue
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Apply uniqueClientNames
    if 'const names = new Set();' in content:
        content = content.replace(
            'const names = new Set();',
            'const names = new Set(dbSavedClients.value);'
        )
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

print("Patch2 applied.")
