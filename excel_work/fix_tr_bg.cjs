const fs = require('fs');

const dir = 'resources/views';
const files = fs.readdirSync(dir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

for (let file of files) {
    let content = fs.readFileSync(`${dir}/${file}`, 'utf-8');
    
    // The target is: class="border-b border-gray-300" :class="{'bg-yellow-200': row.is_client_data, 'hover:bg-yellow-50': !row.is_client_data}"
    // We want to remove the :class part and just use hover:bg-gray-50
    
    const searchClass = `class="border-b border-gray-300" :class="{'bg-yellow-200': row.is_client_data, 'hover:bg-yellow-50': !row.is_client_data}"`;
    const replaceClass = `class="border-b border-gray-300 hover:bg-gray-50"`;
    
    content = content.replace(searchClass, replaceClass);

    fs.writeFileSync(`${dir}/${file}`, content, 'utf-8');
    console.log(`Fixed tr background in ${file}`);
}
