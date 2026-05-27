const fs = require('fs');

const dir = 'resources/views';
const files = fs.readdirSync(dir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

for (let file of files) {
    let content = fs.readFileSync(`${dir}/${file}`, 'utf-8');
    
    // We want to add styling when R === 0
    const searchCode = `if (!ws[cell_ref].s) ws[cell_ref].s = {};
                        ws[cell_ref].s.font = { name: "微軟正黑體", sz: 12 };`;
                        
    const replaceCode = `if (!ws[cell_ref].s) ws[cell_ref].s = {};
                        ws[cell_ref].s.font = { name: "微軟正黑體", sz: 12 };
                        
                        // Header styling
                        if (R === 0) {
                            ws[cell_ref].s.fill = { patternType: "solid", fgColor: { rgb: "E5E7EB" } };
                            ws[cell_ref].s.border = {
                                top: { style: 'thin', color: { auto: 1 } },
                                bottom: { style: 'medium', color: { auto: 1 } },
                                left: { style: 'thin', color: { auto: 1 } },
                                right: { style: 'thin', color: { auto: 1 } }
                            };
                            ws[cell_ref].s.font.bold = true;
                        }`;

    // Replace first occurrence (which is inside the loop where we set font)
    if (content.includes(searchCode)) {
        content = content.replace(searchCode, replaceCode);
        fs.writeFileSync(`${dir}/${file}`, content, 'utf-8');
        console.log(`Added header styling to ${file}`);
    } else {
        // Try regex if whitespace is different
        const regex = /if \(!ws\[cell_ref\]\.s\) ws\[cell_ref\]\.s = \{\};\s*ws\[cell_ref\]\.s\.font = \{ name: "微軟正黑體", sz: 12 \};/g;
        content = content.replace(regex, replaceCode);
        fs.writeFileSync(`${dir}/${file}`, content, 'utf-8');
        console.log(`Added header styling to ${file} (via regex)`);
    }
}
