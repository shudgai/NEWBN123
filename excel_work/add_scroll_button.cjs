const fs = require('fs');

const dir = 'resources/views';
const files = fs.readdirSync(dir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

for (let file of files) {
    let content = fs.readFileSync(`${dir}/${file}`, 'utf-8');
    
    // 1. Update Controls Section
    const topControlsRegex = /<!-- Controls Section -->\s*<div class="mb-4 flex justify-end items-center bg-gray-50 p-3 rounded border">\s*<div class="flex items-center gap-4">/;
    
    const newTopControls = `<!-- Controls Section -->
    <div class="mb-4 flex justify-between items-center bg-gray-50 p-3 rounded border">
        <div>
            <button @click="scrollToBottom" class="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded shadow transition-colors flex items-center gap-2">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"></path></svg>
                移至最底
            </button>
        </div>
        <div class="flex items-center gap-4">`;
    
    content = content.replace(topControlsRegex, newTopControls);
    
    // 2. Add scrollToBottom function before exportExcel
    if (!content.includes('scrollToBottom = ()')) {
        content = content.replace('const exportExcel = () => {', `const scrollToBottom = () => {
                window.scrollTo({
                    top: document.body.scrollHeight,
                    behavior: 'smooth'
                });
            };

            const exportExcel = () => {`);
    }

    // 3. Add to return
    if (!content.includes('scrollToBottom,')) {
        content = content.replace('exportExcel,', 'scrollToBottom,\n                exportExcel,');
    }
    
    fs.writeFileSync(`${dir}/${file}`, content, 'utf-8');
    console.log(`Updated ${file}`);
}
