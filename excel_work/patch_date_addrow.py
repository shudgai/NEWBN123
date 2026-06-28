import glob

def patch_addrow():
    files = glob.glob('/home/shudgai999/project/excel_work/resources/views/client_*.blade.php')
    for filepath in files:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Some files might have `const addRow = async () => {`
        target_str = "const addRow = async () => {"
        replacement_str = """const addRow = async () => {
                if (newRow.value.date) {
                    newRow.value.date = parseAndFormatDate(newRow.value.date);
                }"""

        if replacement_str not in content:
            content = content.replace(target_str, replacement_str)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Patched {filepath}")

if __name__ == '__main__':
    patch_addrow()
