const fs = require('fs');

const dir = 'resources/views';
const files = fs.readdirSync(dir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

for (let file of files) {
    let content = fs.readFileSync(`${dir}/${file}`, 'utf-8');
    
    // Add getCellStyle function
    if (!content.includes('const getCellStyle = ')) {
        const setupRegex = /const handleArrowKeys = \(e, rowIndex, colIndex\) => \{/;
        content = content.replace(setupRegex, `const getCellStyle = (row, colIndex) => {
                    if (!row || !row.styles || !row.styles[colIndex]) return {};
                    return row.styles[colIndex];
                };\n\n                const handleArrowKeys = (e, rowIndex, colIndex) => {`);
                
        // Return getCellStyle from setup
        content = content.replace('exportExcel,', 'exportExcel,\n                getCellStyle,');
    }
    
    // Modify tds to include :style="getCellStyle(row, 0)" etc.
    // We will do this manually for each field since they are hardcoded.
    const fields = {
        'client_206': ['date', 'client_name', 'bill_no', 'pieces', 'weight', 'amount', 'remark'],
        'client_225': ['date', 'client_name', 'bill_no', 'pieces', 'weight', 'amount', 'location', 'remark'],
        'client_276': ['date', 'client_name', 'bill_no', 'pieces', 'weight', 'amount', 'location', 'remark'],
        'client_444': ['date', 'client_name', 'bill_no', 'pieces', 'weight', 'amount', 'remark'],
        'client_639': ['date', 'client_name', 'bill_no', 'pieces', 'weight', 'amount', 'forklift_fee', 'remark']
    };
    
    const fileFields = fields[file.replace('.blade.php', '')];
    if (fileFields) {
        fileFields.forEach((field, index) => {
            const vModel = `v-model="row.${field}"`;
            // Find the td containing this v-model
            // It might look like: <td class="w-24 border-r border-gray-300"><input type="text" v-model="row.date"
            const tdRegex = new RegExp(`<td([^>]*)>\\s*<input[^>]*v-model="row\\.${field}"`, 'g');
            content = content.replace(tdRegex, (match, p1) => {
                if (p1.includes(':style=')) return match; // already added
                return `<td${p1} :style="getCellStyle(row, ${index})">\n                                    <input type="text" v-model="row.${field}"`;
            });
            // also support textarea for remark
            const tdTextareaRegex = new RegExp(`<td([^>]*)>\\s*<textarea[^>]*v-model="row\\.${field}"`, 'g');
            content = content.replace(tdTextareaRegex, (match, p1) => {
                if (p1.includes(':style=')) return match;
                return `<td${p1} :style="getCellStyle(row, ${index})">\n                                    <textarea v-model="row.${field}"`;
            });
        });
    }

    // Now update exportExcel to use row.styles
    // The previous upgrade_export.cjs added a loop that checks is_client_data.
    // Let's replace the whole dataStartRow block to apply styles correctly.
    
    const styleExportRegex = /\/\/ Find data rows and apply yellow background[\s\S]*?const wb = XLSX\.utils\.book_new\(\);/;
    
    const newStyleExportCode = `// Find data rows and apply custom styles
                let dataStartRow = -1;
                for(let R = range.s.r; R <= range.e.r; ++R) {
                    let isHeader = false;
                    for(let C = range.s.c; C <= range.e.c; ++C) {
                        const cell = ws[XLSX.utils.encode_cell({c:C, r:R})];
                        if (cell && (cell.v === '重量' || cell.v === '件數' || cell.v === '運費')) {
                            isHeader = true;
                        }
                    }
                    if (isHeader) {
                        dataStartRow = R + 1;
                        break;
                    }
                }
                
                if (dataStartRow !== -1) {
                    for (let i = 0; i < tableData.value.length; i++) {
                        const rowData = tableData.value[i];
                        const R = dataStartRow + i;
                        for(let C = range.s.c; C <= range.e.c; ++C) {
                            const cell_ref = XLSX.utils.encode_cell({c:C, r:R});
                            if (!ws[cell_ref]) continue;
                            if (!ws[cell_ref].s) ws[cell_ref].s = {};
                            
                            const cellStyleIndex = C - range.s.c; // Assuming columns map directly
                            const customStyle = rowData.styles ? rowData.styles[cellStyleIndex] : null;
                            
                            if (customStyle) {
                                // Background
                                if (customStyle.backgroundColor) {
                                    // simple hex conversion if needed, but rgb is tricky. 
                                    // if it's already hex, use it. if rgb, we could try to convert, but let's just use FFFF00 if it has any yellow.
                                    // SheetJS expects FFFF00 format.
                                    let bg = customStyle.backgroundColor;
                                    if (bg.includes('255, 255, 0') || bg.toLowerCase().includes('ffff00') || bg.toLowerCase() === 'yellow' || bg.includes('rgb(255, 255,')) {
                                        ws[cell_ref].s.fill = { fgColor: { rgb: "FFFF00" } };
                                    } else {
                                        // Try to extract hex
                                        const hexMatch = bg.match(/#([0-9a-fA-F]{6})/);
                                        if (hexMatch) {
                                            ws[cell_ref].s.fill = { fgColor: { rgb: hexMatch[1].toUpperCase() } };
                                        }
                                    }
                                }
                                // Border
                                ['top', 'bottom', 'left', 'right'].forEach(dir => {
                                    const jsProp = 'border' + dir.charAt(0).toUpperCase() + dir.slice(1);
                                    if (customStyle[jsProp] || customStyle.border) {
                                        const b = customStyle[jsProp] || customStyle.border;
                                        if (b.includes('thick') || b.includes('medium') || b.includes('2px') || b.includes('3px')) {
                                            ws[cell_ref].s.border[dir] = { style: "medium", color: { rgb: "000000" } };
                                        }
                                    }
                                });
                            }
                        }
                    }
                }
                
                const wb = XLSX.utils.book_new();`;

    content = content.replace(styleExportRegex, newStyleExportCode);
    
    fs.writeFileSync(`${dir}/${file}`, content, 'utf-8');
    console.log(`Updated UI and export styles in ${file}`);
}
