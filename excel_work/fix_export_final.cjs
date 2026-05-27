const fs = require('fs');

const dir = 'resources/views';
const files = fs.readdirSync(dir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

for (let file of files) {
    let content = fs.readFileSync(`${dir}/${file}`, 'utf-8');
    
    // We want to replace everything from "const ws = XLSX.utils.json_to_sheet(wsData);" 
    // down to "XLSX.writeFile(wb, ..."
    
    const startIndex = content.indexOf('const ws = XLSX.utils.json_to_sheet(wsData);');
    const endIndex = content.indexOf('XLSX.writeFile(wb', startIndex);
    
    if (startIndex === -1 || endIndex === -1) {
        console.log(`Could not find replace range in ${file}`);
        continue;
    }
    
    // Find the end of the XLSX.writeFile line
    const endOfLine = content.indexOf(';', endIndex) + 1;
    
    const originalFilenameMatch = content.substring(endIndex, endOfLine).match(/"([^"]+)"/);
    const filename = originalFilenameMatch ? originalFilenameMatch[1] : "欣華運費明細.xlsx";

    const newCode = `                let minDate = '';
                let maxDate = '';
                let clientName = '';
                if (tableData.value.length > 0) {
                    const dates = tableData.value.map(r => r.date).filter(d => !!d).sort();
                    if (dates.length > 0) {
                        minDate = dates[0];
                        maxDate = dates[dates.length - 1];
                    }
                    clientName = tableData.value[0].client_name || '';
                }
                const dateRange = (minDate && maxDate) ? \`\${minDate}-\${maxDate}\` : '';
                const today = new Date();
                const formattedToday = \`\${today.getFullYear() - 1911}/\${String(today.getMonth()+1).padStart(2, '0')}/\${String(today.getDate()).padStart(2, '0')}\`;
                
                const colHeaders = wsData.length > 0 ? Object.keys(wsData[0]) : [];
                const aoa = [
                    ['', '', '', '', '', '', '', ''],
                    ['運送公司:', '欣華運通有限公司', '叫車公司:', clientName, '', '', '', ''],
                    ['運送日期:', dateRange, '製表日期 :', formattedToday, '', '', '', ''],
                    ['', '', '', '', '', '', '', ''],
                    colHeaders
                ];
                wsData.forEach(row => {
                    aoa.push(Object.values(row));
                });
                const ws = XLSX.utils.aoa_to_sheet(aoa);
                
                // Add styles
                const range = XLSX.utils.decode_range(ws['!ref']);
                for(let R = range.s.r; R <= range.e.r; ++R) {
                    for(let C = range.s.c; C <= range.e.c; ++C) {
                        const cell_address = {c:C, r:R};
                        const cell_ref = XLSX.utils.encode_cell(cell_address);
                        
                        // FIX: Ensure empty cells are created so they can get background color!
                        if(!ws[cell_ref]) ws[cell_ref] = {t:'s', v:''};
                        if (!ws[cell_ref].s) ws[cell_ref].s = {};
                        ws[cell_ref].s.font = { name: "微軟正黑體", sz: 12 };
                        
                        // Header styling for Row 5 (index 4)
                        if (R === 4) {
                            ws[cell_ref].s.border = {
                                top: { style: 'medium', color: { auto: 1 } },
                                bottom: { style: 'medium', color: { auto: 1 } }
                            };
                            ws[cell_ref].s.font.bold = true;
                        }
                    }
                }
                
                // Data rows start at index 5
                const dataStartRow = 5;
                for (let i = 0; i < tableData.value.length; i++) {
                    const rowData = tableData.value[i];
                    const R = dataStartRow + i;
                    for(let C = range.s.c; C <= range.e.c; ++C) {
                        const cell_ref = XLSX.utils.encode_cell({c:C, r:R});
                        
                        // Ensure cell exists
                        if (!ws[cell_ref]) ws[cell_ref] = {t:'s', v:''};
                        if (!ws[cell_ref].s) ws[cell_ref].s = {};
                        
                        const cellStyleIndex = C - range.s.c;
                        const customStyle = rowData.styles ? rowData.styles[cellStyleIndex] : null;
                        
                        // Force yellow background if row is marked as client data
                        if (rowData.is_client_data) {
                            ws[cell_ref].s.fill = { patternType: "solid", fgColor: { rgb: "FFFF00" } };
                        }
                        
                        if (customStyle) {
                            // Background
                            if (customStyle.backgroundColor && !rowData.is_client_data) {
                                let bg = customStyle.backgroundColor;
                                if (bg.includes('255, 255, 0') || bg.toLowerCase().includes('ffff00') || bg.toLowerCase() === 'yellow' || bg.includes('rgb(255, 255,')) {
                                    ws[cell_ref].s.fill = { patternType: "solid", fgColor: { rgb: "FFFF00" } };
                                } else {
                                    const hexMatch = bg.match(/#([0-9a-fA-F]{6})/);
                                    if (hexMatch) {
                                        ws[cell_ref].s.fill = { patternType: "solid", fgColor: { rgb: hexMatch[1].toUpperCase() } };
                                    }
                                }
                            }
                            // Border
                            if (!ws[cell_ref].s.border) ws[cell_ref].s.border = {};
                            ['top', 'bottom', 'left', 'right'].forEach(dir => {
                                const jsProp = 'border' + dir.charAt(0).toUpperCase() + dir.slice(1);
                                if (customStyle[jsProp] || customStyle.border) {
                                    const b = customStyle[jsProp] || customStyle.border;
                                    if (b.includes('thick') || b.includes('medium') || b.includes('2px') || b.includes('3px') || b.includes('1.5pt') || b.includes('2pt')) {
                                        ws[cell_ref].s.border[dir] = { style: "medium", color: { rgb: "000000" } };
                                    } else if (b.includes('thin') || b.includes('.5pt') || b.includes('1px') || b.includes('solid')) {
                                        ws[cell_ref].s.border[dir] = { style: "thin", color: { rgb: "000000" } };
                                    }
                                }
                            });
                        }
                    }
                }
                
                const wb = XLSX.utils.book_new();
                XLSX.utils.book_append_sheet(wb, ws, "運費明細");
                XLSX.writeFile(wb, "${filename}");`;

    const before = content.substring(0, startIndex);
    const after = content.substring(endOfLine);
    fs.writeFileSync(`${dir}/${file}`, before + newCode + after, 'utf-8');
    console.log(`Updated exportExcel fully in ${file}`);
}
