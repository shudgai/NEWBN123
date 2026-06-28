import re

def patch_206():
    filepath = '/home/shudgai999/project/excel_work/resources/views/client_206.blade.php'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Add formatNewDate to new row input
    if '@change="formatNewDate"' not in content:
        content = content.replace(
            'v-model.trim="newRow.date" class="nav-input w-full border p-1" placeholder="日期"',
            '@change="formatNewDate" v-model.trim="newRow.date" class="nav-input w-full border p-1" placeholder="日期"'
        )

    # Insert parseAndFormatDate function and formatNewDate before newRow definition
    funcs_to_add = """
            const formatNewDate = () => {
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
            };

            const newRow = ref({"""

    if 'const parseAndFormatDate = (dateStr) => {' not in content:
        content = content.replace('const newRow = ref({', funcs_to_add)

    # In updateRow, add formatting before payload
    update_row_mod = """const updateRow = async (row) => {
                row.date = parseAndFormatDate(row.date);
                try {"""
    
    if 'row.date = parseAndFormatDate(row.date);' not in content:
        content = content.replace(
            """const updateRow = async (row) => {
                try {""",
            update_row_mod
        )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched client_206.blade.php")

if __name__ == '__main__':
    patch_206()
