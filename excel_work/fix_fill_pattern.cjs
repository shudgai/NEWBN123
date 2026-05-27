const fs = require('fs');

const dir = 'resources/views';
const files = fs.readdirSync(dir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

for (let file of files) {
    let content = fs.readFileSync(`${dir}/${file}`, 'utf-8');
    
    const searchBg1 = `ws[cell_ref].s.fill = { fgColor: { rgb: "FFFF00" } };`;
    const replaceBg1 = `ws[cell_ref].s.fill = { patternType: "solid", fgColor: { rgb: "FFFF00" } };`;
    
    const searchBg2 = `ws[cell_ref].s.fill = { fgColor: { rgb: hexMatch[1].toUpperCase() } };`;
    const replaceBg2 = `ws[cell_ref].s.fill = { patternType: "solid", fgColor: { rgb: hexMatch[1].toUpperCase() } };`;
    
    // Some files might have multiple occurrences
    content = content.split(searchBg1).join(replaceBg1);
    content = content.split(searchBg2).join(replaceBg2);

    fs.writeFileSync(`${dir}/${file}`, content, 'utf-8');
    console.log(`Fixed fill pattern in ${file}`);
}
