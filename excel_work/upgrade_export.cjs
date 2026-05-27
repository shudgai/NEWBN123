const fs = require('fs');

const dir = 'resources/views';
const files = fs.readdirSync(dir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

for (let file of files) {
    let content = fs.readFileSync(`${dir}/${file}`, 'utf-8');
    
    // 1. Replace script source
    content = content.replace(/https:\/\/cdn\.sheetjs\.com\/xlsx-latest\/package\/dist\/xlsx\.full\.min\.js/g, 'https://cdn.jsdelivr.net/npm/xlsx-js-style@1.2.0/dist/xlsx.bundle.js');
    
    // 2. Modify exportExcel function to add styles
    const exportRegex = /const exportExcel = \(\) => \{([\s\S]*?)XLSX\.writeFile\(wb, "([^"]+)"\);\n\s*\};/;
    const match = content.match(exportRegex);
    
    if (match) {
        let innerCode = match[1];
        const filename = match[2];
        
        // Let's inject styling loop before wb creation
        // We know that tableData length is the number of data rows.
        // And there's a "總計" row at the end.
        
        const injectPoint = 'const wb = XLSX.utils.book_new();';
        const stylingCode = `
                // Add styles
                const range = XLSX.utils.decode_range(ws['!ref']);
                for(let R = range.s.r; R <= range.e.r; ++R) {
                    for(let C = range.s.c; C <= range.e.c; ++C) {
                        const cell_address = {c:C, r:R};
                        const cell_ref = XLSX.utils.encode_cell(cell_address);
                        if(!ws[cell_ref]) ws[cell_ref] = {t:'s', v:''};
                        
                        let isYellow = false;
                        let isHeader = false;
                        
                        // Heuristic to find if it's a data row and is_client_data
                        // For 225, 276, 444, 639 headers are 2 or 3 rows.
                        // Let's just say if the row has a date matching tableData it might be it, 
                        // or just rely on the fact that data rows are between headers and "總計"
                        
                        // To be exact, in our code we construct aoa.
                        // Let's check tableData.value. If it has is_client_data, we want it yellow.
                        // Actually, we can just map row index in aoa back to tableData.
                        // Wait, easier: when constructing aoa, we don't have a direct map.
                        // We can just rely on R >= headerOffset.
                        
                        // We can just set border to all cells.
                        if (!ws[cell_ref].s) ws[cell_ref].s = {};
                        ws[cell_ref].s.border = {
                            top: { style: "thin", color: { rgb: "000000" } },
                            bottom: { style: "thin", color: { rgb: "000000" } },
                            left: { style: "thin", color: { rgb: "000000" } },
                            right: { style: "thin", color: { rgb: "000000" } }
                        };
                        ws[cell_ref].s.font = { name: "微軟正黑體", sz: 11 };
                        
                        // Check if it's a data row with is_client_data
                        // Since all files have different header rows (206 has 1, 225 has 3, etc.)
                        // we'll just check if the row content matches
                    }
                }
                
                // Second pass to apply yellow color by matching data
                let dataStartRow = -1;
                // find the row that contains "日期" and "客戶名稱"
                for(let R = range.s.r; R <= range.e.r; ++R) {
                    let hasDate = false;
                    for(let C = range.s.c; C <= range.e.c; ++C) {
                        const cell = ws[XLSX.utils.encode_cell({c:C, r:R})];
                        if (cell && cell.v === '日期') hasDate = true;
                    }
                    if (hasDate) {
                        dataStartRow = R + 1;
                        break;
                    }
                }
                
                if (dataStartRow !== -1) {
                    for (let i = 0; i < tableData.value.length; i++) {
                        const rowData = tableData.value[i];
                        if (rowData.is_client_data) {
                            const R = dataStartRow + i;
                            for(let C = range.s.c; C <= range.e.c; ++C) {
                                const cell_ref = XLSX.utils.encode_cell({c:C, r:R});
                                if (ws[cell_ref] && ws[cell_ref].s) {
                                    ws[cell_ref].s.fill = { fgColor: { rgb: "FFFF00" } };
                                }
                            }
                        }
                    }
                }
                
                `;
                
        // For client_206 it might not use "日期", it uses "結帳日".
        // Let's modify the heuristic: Find header row by checking for common fields like "重量", "件數", "運費"
        
        const betterStylingCode = `
                // Add styles
                const range = XLSX.utils.decode_range(ws['!ref']);
                for(let R = range.s.r; R <= range.e.r; ++R) {
                    for(let C = range.s.c; C <= range.e.c; ++C) {
                        const cell_address = {c:C, r:R};
                        const cell_ref = XLSX.utils.encode_cell(cell_address);
                        if(!ws[cell_ref]) ws[cell_ref] = {t:'s', v:''};
                        
                        if (!ws[cell_ref].s) ws[cell_ref].s = {};
                        ws[cell_ref].s.border = {
                            top: { style: "thin", color: { rgb: "000000" } },
                            bottom: { style: "thin", color: { rgb: "000000" } },
                            left: { style: "thin", color: { rgb: "000000" } },
                            right: { style: "thin", color: { rgb: "000000" } }
                        };
                        ws[cell_ref].s.font = { name: "微軟正黑體", sz: 12 };
                    }
                }
                
                // Find data rows and apply yellow background
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
                        if (rowData.is_client_data) {
                            const R = dataStartRow + i;
                            for(let C = range.s.c; C <= range.e.c; ++C) {
                                const cell_ref = XLSX.utils.encode_cell({c:C, r:R});
                                if (ws[cell_ref] && ws[cell_ref].s) {
                                    ws[cell_ref].s.fill = { fgColor: { rgb: "FFFF00" } };
                                }
                            }
                        }
                    }
                }
                
                const wb = XLSX.utils.book_new();`;

        let replacedInner = innerCode.replace('const wb = XLSX.utils.book_new();', betterStylingCode);
        
        // Also if it uses json_to_sheet (like client_225 might have done before we fixed them? wait 225 uses json_to_sheet)
        if (replacedInner.includes('json_to_sheet')) {
             replacedInner = replacedInner.replace('const ws = XLSX.utils.json_to_sheet(wsData);', `const ws = XLSX.utils.json_to_sheet(wsData);
             
                // json_to_sheet puts headers at row 0. So data starts at row 1.
                // Wait, if it's json_to_sheet, we can just say dataStartRow = 1
             `);
        }
        
        const newExportCode = `const exportExcel = () => {${replacedInner}XLSX.writeFile(wb, "${filename}");\n            };`;
        content = content.replace(exportRegex, newExportCode);
        
        fs.writeFileSync(`${dir}/${file}`, content, 'utf-8');
        console.log(`Updated ${file}`);
    }
}
