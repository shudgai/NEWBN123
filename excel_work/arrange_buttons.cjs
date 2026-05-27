const fs = require('fs');

const dir = 'resources/views';
const files = fs.readdirSync(dir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

for (let file of files) {
    let content = fs.readFileSync(`${dir}/${file}`, 'utf-8');
    
    // 1. Remove clearAllData from bottom
    const clearDataRegex = /\s*<button @click="clearAllData"[\s\S]*?<\/button>/;
    content = content.replace(clearDataRegex, '');
    
    // 2. Add clearAllData to top-left
    const topControlsRegex = /<div class="mb-4 flex justify-end items-center bg-gray-50 p-3 rounded border">/;
    const newTopControls = `<div class="mb-4 flex justify-between items-center bg-gray-50 p-3 rounded border">
        <button @click="clearAllData" class="bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded shadow transition-colors">
            清空全部資料
        </button>`;
    content = content.replace(topControlsRegex, newTopControls);

    // 3. For 206, remove hint and move buttons
    if (file === 'client_206.blade.php') {
        // Find the hint and remove it
        const hintRegex = /\s*<span class="text-sm text-gray-500 ml-2">※ 提示：如果有打勾選取超過1筆資料，只會針對選取的資料重新排序<\/span>/;
        content = content.replace(hintRegex, '');
        
        // Find the split between the two button groups and merge them
        const splitRegex = /<\/div>\s*<div class="flex gap-4 items-center mt-4 lg:mt-0">/;
        content = content.replace(splitRegex, '');
        
        // Remove justify-between from the wrapper
        content = content.replace(/justify-between/, 'justify-start');
    } else {
        // For other files, change justify-end to justify-start
        content = content.replace(/<div class="mt-4 p-4 bg-gray-50 border border-gray-300 rounded-lg shadow-sm flex flex-wrap gap-4 items-center justify-end">/, '<div class="mt-4 p-4 bg-gray-50 border border-gray-300 rounded-lg shadow-sm flex flex-wrap gap-4 items-center justify-start">');
    }

    fs.writeFileSync(`${dir}/${file}`, content, 'utf-8');
    console.log(`Updated ${file}`);
}
