import sys

filepath = 'resources/views/client_276.blade.php'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove the location td from newRow
line_to_remove = '<td><input list="location-names" autocomplete="off" @keyup.enter="addRow" @keydown="handleArrowKeys" type="text" v-model.trim="newRow.location" class="nav-input w-full border p-1" placeholder="地點"></td>'
content = content.replace(line_to_remove + '\n', '')
content = content.replace(line_to_remove, '')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Removed location from newRow in 276")
