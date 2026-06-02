import re

for client in ['225', '276', '444', '639']:
    filepath = f'resources/views/client_{client}.blade.php'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Fix getCellStyle
    # We are looking for:
    # if (!row || !row.styles || !row.styles[colIndex]) return {,
    #     sortState,
    #     resetView,
    #     sortBy,
    #     isAmountManual,
    #     recalculateAndSave
    # };
    
    bad_pattern = re.compile(r'if \(!row \|\| !row\.styles \|\| !row\.styles\[colIndex\]\) return \{,.*?recalculateAndSave\n\s*\};\n', re.DOTALL)
    content = bad_pattern.sub(r'if (!row || !row.styles || !row.styles[colIndex]) return {};\n', content)
    
    # Also some files might not have isAmountManual in the bad block, let's use a broader regex if needed
    bad_pattern_broad = re.compile(r'if \(!row \|\| !row\.styles \|\| !row\.styles\[colIndex\]\) return \{,\n\s*sortState,.*?};\n', re.DOTALL)
    content = bad_pattern_broad.sub(r'if (!row || !row.styles || !row.styles[colIndex]) return {};\n', content)

    # 2. Add missing variables to the FINAL return block
    # The final return block looks like "return { .... };" before "}" of setup()
    # Let's find the last "return {"
    last_return_idx = content.rfind('return {')
    if last_return_idx != -1:
        end_brace_idx = content.find('};', last_return_idx)
        if end_brace_idx != -1:
            returns = content[last_return_idx:end_brace_idx]
            
            added = []
            for var in ['sortState', 'resetView', 'sortBy', 'isAmountManual', 'recalculateAndSave']:
                if var not in returns:
                    added.append(var)
                    
            if added:
                new_returns = returns.rstrip() + ',\n                ' + ',\n                '.join(added) + '\n            '
                content = content[:last_return_idx] + new_returns + content[end_brace_idx:]
                
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Fixed {filepath}")
