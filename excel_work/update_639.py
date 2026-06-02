import re

filepath = 'resources/views/client_639.blade.php'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add <th> for Location
th_pattern = r'<th style="width: 100px;" class="text-right">堆高機</th>\n\s*<th @click="sortBy\(\'remark\'\)"'
th_replacement = r'<th style="width: 100px;" class="text-right">堆高機</th>\n                    <th @click="sortBy(\'location\')" style="width: 100px;" class="cursor-pointer hover:bg-gray-200 select-none">地點</th>\n                    <th @click="sortBy(\'remark\')"'
content = re.sub(th_pattern, th_replacement, content)

# 2. Add <td> for Location in data rows
td_pattern = r'<td><input autocomplete="off" @keydown="handleArrowKeys" @input="isAmountManual = true" type="text" v-model.number="row\.amount".*?</td>\n\s*<td><input autocomplete="off" @keydown="handleArrowKeys" type="text" v-model.number="row\.forklift_fee".*?</td>\n\s*<td class="p-0 relative group".*?v-model\.trim="row\.remark"'
# Actually let's just find the forklift_fee td and remark td
forklift_td_pattern = r'(<td><input autocomplete="off" @keydown="handleArrowKeys" type="text" v-model.number="row\.forklift_fee"[^>]*></td>)\n(\s*<td class="p-0 relative group" :class="\{\'fill-highlight\': isFillHighlighted\(index, \'remark\'\)\}" :style="getCellStyle\(row, 7\)")'
forklift_td_repl = r'\1\n                    <td class="p-0 relative group" :class="{\'fill-highlight\': isFillHighlighted(index, \'location\')}" :style="getCellStyle(row, 7)"><input list="location-names" autocomplete="off" @keydown="handleArrowKeys" @input="previewFreight(row)" @change="handleRemarkChange(row, index)" type="text" v-model.trim="row.location" class="nav-input w-full p-1 bg-transparent border-0 focus:outline-none focus:bg-white focus:ring-1 focus:ring-blue-400"><div class="fill-handle" @mousedown="startFill(index, \'location\', $event)"></div></td>\n\2'
content = re.sub(forklift_td_pattern, forklift_td_repl, content)
# Also change getCellStyle(row, 7) for remark to getCellStyle(row, 8)
content = re.sub(r"(:class=\"\{'fill-highlight': isFillHighlighted\(index, 'remark'\)\}\" :style=\"getCellStyle\(row, )7(\)\")", r"\g<1>8\g<2>", content)

# 3. Add <td> for Location in newRow
newrow_td_pattern = r'(<td><input autocomplete="off" @keyup\.enter="addRow" @keydown="handleArrowKeys" type="text" v-model\.number="newRow\.forklift_fee"[^>]*></td>)\n(\s*<td><input list="remark-options")'
newrow_td_repl = r'\1\n                    <td><input list="location-names" autocomplete="off" @keyup.enter="addRow" @keydown="handleArrowKeys" type="text" v-model.trim="newRow.location" class="nav-input w-full border p-1" placeholder="地點"></td>\n\2'
content = re.sub(newrow_td_pattern, newrow_td_repl, content)

# 4. Update fields in handlePaste
fields_pattern = r"const fields = \['date', 'client_name', 'bill_no', 'pieces', 'weight', 'amount', 'location', 'remark'\];"
fields_repl = r"const fields = ['date', 'client_name', 'bill_no', 'pieces', 'weight', 'amount', 'forklift_fee', 'location', 'remark'];"
content = content.replace(fields_pattern, fields_repl)

# 5. Handle row creation in handlePaste
# It currently has:
# targetRow.amount = rowVals[4].trim() === '' ? null : (parseFloat(rowVals[4]) || 0);
# targetRow.pieces = rowVals[6].trim() === '' ? null : (parseFloat(rowVals[6]) || 0);
# targetRow.weight = rowVals[7].trim() === '' ? null : (parseFloat(rowVals[7]) || 0);
# Wait! Let's just fix it globally if it's there
# It doesn't seem to be matching the new fields array. Let's check what it actually is in 639
# Wait, let's just do it with python string manipulation if we need to.

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated basic HTML and paste fields")
