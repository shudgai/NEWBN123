const fs = require('fs');

const dir = 'resources/views';
const files = fs.readdirSync(dir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

for (let file of files) {
    let content = fs.readFileSync(`${dir}/${file}`, 'utf-8');
    
    // We want to swap the "清空全部資料" button and the "刪除選取項目" button.
    const clearDataBtn = `            <button @click="clearAllData" class="bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded shadow transition-colors">
                清空全部資料
            </button>`;
            
    const deleteSelectedBtn = `            <button v-if="selectedRows.length > 0" @click="deleteSelected" class="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded shadow transition-colors">
                刪除選取項目 (@{{ selectedRows.length }})
            </button>`;

    // Remove them first
    content = content.replace(clearDataBtn + '\n', '');
    content = content.replace(deleteSelectedBtn + '\n', '');
    content = content.replace(clearDataBtn, ''); // in case of no trailing newline
    content = content.replace(deleteSelectedBtn, '');
    
    // Now insert them back in the new order after exportExcel
    const exportExcelBtn = `            <button @click="exportExcel" class="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded shadow transition-colors">
                匯出 Excel
            </button>`;
            
    content = content.replace(exportExcelBtn, exportExcelBtn + '\n' + deleteSelectedBtn + '\n' + clearDataBtn);

    fs.writeFileSync(`${dir}/${file}`, content, 'utf-8');
    console.log(`Updated ${file}`);
}
