const fs = require('fs');

const dir = 'resources/views';
const files = fs.readdirSync(dir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

for (let file of files) {
    let content = fs.readFileSync(`${dir}/${file}`, 'utf-8');
    
    // We want to add the is_client_data background check right before customStyle background check
    const searchCode = `if (customStyle) {
                                // Background`;
                        
    const replaceCode = `// Force yellow background if row is marked as client data
                            if (rowData.is_client_data) {
                                ws[cell_ref].s.fill = { patternType: "solid", fgColor: { rgb: "FFFF00" } };
                            }
                            
                            if (customStyle) {
                                // Background`;

    if (content.includes(searchCode)) {
        content = content.replace(searchCode, replaceCode);
        fs.writeFileSync(`${dir}/${file}`, content, 'utf-8');
        console.log(`Added is_client_data bg to ${file}`);
    }
}
