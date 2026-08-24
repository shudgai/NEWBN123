import os
import re

clients = ['206', '225', '276', '282', '444', '639']

for code in clients:
    filepath = f"resources/views/client_{code}.blade.php"
    if not os.path.exists(filepath):
        continue
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Add dbSavedClients
    if 'const dbSavedClients' not in content:
        content = content.replace('const tableData = ref([]);', 'const tableData = ref([]);\n            const dbSavedClients = ref([]);')

    # 2. Add fetchSavedClients and saveClientName
    js_code = f"""
            const fetchSavedClients = async () => {{
                try {{
                    const response = await fetch(`/api/saved-clients?client_code={code}`);
                    if (response.ok) {{
                        dbSavedClients.value = await response.json();
                    }}
                }} catch (e) {{
                    console.error("Error fetching saved clients:", e);
                }}
            }};

            const saveClientName = async (name) => {{
                if (!name || dbSavedClients.value.includes(name)) return;
                try {{
                    const response = await fetch('/api/saved-clients', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ client_code: '{code}', client_name: name }})
                    }});
                    if (response.ok) {{
                        dbSavedClients.value.push(name);
                    }}
                }} catch (e) {{
                    console.error("Error saving client name:", e);
                }}
            }};
"""
    if 'const fetchSavedClients' not in content:
        content = content.replace('const handleGlobalKeyDown = (e) => {', js_code + '\n            const handleGlobalKeyDown = (e) => {')
    
    # 3. Call fetchSavedClients in onMounted
    if 'fetchSavedClients();' not in content:
        content = content.replace('fetchData();', 'fetchData();\n                fetchSavedClients();')
        
    # 4. Modify uniqueClientNames
    if 'const names = new Set();' in content and 'dbSavedClients.value' not in content:
        content = content.replace(
            'const names = new Set();',
            'const names = new Set(dbSavedClients.value);'
        )
        
    # 5. Call saveClientName in updateRow
    if 'const updateRow = async (row) => {' in content:
        # After successful fetch for update, we should save. Or just call it directly since it's async and checks if exists
        # Find where it says: row.isDirty = false; or similar inside updateRow
        content = re.sub(r'(const updateRow = async \(row\) => \{[\s\S]*?try \{[\s\S]*?if \(response\.ok\) \{[\s\S]*?)(\n[ \t]*row\.original =)', r'\1\n                        saveClientName(row.client_name);\2', content)

    # 6. Call saveClientName in addRow
    if 'const addRow = async () => {' in content:
        content = re.sub(r'(const addRow = async \(\) => \{[\s\S]*?try \{[\s\S]*?if \(response\.ok\) \{[\s\S]*?)(\n[ \t]*newRow\.value =)', r'\1\n                        saveClientName(newRow.value.client_name);\2', content)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

print("Patch applied.")
