const fs = require('fs');
const file = 'resources/views/client_206.blade.php';

let content = fs.readFileSync(file, 'utf-8');

const topRegex = /<div class="mb-4 flex justify-between items-center bg-gray-50 p-3 rounded border">[\s\S]*?<\/div>\s*<\/div>/;

const newTop = `<div class="mb-4 grid grid-cols-3 items-center bg-gray-50 p-3 rounded border">
    <div class="flex justify-start">
        <button @click="clearAllData" class="bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded shadow transition-colors">
            清空全部資料
        </button>
    </div>
    <div class="flex justify-center items-center gap-4">
        <label for="fontSizeSlider" class="font-bold text-sm text-gray-700 whitespace-nowrap">字體大小調整 (目前: @{{ fontSize }}px)</label>
        <input type="range" id="fontSizeSlider" v-model="fontSize" min="10" max="24" step="1" class="w-32 md:w-48 cursor-pointer">
    </div>
    <div class="flex justify-end">
        <button @click="scrollToBottom" class="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded shadow transition-colors flex items-center gap-2">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"></path></svg>
            移至最底
        </button>
    </div>
</div>`;

content = content.replace(topRegex, newTop);
fs.writeFileSync(file, content, 'utf-8');
console.log(`Updated ${file}`);
