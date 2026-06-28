import os
import glob
import re

def patch_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if '_calculateFreight' in content:
        print(f"Already patched {filepath}")
        return

    # Check for signature 1
    if "const calculateFreight = (weight, remark, client) => {" in content:
        content = content.replace(
            "const calculateFreight = (weight, remark, client) => {",
            """const calculateFreight = (weight, remark, client) => {
                let amt = _calculateFreight(weight, remark, client);
                if (amt > 0 && remark && remark.includes('+尾門')) {
                    amt += 500;
                }
                return amt;
            };

            const _calculateFreight = (weight, remark, client) => {"""
        )
    elif "const calculateFreight = (weight, remark) => {" in content:
        content = content.replace(
            "const calculateFreight = (weight, remark) => {",
            """const calculateFreight = (weight, remark) => {
                let amt = _calculateFreight(weight, remark);
                if (amt > 0 && remark && remark.includes('+尾門')) {
                    amt += 500;
                }
                return amt;
            };

            const _calculateFreight = (weight, remark) => {"""
        )
    else:
        print(f"Could not find calculateFreight signature in {filepath}")
        return

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Patched {filepath}")

if __name__ == '__main__':
    files = glob.glob('/home/shudgai999/project/excel_work/resources/views/client_*.blade.php')
    for file in files:
        patch_file(file)
