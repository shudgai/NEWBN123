const fs = require('fs');

const dir = 'resources/views';
const files = fs.readdirSync(dir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

for (let file of files) {
    let content = fs.readFileSync(`${dir}/${file}`, 'utf-8');
    
    // 1. Restore and fix inline style border parsing
    const inlineBorderRegex = /\['borderTop', 'borderBottom', 'borderLeft', 'borderRight', 'border'\]\.forEach\(prop => \{\n\s*if \(cell\.style\[prop\]\) \{\n\s*const val = cell\.style\[prop\]\.toLowerCase\(\);\n\s*\/\/ Ignore thin borders \(\.5pt, thin, 1px\) to only keep thick borders\n\s*if \(val\.includes\('\.5pt'\) \|\| val\.includes\('thin'\) \|\| val\.includes\('1px'\) \|\| val === 'solid windowtext'\) \{\n\s*\/\/ ignore\n\s*\} else \{\n\s*cellStyle\[prop\] = cell\.style\[prop\];\n\s*\}\n\s*\}\n\s*\}\);/g;
    
    const newInlineBorderCode = `['borderTop', 'borderBottom', 'borderLeft', 'borderRight', 'border'].forEach(prop => {
                                    if (cell.style[prop]) {
                                        cellStyle[prop] = cell.style[prop].replace(/windowtext/gi, 'black');
                                    }
                                });`;
                                
    content = content.replace(inlineBorderRegex, newInlineBorderCode);
    
    // 2. Restore and fix class style border parsing
    const classBorderRegex = /if \(prop\.includes\('border'\)\) \{\n\s*const v = val\.toLowerCase\(\);\n\s*if \(v\.includes\('\.5pt'\) \|\| v\.includes\('thin'\) \|\| v\.includes\('1px'\) \|\| v === 'solid windowtext' \|\| v === 'none'\) \{\n\s*\/\/ ignore\n\s*\} else \{\n\s*const jsProp = prop\.replace\(/-([a-z])/g, g => g\[1\]\.toUpperCase\(\)\);\n\s*styleObj\[jsProp\] = val;\n\s*\}\n\s*\}/g;
    
    const newClassBorderCode = `if (prop.includes('border')) {
                                            const jsProp = prop.replace(/-([a-z])/g, g => g[1].toUpperCase());
                                            styleObj[jsProp] = val.replace(/windowtext/gi, 'black');
                                        }`;
                                        
    content = content.replace(classBorderRegex, newClassBorderCode);
    
    // 3. Fix export logic to map thin -> thin, thick -> medium
    const exportRegex = /\/\/ Only export thick borders\n\s*if \(b\.includes\('thick'\) \|\| b\.includes\('medium'\) \|\| b\.includes\('2px'\) \|\| b\.includes\('3px'\) \|\| b\.includes\('1\.5pt'\) \|\| b\.includes\('2pt'\) \|\| b\.includes\('solid'\)\) \{\n\s*ws\[cell_ref\]\.s\.border\[dir\] = \{ style: "medium", color: \{ rgb: "000000" \} \};\n\s*\}/g;
    
    const newExportCode = `// Export borders mapping
                                        if (b.includes('thick') || b.includes('medium') || b.includes('2px') || b.includes('3px') || b.includes('1.5pt') || b.includes('2pt')) {
                                            ws[cell_ref].s.border[dir] = { style: "medium", color: { rgb: "000000" } };
                                        } else if (b.includes('thin') || b.includes('.5pt') || b.includes('1px') || b.includes('solid')) {
                                            ws[cell_ref].s.border[dir] = { style: "thin", color: { rgb: "000000" } };
                                        }`;
                                        
    content = content.replace(exportRegex, newExportCode);

    fs.writeFileSync(`${dir}/${file}`, content, 'utf-8');
    console.log(`Restored all borders in ${file}`);
}
