import glob
import re

files = glob.glob('/home/shudgai999/project/excel_work/resources/views/client_*.blade.php')

count_patched = 0
for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Update existing vehicleRegex (for files that already have it)
    old_regex_code = """let vehicles = [];
                const vehicleRegex = /(3\.49|6\.8|8\.8|10\.5|15|17)噸/g;
                let match;
                while ((match = vehicleRegex.exec(r)) !== null) {
                    vehicles.push(match[1]);
                }"""
    
    new_regex_code = """let vehicles = [];
                const vehicleRegex = /(3\.49|6\.8|8\.8|10\.5|15|17)噸(?:車)?\s*(?:[*xX]\s*(\d+))?/g;
                let match;
                while ((match = vehicleRegex.exec(r)) !== null) {
                    let count = match[2] ? parseInt(match[2], 10) : 1;
                    for (let i = 0; i < count; i++) {
                        vehicles.push(match[1]);
                    }
                }"""
    
    if old_regex_code in content:
        content = content.replace(old_regex_code, new_regex_code)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        count_patched += 1
        print(f"Patched existing multi-vehicle regex in {filepath}")
    else:
        # Check if it has the older single vehicle logic
        if "if (r.match(/3\.49噸/)) vehicle = '3.49';" in content and "let vehicle = null;" in content:
            # We need to replace it. But I previously found it failed on some files because of variations.
            # I'll just write a dynamic regex replacement if needed. For now, let's see.
            pass

print(f"Total patched: {count_patched}")
