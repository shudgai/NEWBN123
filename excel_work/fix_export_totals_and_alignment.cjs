const fs = require('fs');

const dir = 'resources/views';
const files = fs.readdirSync(dir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

for (let file of files) {
    let content = fs.readFileSync(`${dir}/${file}`, 'utf-8');
    
    // 1. Add Total calculation
    const searchDataPush = `wsData.forEach(row => {
                    aoa.push(Object.values(row));
                });`;
    const replaceDataPush = `let totalPieces = 0, totalWeight = 0, totalAmount = 0;
                wsData.forEach(row => {
                    aoa.push(Object.values(row));
                    totalPieces += (Number(row['件數']) || 0);
                    totalWeight += (Number(row['重量']) || 0);
                    totalAmount += (Number(row['運費']) || 0);
                });
                aoa.push(['', '', '總計', totalPieces, totalWeight, totalAmount, '', '']);`;
    
    content = content.replace(searchDataPush, replaceDataPush);
    
    // 2. Add Column Widths
    const searchSheetAdd = `const ws = XLSX.utils.aoa_to_sheet(aoa);`;
    const replaceSheetAdd = `const ws = XLSX.utils.aoa_to_sheet(aoa);
                ws['!cols'] = [
                    { wch: 15 }, // Date
                    { wch: 25 }, // Client Name
                    { wch: 25 }, // Bill No
                    { wch: 12 }, // Pieces
                    { wch: 12 }, // Weight
                    { wch: 15 }, // Amount
                    { wch: 18 }, // Location
                    { wch: 30 }  // Remark
                ];`;
                
    content = content.replace(searchSheetAdd, replaceSheetAdd);
    
    // 3. Fix alignment and handle total row styling
    const searchLoopStart = `for (let i = 0; i < tableData.value.length; i++) {
                    const rowData = tableData.value[i];`;
    const replaceLoopStart = `for (let i = 0; i <= tableData.value.length; i++) {
                    const rowData = tableData.value[i];`;
                    
    content = content.replace(searchLoopStart, replaceLoopStart);
    
    // 4. Inject formatting inside the loop
    const searchCellInit = `if (!ws[cell_ref].s) ws[cell_ref].s = {};`;
    const replaceCellInit = `if (!ws[cell_ref].s) ws[cell_ref].s = {};
                        
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
                        }`;
                        
    content = content.replace(searchCellInit, replaceCellInit);

    fs.writeFileSync(`${dir}/${file}`, content, 'utf-8');
    console.log(`Fixed totals and alignment in ${file}`);
}
