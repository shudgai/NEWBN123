const fs = require('fs');

const dir = 'resources/views';
const files = fs.readdirSync(dir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

for (let file of files) {
    let content = fs.readFileSync(`${dir}/${file}`, 'utf-8');
    
    // 1. Replace the inline style border loop
    const borderCodeToReplace = "['borderTop', 'borderBottom', 'borderLeft', 'borderRight', 'border'].forEach(prop => {\n                                    if (cell.style[prop]) {\n                                        cellStyle[prop] = cell.style[prop];\n                                    }\n                                });";
    
    const newBorderCode = `['borderTop', 'borderBottom', 'borderLeft', 'borderRight', 'border'].forEach(prop => {
                                    if (cell.style[prop]) {
                                        const val = cell.style[prop].toLowerCase();
                                        // Ignore thin borders (.5pt, thin, 1px) to only keep thick borders
                                        if (val.includes('.5pt') || val.includes('thin') || val.includes('1px') || val === 'solid windowtext') {
                                            // ignore
                                        } else {
                                            cellStyle[prop] = cell.style[prop];
                                        }
                                    }
                                });`;
                                
    // Just string replace
    content = content.replace(borderCodeToReplace, newBorderCode);
    
    // 2. Replace the class style border setting
    const classBorderCodeToReplace = `if (prop.includes('border')) {
                                            const jsProp = prop.replace(/-([a-z])/g, g => g[1].toUpperCase());
                                            styleObj[jsProp] = val;
                                        }`;
    
    const newClassBorderCode = `if (prop.includes('border')) {
                                            const v = val.toLowerCase();
                                            if (v.includes('.5pt') || v.includes('thin') || v.includes('1px') || v === 'solid windowtext' || v === 'none') {
                                                // ignore
                                            } else {
                                                const jsProp = prop.replace(/-([a-z])/g, g => g[1].toUpperCase());
                                                styleObj[jsProp] = val;
                                            }
                                        }`;
                                        
    content = content.replace(classBorderCodeToReplace, newClassBorderCode);
    
    // 3. Update export logic
    const exportRegex = /if \(b\.includes\('thick'\) \|\| b\.includes\('medium'\) \|\| b\.includes\('2px'\) \|\| b\.includes\('3px'\)\) \{\n\s*ws\[cell_ref\]\.s\.border\[dir\] = \{ style: "medium", color: \{ rgb: "000000" \} \};\n\s*\} else if \(b\.includes\('thin'\) \|\| b\.includes\('1px'\) \|\| b\.includes\('solid'\)\) \{\n\s*ws\[cell_ref\]\.s\.border\[dir\] = \{ style: "thin", color: \{ rgb: "000000" \} \};\n\s*\}/g;
    
    const newExportCode = `// Only export thick borders
                                        if (b.includes('thick') || b.includes('medium') || b.includes('2px') || b.includes('3px') || b.includes('1.5pt') || b.includes('2pt') || b.includes('solid')) {
                                            ws[cell_ref].s.border[dir] = { style: "medium", color: { rgb: "000000" } };
                                        }`;
                                        
    content = content.replace(exportRegex, newExportCode);

    fs.writeFileSync(`${dir}/${file}`, content, 'utf-8');
    console.log(`Filtered borders in ${file}`);
}
