import os
import re

clients = ['206', '225', '276', '282', '444', '639']

for code in clients:
    filepath = f"resources/views/client_{code}.blade.php"
    if not os.path.exists(filepath):
        continue
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. uniqueClientNames
    if 'Array.from(names).sort()' in content:
        content = content.replace(
            'Array.from(names).sort()',
            "Array.from(names).sort((a, b) => a.localeCompare(b, 'zh-TW', { collation: 'stroke' }))"
        )
        
    # 2. uniqueLocations
    if 'Array.from(locs).sort()' in content:
        content = content.replace(
            'Array.from(locs).sort()',
            "Array.from(locs).sort((a, b) => a.localeCompare(b, 'zh-TW', { collation: 'stroke' }))"
        )
        
    # 3. sortBy function
    old_cmp = """                    if (typeof valA === 'number' && typeof valB === 'number') {
                        cmp = valA - valB;
                    } else {
                        cmp = valA.toString().localeCompare(valB.toString(), undefined, { numeric: true, sensitivity: 'base' });
                    }"""
    
    new_cmp = """                    if (typeof valA === 'number' && typeof valB === 'number') {
                        cmp = valA - valB;
                    } else {
                        if (column === 'client_name' || column === 'location') {
                            cmp = valA.toString().localeCompare(valB.toString(), 'zh-TW', { collation: 'stroke' });
                        } else {
                            cmp = valA.toString().localeCompare(valB.toString(), undefined, { numeric: true, sensitivity: 'base' });
                        }
                    }"""
    
    if old_cmp in content:
        content = content.replace(old_cmp, new_cmp)
        
    # In case there are subtle whitespace differences, we can use regex
    if 'cmp = valA.toString().localeCompare(valB.toString(), undefined, { numeric: true, sensitivity: \'base\' });' in content and 'column === \'client_name\'' not in content:
        content = re.sub(
            r'cmp = valA\.toString\(\)\.localeCompare\(valB\.toString\(\), undefined, \{ numeric: true, sensitivity: \'base\' \} \);',
            r"if (column === 'client_name' || column === 'location') {\n                            cmp = valA.toString().localeCompare(valB.toString(), 'zh-TW', { collation: 'stroke' });\n                        } else {\n                            cmp = valA.toString().localeCompare(valB.toString(), undefined, { numeric: true, sensitivity: 'base' });\n                        }",
            content
        )
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

print("Patch applied.")
