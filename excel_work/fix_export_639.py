import sys

filepath = 'resources/views/client_639.blade.php'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix header array
old_header = '["日期", "客戶名稱", "提單號碼", "箱數", "重量", "金額", "堆高機", "備註"]'
new_header = '["日期", "客戶名稱", "提單號碼", "箱數", "重量", "金額", "堆高機", "地點", "備註"]'
content = content.replace(old_header, new_header)

# Fix rows pushing
old_rows = """                        row.amount || '',
                        row.forklift_fee || '',
                        row.remark || ''"""
new_rows = """                        row.amount || '',
                        row.forklift_fee || '',
                        row.location || '',
                        row.remark || ''"""
content = content.replace(old_rows, new_rows)

# Fix total amount row offset
old_total = 'aoa.push(["總計", "", "", "", "", totalAmount.value, "", ""]);'
new_total = 'aoa.push(["總計", "", "", "", "", totalAmount.value, "", "", ""]);'
content = content.replace(old_total, new_total)

# Fix cols
old_cols = """                    { wch: 15 }, // Amount
                    { wch: 18 }, // Location
                    { wch: 30 }  // Remark"""
new_cols = """                    { wch: 15 }, // Amount
                    { wch: 15 }, // Forklift
                    { wch: 18 }, // Location
                    { wch: 30 }  // Remark"""
content = content.replace(old_cols, new_cols)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated exportExcel for 639")
