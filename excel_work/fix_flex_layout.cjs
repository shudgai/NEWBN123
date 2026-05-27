const fs = require('fs');

const dir = 'resources/views';
const files = fs.readdirSync(dir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

for (let file of files) {
    let content = fs.readFileSync(`${dir}/${file}`, 'utf-8');
    
    // Find the whole controls section block
    const regex = /<div class="mb-4[^>]*>[\s\S]*?移至最底\s*<\/button>\s*<\/div>\s*<\/div>/;
    
    const newHTML = `<div class="mb-4 flex justify-between items-center bg-gray-50 p-3 rounded border w-full">
        <div>
            <button @click="clearAllData" class="bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded shadow transition-colors focus:outline-none focus:ring-0">
                清空全部資料
            </button>
        </div>
        <div class="flex items-center justify-center gap-4">
            <label for="fontSizeSlider" class="font-bold text-sm text-gray-700 whitespace-nowrap">字體大小調整 (目前: @{{ fontSize }}px)</label>
            <input type="range" id="fontSizeSlider" v-model="fontSize" min="10" max="24" step="1" class="w-32 md:w-48 cursor-pointer focus:outline-none focus:ring-0">
        </div>
        <div>
            <button @click="scrollToBottom" class="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded shadow transition-colors flex items-center gap-2 focus:outline-none focus:ring-0">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"></path></svg>
                移至最底
            </button>
        </div>
    </div>`;
    
    if (regex.test(content)) {
        content = content.replace(regex, newHTML);
        fs.writeFileSync(`${dir}/${file}`, content, 'utf-8');
        console.log(`Fixed layout in ${file}`);
    } else {
        console.log(`Could not match layout in ${file}`);
    }
}
