const fs = require('fs');

const dir = 'resources/views';
const files = fs.readdirSync(dir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

for (let file of files) {
    let content = fs.readFileSync(`${dir}/${file}`, 'utf-8');
    
    // Check if getCellStyle is defined
    if (!content.includes('const getCellStyle = (row, colIndex) => {')) {
        // Inject right after const tableData = ref([]);
        content = content.replace('const tableData = ref([]);', `const tableData = ref([]);
            
            const getCellStyle = (row, colIndex) => {
                if (!row || !row.styles || !row.styles[colIndex]) return {};
                return row.styles[colIndex];
            };`);
            
        fs.writeFileSync(`${dir}/${file}`, content, 'utf-8');
        console.log(`Fixed getCellStyle in ${file}`);
    }
}
