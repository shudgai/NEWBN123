import sys
import re

filepath = 'resources/views/client_276.blade.php'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update recalculateAndSave (single row)
old1 = "const textToCheck = (row.location || '') + ' ' + (row.remark || '');"
new1 = "const textToCheck = (row.client_name || '') + ' ' + (row.location || '') + ' ' + (row.remark || '');"
content = content.replace(old1, new1)

# 2. Update recalculateAndSave and previewFreight (grouped rows)
old2 = "combinedText += (r.location || '') + ' ' + (r.remark || '') + ' ';"
new2 = "combinedText += (r.client_name || '') + ' ' + (r.location || '') + ' ' + (r.remark || '') + ' ';"
content = content.replace(old2, new2)

# 3. Update handlePaste
old3 = "const textToCheck = (targetRow.location || '') + ' ' + (targetRow.remark || '');"
new3 = "const textToCheck = (targetRow.client_name || '') + ' ' + (targetRow.location || '') + ' ' + (targetRow.remark || '');"
content = content.replace(old3, new3)

# 4. Update watch for newRow
# Let's find the watch line
watch_pattern = r"watch\(\[\(\) => newRow\.value\.weight, \(\) => newRow\.value\.location, \(\) => newRow\.value\.remark\], \(\[newWeight, newLoc, newRemark\]\) => \{"
new_watch = "watch([() => newRow.value.weight, () => newRow.value.location, () => newRow.value.remark, () => newRow.value.client_name], ([newWeight, newLoc, newRemark, newClientName]) => {"
content = re.sub(watch_pattern, new_watch, content)

# 5. Update textToCheck inside watch
watch_text_pattern = r"const textToCheck = \(newLoc \|\| ''\) \+ ' ' \+ \(newRemark \|\| ''\);"
new_watch_text = "const textToCheck = (newClientName || '') + ' ' + (newLoc || '') + ' ' + (newRemark || '');"
content = re.sub(watch_text_pattern, new_watch_text, content)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated textToCheck in 276 to include client_name")
