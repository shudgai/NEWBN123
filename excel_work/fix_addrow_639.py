import sys

filepath = 'resources/views/client_639.blade.php'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_payload = """                        weight: newRow.value.weight || 0,
                        forklift_fee: newRow.value.forklift_fee || 0,
                        remark: newRow.value.remark || '',"""
new_payload = """                        weight: newRow.value.weight || 0,
                        forklift_fee: newRow.value.forklift_fee || 0,
                        location: newRow.value.location || '',
                        remark: newRow.value.remark || '',"""
content = content.replace(old_payload, new_payload)

old_reset = """                        newRow.value.weight = null;
                        newRow.value.forklift_fee = null;
                        newRow.value.remark = '';"""
new_reset = """                        newRow.value.weight = null;
                        newRow.value.forklift_fee = null;
                        newRow.value.location = '';
                        newRow.value.remark = '';"""
content = content.replace(old_reset, new_reset)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed addRow for location in 639")
