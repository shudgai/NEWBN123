const fs = require('fs');

const dir = 'resources/views';
const files = fs.readdirSync(dir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

for (let file of files) {
    let content = fs.readFileSync(`${dir}/${file}`, 'utf-8');
    
    // Remove the forced yellow background for is_client_data in exportExcel
    const searchCode = `                        // Force yellow background if row is marked as client data
                        if (rowData.is_client_data) {
                            ws[cell_ref].s.fill = { patternType: "solid", fgColor: { rgb: "FFFF00" } };
                        }`;
                        
    content = content.replace(searchCode, '');
    
    // Also remove the !rowData.is_client_data check so custom styles apply normally
    const searchCheck = `if (customStyle.backgroundColor && !rowData.is_client_data) {`;
    const replaceCheck = `if (customStyle.backgroundColor) {`;
    content = content.replace(searchCheck, replaceCheck);

    fs.writeFileSync(`${dir}/${file}`, content, 'utf-8');
    console.log(`Fixed export is_client_data in ${file}`);
}
