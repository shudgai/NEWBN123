const fs = require('fs');

const dir = 'resources/views';
const files = fs.readdirSync(dir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

for (let file of files) {
    let content = fs.readFileSync(`${dir}/${file}`, 'utf-8');
    
    // 1. Remove default thin borders
    const defaultBorderRegex = /ws\[cell_ref\]\.s\.border = \{\s*top: \{ style: "thin", color: \{ rgb: "000000" \} \},\s*bottom: \{ style: "thin", color: \{ rgb: "000000" \} \},\s*left: \{ style: "thin", color: \{ rgb: "000000" \} \},\s*right: \{ style: "thin", color: \{ rgb: "000000" \} \}\s*\};\n/g;
    content = content.replace(defaultBorderRegex, '');
    
    // 2. Fix custom style border application
    const customBorderRegex = /\['top', 'bottom', 'left', 'right'\]\.forEach\(dir => \{\n\s*const jsProp = 'border' \+ dir\.charAt\(0\)\.toUpperCase\(\) \+ dir\.slice\(1\);\n\s*if \(customStyle\[jsProp\] \|\| customStyle\.border\) \{\n\s*const b = customStyle\[jsProp\] \|\| customStyle\.border;\n\s*if \(b\.includes\('thick'\) \|\| b\.includes\('medium'\) \|\| b\.includes\('2px'\) \|\| b\.includes\('3px'\)\) \{\n\s*ws\[cell_ref\]\.s\.border\[dir\] = \{ style: "medium", color: \{ rgb: "000000" \} \};\n\s*\}\n\s*\}\n\s*\}\);/g;
    
    const newCustomBorderCode = `if (!ws[cell_ref].s.border) ws[cell_ref].s.border = {};
                                ['top', 'bottom', 'left', 'right'].forEach(dir => {
                                    const jsProp = 'border' + dir.charAt(0).toUpperCase() + dir.slice(1);
                                    if (customStyle[jsProp] || customStyle.border) {
                                        const b = customStyle[jsProp] || customStyle.border;
                                        if (b.includes('thick') || b.includes('medium') || b.includes('2px') || b.includes('3px')) {
                                            ws[cell_ref].s.border[dir] = { style: "medium", color: { rgb: "000000" } };
                                        } else if (b.includes('thin') || b.includes('1px') || b.includes('solid')) {
                                            ws[cell_ref].s.border[dir] = { style: "thin", color: { rgb: "000000" } };
                                        }
                                    }
                                });`;
    
    content = content.replace(customBorderRegex, newCustomBorderCode);
    
    fs.writeFileSync(`${dir}/${file}`, content, 'utf-8');
    console.log(`Fixed borders in ${file}`);
}
