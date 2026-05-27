const fs = require('fs');

const dir = 'resources/views';
const files = fs.readdirSync(dir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

for (let file of files) {
    let content = fs.readFileSync(`${dir}/${file}`, 'utf-8');
    
    // 1. Change @click="undoPaste" to @click="undoAction"
    content = content.replace(/@click="undoPaste"/g, '@click="undoAction"');
    
    // 2. Replace the undoPaste function with undoAction
    const undoPasteRegex = /const undoPaste = async \(\) => \{[\s\S]*?\n\s*await fetchData\(\);\n\s*\};/;
    const newUndoAction = `const undoAction = async () => {
                if (!undoData) return;
                showToast.value = false;
                
                if (undoData.type === 'delete') {
                    // Restore deleted rows by creating them again
                    for (const row of undoData.deletedRows) {
                        try {
                            await fetch('/api/waybills', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                                body: JSON.stringify(row)
                            });
                        } catch (e) { console.error(e); }
                    }
                } else {
                    // Default to undo paste behavior
                    for (const id of undoData.newRowIds || []) {
                        try {
                            await fetch(\`/api/waybills/\${id}\`, { method: 'DELETE' });
                        } catch (e) { console.error(e); }
                    }
                    
                    for (const oldRow of undoData.oldRows || []) {
                        try {
                            await fetch(\`/api/waybills/\${oldRow.id}\`, {
                                method: 'PUT',
                                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                                body: JSON.stringify(oldRow)
                            });
                        } catch (e) { console.error(e); }
                    }
                }
                
                undoData = null;
                await fetchData();
            };`;
            
    content = content.replace(undoPasteRegex, newUndoAction);
    
    // 3. Update deleteSelected to set undoData
    const deleteSelectedRegex = /const deleteSelected = async \(\) => \{[\s\S]*?if \(!confirm\([\s\S]*?\) return;\n\s*try \{/;
    const newDeleteSelected = `const deleteSelected = async () => {
                if (!confirm(\`確定要刪除選取的 \${selectedRows.value.length} 筆資料嗎？\`)) return;
                
                // Save rows to be deleted for undo functionality
                const rowsToDelete = tableData.value.filter(row => selectedRows.value.includes(row.id));
                undoData = {
                    type: 'delete',
                    deletedRows: rowsToDelete
                };
                
                try {`;
    content = content.replace(deleteSelectedRegex, newDeleteSelected);
    
    // 4. Update the success part of deleteSelected to show the toast
    const deleteSuccessRegex = /selectedRows\.value = \[\];\n\s*await fetchData\(\);/;
    const newDeleteSuccess = `selectedRows.value = [];
                    await fetchData();
                    
                    toastMessage.value = \`已刪除 \${undoData.deletedRows.length} 筆資料\`;
                    showToast.value = true;
                    setTimeout(() => { showToast.value = false; }, 8000);`;
    content = content.replace(deleteSuccessRegex, newDeleteSuccess);
    
    // 5. Change export of undoPaste to undoAction
    content = content.replace(/undoPaste,/g, 'undoAction,');
    
    fs.writeFileSync(`${dir}/${file}`, content, 'utf-8');
    console.log(`Updated ${file}`);
}
