import glob
import re

def fix_all():
    files = glob.glob('/home/shudgai999/project/excel_work/resources/views/client_*.blade.php')
    
    for filepath in files:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Fix issue 2: Do not clear location
        if "newRow.value.location = '';" in content:
            content = content.replace("newRow.value.location = '';", "// newRow.value.location = '';")
            print(f"Fixed location clearing in {filepath}")

        # Fix issue 1: Remove M月D日 formatting from client_206
        if 'client_206.blade.php' in filepath:
            # Remove from addRow
            add_row_date = """if (newRow.value.date) {
                    newRow.value.date = parseAndFormatDate(newRow.value.date);
                }"""
            if add_row_date in content:
                content = content.replace(add_row_date, "")
                
            # Remove from updateRow
            content = content.replace("row.date = parseAndFormatDate(row.date);", "")
            
            # Remove parseAndFormatDate function and formatNewDate
            funcs = """const formatNewDate = () => {
                newRow.value.date = parseAndFormatDate(newRow.value.date);
            };

            const parseAndFormatDate = (dateStr) => {
                if (!dateStr || typeof dateStr !== 'string') return dateStr;
                let m = null, d = null;
                const slashMatch = dateStr.match(/^(\d{1,2})[\/\-](\d{1,2})$/);
                if (slashMatch) {
                    m = parseInt(slashMatch[1], 10);
                    d = parseInt(slashMatch[2], 10);
                } else if (/^\d{3,4}$/.test(dateStr)) {
                    if (dateStr.length === 4) {
                        m = parseInt(dateStr.substring(0, 2), 10);
                        d = parseInt(dateStr.substring(2, 4), 10);
                    } else if (dateStr.length === 3) {
                        m = parseInt(dateStr.substring(0, 1), 10);
                        d = parseInt(dateStr.substring(1, 3), 10);
                    }
                }
                if (m !== null && d !== null && m >= 1 && m <= 12 && d >= 1 && d <= 31) {
                    return `${m}月${d}日`;
                }
                return dateStr;
            };"""
            
            # Since formatting might differ, we can use regex to remove parseAndFormatDate block
            content = re.sub(r'const formatNewDate = \(\) => \{[\s\S]*?const parseAndFormatDate = \(dateStr\) => \{[\s\S]*?return dateStr;\n\s*\};\n', '', content)
            
            # Remove @change="formatNewDate"
            content = content.replace('@change="formatNewDate" ', '')
            
            print(f"Reverted date formatting for {filepath}")

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

if __name__ == '__main__':
    fix_all()
