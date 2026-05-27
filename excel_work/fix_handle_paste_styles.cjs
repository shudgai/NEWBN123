const fs = require('fs');

const dir = 'resources/views';
const files = fs.readdirSync(dir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

for (let file of files) {
    let content = fs.readFileSync(`${dir}/${file}`, 'utf-8');
    
    // Replace the targetRow.styles assignment
    const searchCode = `if (rowStyles.length > 0) {
                            targetRow.styles = rowStyles;
                        }`;
                        
    // We want to merge the pasted styles into targetRow.styles aligned with startColIndex
    const replaceCode = `if (rowStyles.length > 0) {
                            if (!targetRow.styles) targetRow.styles = [];
                            // Ensure the array has enough elements
                            while(targetRow.styles.length < fields.length) targetRow.styles.push({});
                            
                            // Align pasted styles with the columns
                            for (let i = 0; i < rowStyles.length; i++) {
                                if (startColIndex + i < fields.length) {
                                    targetRow.styles[startColIndex + i] = rowStyles[i];
                                }
                            }
                            
                            // Force reactivity update in Vue by replacing the array reference
                            targetRow.styles = [...targetRow.styles];
                        }`;

    // There might be variations in whitespace, let's use a regex
    const regex = /if \(rowStyles\.length > 0\) \{\n\s*targetRow\.styles = rowStyles;\n\s*\}/g;
    content = content.replace(regex, replaceCode);

    fs.writeFileSync(`${dir}/${file}`, content, 'utf-8');
    console.log(`Fixed handlePaste styles in ${file}`);
}
