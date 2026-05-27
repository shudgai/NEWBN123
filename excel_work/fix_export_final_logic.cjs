const fs = require('fs');

const dir = 'resources/views';
const files = fs.readdirSync(dir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

for (let file of files) {
    let content = fs.readFileSync(`${dir}/${file}`, 'utf-8');
    
    // 1. Fix the first loop: it currently has `if (i === tableData.value.length)` which causes ReferenceError!
    // Let's replace the ENTIRE first loop body from `if (!ws[cell_ref].s) ws[cell_ref].s = {};` to `ws[cell_ref].s.font.bold = true; } } }`
    
    // A safer way is to just use regex to replace the faulty block.
    // The faulty block is:
    /*
                        // Default font for all data cells
                        ws[cell_ref].s.font = { name: "微軟正黑體", sz: 12 };
                        
                        // Right-align numeric columns
                        if (C === 3 || C === 4 || C === 5) {
                            ws[cell_ref].s.alignment = { horizontal: "right" };
                        }
                        
                        if (i === tableData.value.length) {
                            // Total row styling
                            if (C === 2) ws[cell_ref].s.alignment = { horizontal: "right" };
                            ws[cell_ref].s.font = { name: "微軟正黑體", sz: 12, bold: true };
                            ws[cell_ref].s.border = {
                                top: { style: 'thin', color: { auto: 1 } },
                                bottom: { style: 'double', color: { auto: 1 } }
                            };
                            continue;
                        }
    */
    content = content.replace(/\/\/ Default font for all data cells[\s\S]*?continue;\n\s*\}/g, '');
    
    // Now we need to insert the correct logic in the first loop.
    // The original first loop just had: `ws[cell_ref].s.font = { name: "微軟正黑體", sz: 12 };`
    // And then `if (R === 4) { ... }`
    
    // Let's find: `if (!ws[cell_ref].s) ws[cell_ref].s = {};` (first occurrence)
    // Actually, because of my previous replace, the first loop might have two `ws[cell_ref].s.font = ...`
    // Let's just completely replace the first loop block.
    const searchFirstLoop = `for(let R = range.s.r; R <= range.e.r; ++R) {
                    for(let C = range.s.c; C <= range.e.c; ++C) {
                        const cell_address = {c:C, r:R};
                        const cell_ref = XLSX.utils.encode_cell(cell_address);
                        
                        // FIX: Ensure empty cells are created so they can get background color!
                        if(!ws[cell_ref]) ws[cell_ref] = {t:'s', v:''};
                        if (!ws[cell_ref].s) ws[cell_ref].s = {};`;
                        
    // Wait, the safest way is to replace the whole `// Add styles` to `// Data rows start at index 5`
    const wholeBlockRegex = /\/\/ Add styles[\s\S]*?\/\/ Data rows start at index 5/g;
    
    const correctFirstLoop = `// Add styles
                const range = XLSX.utils.decode_range(ws['!ref']);
                for(let R = range.s.r; R <= range.e.r; ++R) {
                    for(let C = range.s.c; C <= range.e.c; ++C) {
                        const cell_address = {c:C, r:R};
                        const cell_ref = XLSX.utils.encode_cell(cell_address);
                        
                        // FIX: Ensure empty cells are created so they can get background color!
                        if(!ws[cell_ref]) ws[cell_ref] = {t:'s', v:''};
                        if (!ws[cell_ref].s) ws[cell_ref].s = {};
                        ws[cell_ref].s.font = { name: "微軟正黑體", sz: 12 };
                        
                        // Right-align numeric columns (Pieces, Weight, Amount)
                        if (C === 3 || C === 4 || C === 5) {
                            ws[cell_ref].s.alignment = { horizontal: "right" };
                        }
                        
                        // Header styling for Row 5 (index 4)
                        if (R === 4) {
                            ws[cell_ref].s.border = {
                                top: { style: 'medium', color: { auto: 1 } },
                                bottom: { style: 'medium', color: { auto: 1 } }
                            };
                            ws[cell_ref].s.font.bold = true;
                        }
                        
                        // Total row styling (last row)
                        if (R === range.e.r && R > 4) {
                            if (C === 2) ws[cell_ref].s.alignment = { horizontal: "right" };
                            ws[cell_ref].s.font = { name: "微軟正黑體", sz: 12, bold: true };
                            ws[cell_ref].s.border = {
                                top: { style: 'thin', color: { auto: 1 } },
                                bottom: { style: 'double', color: { auto: 1 } }
                            };
                        }
                    }
                }
                
                // Data rows start at index 5`;
                
    content = content.replace(wholeBlockRegex, correctFirstLoop);
    
    // Now fix the second loop. We want it to be `< tableData.value.length` instead of `<=`, 
    // because the total row doesn't have custom styles from `tableData`!
    const searchSecondLoop = `for (let i = 0; i <= tableData.value.length; i++) {`;
    const replaceSecondLoop = `for (let i = 0; i < tableData.value.length; i++) {`;
    content = content.replace(searchSecondLoop, replaceSecondLoop);
    
    // Also remove any stray `ws[cell_ref].s.font = { name: "微軟正黑體", sz: 12 };` that might be left in the first loop body.
    
    fs.writeFileSync(`${dir}/${file}`, content, 'utf-8');
    console.log(`Fixed logic error in exportExcel for ${file}`);
}
