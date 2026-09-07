import glob
import re

files = glob.glob('/home/shudgai999/project/excel_work/resources/views/client_*.blade.php')

new_regex_code = """                let vehicles = [];
                const vehicleRegex = /(3\.49|6\.8|8\.8|10\.5|15|17)噸(?:車)?\s*(?:[*xX]\s*(\d+))?/g;
                let match;
                while ((match = vehicleRegex.exec(r)) !== null) {
                    let count = match[2] ? parseInt(match[2], 10) : 1;
                    for (let i = 0; i < count; i++) {
                        vehicles.push(match[1]);
                    }
                }"""

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find where 'let vehicle = null;' starts
    start_idx = content.find('let vehicle = null;')
    if start_idx != -1:
        # Find where 'vehicle = '17';' ends
        end_idx = content.find("vehicle = '17';", start_idx)
        if end_idx != -1:
            end_idx += len("vehicle = '17';")
            
            old_block = content[start_idx:end_idx]
            content = content.replace(old_block, new_regex_code)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Patched single-vehicle logic in {filepath}")
