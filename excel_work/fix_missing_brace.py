import re
import sys

files = ['225', '276', '444', '639']
for client in files:
    filepath = f'resources/views/client_{client}.blade.php'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # The missing brace is at the end of the styling loop in exportExcel, right before const wb = XLSX.utils.book_new();
    # Let's find exactly the pattern that's currently there.
    
    old_pattern = """                            if (Object.keys(ws[cell_ref].s.border).length === 0) {
                                delete ws[cell_ref].s.border;
                            }
                    }
                }
                
                const wb = XLSX.utils.book_new();"""
                
    new_pattern = """                            if (Object.keys(ws[cell_ref].s.border).length === 0) {
                                delete ws[cell_ref].s.border;
                            }
                        }
                    }
                }
                
                const wb = XLSX.utils.book_new();"""

    if old_pattern in content:
        content = content.replace(old_pattern, new_pattern)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed missing brace in {filepath}")
    else:
        print(f"Pattern not found in {filepath} (maybe already fixed or different formatting?)")

