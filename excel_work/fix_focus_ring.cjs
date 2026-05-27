const fs = require('fs');

const dir = 'resources/views';
const files = fs.readdirSync(dir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

for (let file of files) {
    let content = fs.readFileSync(`${dir}/${file}`, 'utf-8');
    
    // Add focus:outline-none to the slider
    content = content.replace(/class="w-32 md:w-48 cursor-pointer"/g, 'class="w-32 md:w-48 cursor-pointer focus:outline-none focus:ring-0"');
    
    fs.writeFileSync(`${dir}/${file}`, content, 'utf-8');
}
console.log('Fixed focus ring.');
