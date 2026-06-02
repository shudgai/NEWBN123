import sys

filepath = 'resources/views/client_639.blade.php'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# The target line to find
forklift_td = """<td class="p-0 relative group" :class="{'fill-highlight': isFillHighlighted(index, 'forklift_fee')}" :style="getCellStyle(row, 6)"><input autocomplete="off" @keydown="handleArrowKeys" @change="recalculateAndSave(row)" type="text" v-model.number="row.forklift_fee" class="nav-input w-full p-1 bg-transparent border-0 text-right focus:outline-none focus:bg-white focus:ring-1 focus:ring-blue-400"><div class="fill-handle" @mousedown="startFill(index, 'forklift_fee', $event)"></div></td>"""

# The line to insert after it
location_td = """                    <td class="p-0 relative group" :class="{'fill-highlight': isFillHighlighted(index, 'location')}" :style="getCellStyle(row, 7)"><input list="location-names" autocomplete="off" @keydown="handleArrowKeys" @change="updateRow(row)" type="text" v-model.trim="row.location" class="nav-input w-full p-1 bg-transparent border-0 focus:outline-none focus:bg-white focus:ring-1 focus:ring-blue-400"><div class="fill-handle" @mousedown="startFill(index, 'location', $event)"></div></td>"""

if forklift_td in content:
    content = content.replace(forklift_td, forklift_td + "\n" + location_td)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Inserted location td!")
else:
    print("Could not find forklift td!")
