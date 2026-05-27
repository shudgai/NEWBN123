const fs = require('fs');

const dir = 'resources/views';
const files = fs.readdirSync(dir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

for (let file of files) {
    let content = fs.readFileSync(`${dir}/${file}`, 'utf-8');
    
    // 1. Update parsing logic in handlePaste
    // We need to replace the `let htmlBgData = [];` up to the end of parsing loop
    const parseRegex = /let htmlBgData = \[\];[\s\S]*?\} catch \(err\) \{\n\s*console\.error\('Error parsing HTML paste:', err\);\n\s*\}/;
    
    const newParseCode = `let htmlBgData = [];
                let htmlStylesData = [];
                
                if (htmlText) {
                    try {
                        const parser = new DOMParser();
                        const doc = parser.parseFromString(htmlText, 'text/html');
                        
                        // Parse style block for classes
                        let classStyles = {};
                        const styleTags = doc.querySelectorAll('style');
                        styleTags.forEach(style => {
                            const css = style.innerHTML;
                            const regex = /\\.(\\w+)\\s*\\{([^}]+)\\}/g;
                            let match;
                            while ((match = regex.exec(css)) !== null) {
                                const className = match[1];
                                const rules = match[2].split(';');
                                let styleObj = {};
                                rules.forEach(rule => {
                                    const parts = rule.split(':');
                                    if (parts.length === 2) {
                                        const prop = parts[0].trim();
                                        const val = parts[1].trim();
                                        if (prop.includes('background')) styleObj.backgroundColor = val;
                                        if (prop.includes('border')) {
                                            const jsProp = prop.replace(/-([a-z])/g, g => g[1].toUpperCase());
                                            styleObj[jsProp] = val;
                                        }
                                        if (prop.includes('color')) styleObj.color = val;
                                        if (prop.includes('font-weight')) styleObj.fontWeight = val;
                                    }
                                });
                                classStyles[className] = styleObj;
                            }
                        });

                        const rows = doc.querySelectorAll('tr');
                        for (let r = 0; r < rows.length; r++) {
                            const cells = rows[r].querySelectorAll('td, th');
                            if (cells.length === 0) continue;
                            let isClientData = false;
                            let rowStyles = [];
                            
                            for (let c = 0; c < cells.length; c++) {
                                const cell = cells[c];
                                let cellStyle = {};
                                
                                // Merge from class
                                const className = cell.className || '';
                                className.split(' ').forEach(cls => {
                                    if (classStyles[cls]) {
                                        Object.assign(cellStyle, classStyles[cls]);
                                    }
                                });
                                
                                // Merge from inline
                                const bg = cell.style.backgroundColor || cell.style.background || cell.getAttribute('bgcolor');
                                if (bg) cellStyle.backgroundColor = bg;
                                
                                ['borderTop', 'borderBottom', 'borderLeft', 'borderRight', 'border'].forEach(prop => {
                                    if (cell.style[prop]) {
                                        cellStyle[prop] = cell.style[prop];
                                    }
                                });
                                if (cell.style.fontWeight) cellStyle.fontWeight = cell.style.fontWeight;
                                if (cell.style.color) cellStyle.color = cell.style.color;

                                // Check yellow background for legacy is_client_data
                                if (cellStyle.backgroundColor && (cellStyle.backgroundColor.includes('255, 255, 0') || cellStyle.backgroundColor.toLowerCase().includes('ffff00') || cellStyle.backgroundColor.toLowerCase() === 'yellow' || cellStyle.backgroundColor.includes('rgb(255, 255,'))) {
                                    isClientData = true;
                                }
                                rowStyles.push(cellStyle);
                            }
                            htmlBgData.push(isClientData);
                            htmlStylesData.push(rowStyles);
                        }
                    } catch (err) {
                        console.error('Error parsing HTML paste:', err);
                    }`;
                    
    content = content.replace(parseRegex, newParseCode);
    
    // 2. Update applying logic in handlePaste
    const applyRegex = /const isClientData = htmlBgData\[r\] \|\| false;/;
    const newApplyCode = `const isClientData = htmlBgData[r] || false;
                    const rowStyles = htmlStylesData[r] || [];`;
    content = content.replace(applyRegex, newApplyCode);
    
    const targetRowRegex = /if \(isClientData\) \{\n\s*targetRow\.is_client_data = true;\n\s*\}/;
    const newTargetRowCode = `if (isClientData) {
                            targetRow.is_client_data = true;
                        }
                        if (rowStyles.length > 0) {
                            targetRow.styles = rowStyles;
                        }`;
    content = content.replace(targetRowRegex, newTargetRowCode);
    
    // 3. Update tr rendering to NOT use bg-yellow-200 if styles exists, because we apply styles to tds
    // Let's modify the <tr> to still keep its bg-yellow-200 but td can override it.
    // Wait, let's inject style bindings to tds.
    // In all files, tds look like: <td class="w-24 border-r border-gray-300">
    // Let's use a regex to add :style="row.styles ? row.styles[0] : {}" to the first td, etc.
    // This is hard with regex because colIndex varies.
    // Let's dynamically add a helper function getStyle(row, fieldName) ?
    // Or we just add the styles to exportExcel first, and handle UI later.
    
    fs.writeFileSync(`${dir}/${file}`, content, 'utf-8');
    console.log(`Updated paste logic in ${file}`);
}
