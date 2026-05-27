const fs = require('fs');

const dir = 'resources/views';
const files = fs.readdirSync(dir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

for (let file of files) {
    let content = fs.readFileSync(`${dir}/${file}`, 'utf-8');
    
    // 1. Remove Top Buttons
    const topControlsRegex = /<!-- Controls Section -->[\s\S]*?(?=<!-- Excel Header Section)/;
    
    const newTopControls = `<!-- Controls Section -->
    <div class="mb-4 flex justify-end items-center bg-gray-50 p-3 rounded border">
        <div class="flex items-center gap-4">
            <label for="fontSizeSlider" class="font-bold text-sm text-gray-700">字體大小調整 (目前: @{{ fontSize }}px)</label>
            <input type="range" id="fontSizeSlider" v-model="fontSize" min="10" max="24" step="1" class="w-48 cursor-pointer">
        </div>
    </div>

    `;
    
    content = content.replace(topControlsRegex, newTopControls);
    
    // 2. Add Bottom Controls
    const commonButtons = `
            <a href="/" class="bg-gray-700 hover:bg-gray-800 text-white font-bold py-2 px-4 rounded shadow transition-colors">
                回首頁
            </a>
            <button @click="exportExcel" class="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded shadow transition-colors">
                匯出 Excel
            </button>
            <button @click="clearAllData" class="bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded shadow transition-colors">
                清空全部資料
            </button>
            <button v-if="selectedRows.length > 0" @click="deleteSelected" class="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded shadow transition-colors">
                刪除選取項目 (@{{ selectedRows.length }})
            </button>
`;
    
    if (file === 'client_206.blade.php') {
        const bottom206Regex = /<!-- Bottom Controls -->[\s\S]*?(?=<div v-if="showToast")/;
        
        const newBottom206 = `<!-- Bottom Controls -->
    <div class="mt-4 p-4 bg-gray-50 border border-gray-300 rounded-lg shadow-sm">
        <div class="flex flex-wrap gap-4 items-center justify-between">
            <div class="flex gap-4 items-center">
                <span class="text-gray-700 font-bold text-lg">快速排序：</span>
                <button @click="sortBy('bill_no')" class="bg-indigo-500 hover:bg-indigo-600 text-white font-bold py-2 px-4 rounded shadow transition-colors flex items-center gap-2">
                    <span>依帳單編號排序</span>
                    <span v-if="sortState.column === 'bill_no'" class="text-xs bg-indigo-700 px-1 rounded">@{{ sortState.order === 'asc' ? '▲' : '▼' }}</span>
                </button>
                <button @click="resetView" class="bg-gray-500 hover:bg-gray-600 text-white font-bold py-2 px-4 rounded shadow transition-colors flex items-center gap-2">
                    <span>恢復介面</span>
                </button>
                <span class="text-sm text-gray-500 ml-2">※ 提示：如果有打勾選取超過1筆資料，只會針對選取的資料重新排序</span>
            </div>
            
            <div class="flex gap-4 items-center mt-4 lg:mt-0">
                ${commonButtons}
            </div>
        </div>
    </div>

    `;
        content = content.replace(bottom206Regex, newBottom206);
    } else {
        // For other files, insert before <div v-if="showToast"
        const newBottom = `
    <!-- Bottom Controls -->
    <div class="mt-4 p-4 bg-gray-50 border border-gray-300 rounded-lg shadow-sm flex flex-wrap gap-4 items-center justify-end">
        ${commonButtons}
    </div>

    `;
        content = content.replace(/(<div v-if="showToast")/, newBottom + '$1');
    }
    
    fs.writeFileSync(`${dir}/${file}`, content, 'utf-8');
    console.log(`Updated ${file}`);
}
