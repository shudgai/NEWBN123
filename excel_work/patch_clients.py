import re

def read_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(filepath, content):
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

content_206 = read_file('resources/views/client_206.blade.php')

# Extract Bottom Controls HTML
html_match = re.search(r'(<!-- Bottom Controls -->.*?</div>\s*</div>\s*</div>)', content_206, re.DOTALL)
if html_match:
    bottom_controls_html = html_match.group(1)
else:
    print("Failed to find Bottom Controls HTML in 206")
    exit(1)

# Extract sorting JS logic
js_match = re.search(r'(const sortState = ref\(\{ column: null, order: \'asc\' \}\);.*?)(const handleArrowKeys =)', content_206, re.DOTALL)
if js_match:
    sorting_js = js_match.group(1)
else:
    print("Failed to find sorting JS in 206")
    exit(1)

clients = ['225', '276', '444', '639']
for client in clients:
    filepath = f'resources/views/client_{client}.blade.php'
    try:
        content = read_file(filepath)
    except FileNotFoundError:
        print(f"Skipping {filepath} - not found")
        continue
        
    # 1. Replace Bottom Controls
    # In 225, there are two Bottom Controls blocks. We should replace everything from the first <!-- Bottom Controls --> to the end of the last one before <div v-if="showToast"
    content = re.sub(r'<!-- Bottom Controls -->.*?<div v-if="showToast"', bottom_controls_html + '\n\n    <div v-if="showToast"', content, flags=re.DOTALL)
    
    # 2. Add table header click events for sorting
    content = content.replace('<th style="width: 100px;">日期</th>', '<th @click="sortBy(\'date\')" style="width: 100px;" class="cursor-pointer hover:bg-gray-200 select-none">日期</th>')
    content = content.replace('<th style="width: 100px;">客戶名稱</th>', '<th @click="sortBy(\'client_name\')" style="width: 100px;" class="cursor-pointer hover:bg-gray-200 select-none">客戶名稱</th>')
    content = content.replace('<th style="width: 150px;">提單號碼</th>', '<th @click="sortBy(\'bill_no\')" style="width: 150px;" class="cursor-pointer hover:bg-gray-200 select-none">提單號碼</th>')
    content = content.replace('<th style="width: 60px;" class="text-right">件數</th>', '<th @click="sortBy(\'pieces\')" style="width: 60px;" class="text-right cursor-pointer hover:bg-gray-200 select-none">件數</th>')
    content = content.replace('<th style="width: 60px;" class="text-right">重量</th>', '<th @click="sortBy(\'weight\')" style="width: 60px;" class="text-right cursor-pointer hover:bg-gray-200 select-none">重量</th>')
    content = content.replace('<th style="width: 100px;" class="text-right">運費</th>', '<th @click="sortBy(\'amount\')" style="width: 100px;" class="text-right cursor-pointer hover:bg-gray-200 select-none">運費</th>')
    content = content.replace('<th style="width: 100px;">地點</th>', '<th @click="sortBy(\'location\')" style="width: 100px;" class="cursor-pointer hover:bg-gray-200 select-none">地點</th>')
    content = content.replace('<th style="width: 150px;">備註</th>', '<th @click="sortBy(\'remark\')" style="width: 150px;" class="cursor-pointer hover:bg-gray-200 select-none">備註</th>')

    # 3. Inject sorting logic
    if 'const sortState = ref' not in content:
        content = content.replace('const handleArrowKeys =', sorting_js + 'const handleArrowKeys =')
        
    # 4. Add to return block
    return_match = re.search(r'(return \{)(.*?)(\};)', content, re.DOTALL)
    if return_match:
        returns = return_match.group(2)
        added = []
        for var in ['sortState', 'resetView', 'sortBy', 'isAmountManual', 'recalculateAndSave']:
            if var not in returns:
                added.append(var)
        if added:
            new_returns = returns.rstrip() + ',\n                ' + ',\n                '.join(added) + '\n            '
            content = content[:return_match.start(2)] + new_returns + content[return_match.end(2):]
            
    write_file(filepath, content)
    print(f"Patched {filepath}")
