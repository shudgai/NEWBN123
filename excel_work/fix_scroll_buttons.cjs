const fs = require('fs');

const dir = 'resources/views';
const files = fs.readdirSync(dir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

for (let file of files) {
    let content = fs.readFileSync(`${dir}/${file}`, 'utf-8');
    
    // 1. Update Controls Section (move scrollToBottom to the right)
    const topControlsRegex = /<!-- Controls Section -->[\s\S]*?<div class="mb-6 grid grid-cols-2 gap-4 text-sm"/;
    
    const newTopControls = `<!-- Controls Section -->
    <div class="mb-4 flex justify-end items-center bg-gray-50 p-3 rounded border">
        <div class="flex items-center gap-4">
            <label for="fontSizeSlider" class="font-bold text-sm text-gray-700">字體大小調整 (目前: @{{ fontSize }}px)</label>
            <input type="range" id="fontSizeSlider" v-model="fontSize" min="10" max="24" step="1" class="w-48 cursor-pointer">
            <button @click="scrollToBottom" class="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded shadow transition-colors flex items-center gap-2 ml-4">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"></path></svg>
                移至最底
            </button>
        </div>
    </div>

    <!-- Excel Header Section -->
    <div class="mb-6 grid grid-cols-2 gap-4 text-sm"`;
    
    content = content.replace(topControlsRegex, newTopControls);
    
    // 2. Add scrollToTop button at the bottom controls
    const scrollToTopBtn = `
            <button @click="scrollToTop" class="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded shadow transition-colors flex items-center gap-2">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18"></path></svg>
                移至最上方
            </button>`;
            
    content = content.replace(/<a href="\/" class="bg-gray-700/, scrollToTopBtn + '\n            <a href="/" class="bg-gray-700');
    
    // 3. Add scrollToTop function
    if (!content.includes('scrollToTop = ()')) {
        content = content.replace('const scrollToBottom = () => {', `const scrollToTop = () => {
                window.scrollTo({
                    top: 0,
                    behavior: 'smooth'
                });
            };

            const scrollToBottom = () => {`);
    }

    // 4. Add to return
    if (!content.includes('scrollToTop,')) {
        content = content.replace('scrollToBottom,', 'scrollToTop,\n                scrollToBottom,');
    }
    
    fs.writeFileSync(`${dir}/${file}`, content, 'utf-8');
    console.log(`Updated ${file}`);
}
