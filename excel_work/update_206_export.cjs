const fs = require('fs');

const file = 'resources/views/client_206.blade.php';
let content = fs.readFileSync(file, 'utf-8');

const exportFuncRegex = /const exportExcel = \(\) => \{[\s\S]*?XLSX\.writeFile\(wb, [^;]+;\n\s*\};/;

const newExportFunc = `const exportExcel = () => {
                if (typeof XLSX === 'undefined') {
                    alert('Excel 匯出模組尚未載入完成，請稍後再試。');
                    return;
                }
                const wsData = tableData.value.map(row => ({
                    '運送日期': row.date,
                    '帳單編號': row.bill_no,
                    '客戶名稱': row.client_name,
                    ' ': '', // Empty column for logo
                    '運費金額': row.amount,
                    '  ': '', // Empty column for logo
                    '件數': row.pieces,
                    '重量': row.weight,
                    '備註': row.remark
                }));
                
                let minDate = '';
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
                    ['', '', '', '', '', '', '', '', ''],
                    ['運送公司:', '欣華運通有限公司', '', '叫車公司:', clientName, '', '', '', ''],
                    ['運送日期:', dateRange, '', '製表日期 :', formattedToday, '', '', '', ''],
                    ['', '', '', '', '', '', '', '', ''],
                    colHeaders
                ];
                
                let totalPieces = 0, totalWeight = 0, totalAmount = 0;
                wsData.forEach(row => {
                    aoa.push(Object.values(row));
                    totalPieces += (Number(row['件數']) || 0);
                    totalWeight += (Number(row['重量']) || 0);
                    totalAmount += (Number(row['運費金額']) || 0);
                });
                // Total row (9 columns)
                aoa.push(['', '', '總計', '', totalAmount, '', totalPieces, totalWeight, '']);
                
                const ws = XLSX.utils.aoa_to_sheet(aoa);
                ws['!cols'] = [
                    { wch: 15 }, // Date
                    { wch: 20 }, // Bill No
                    { wch: 25 }, // Client Name
                    { wch: 8 },  // Logo 1
                    { wch: 15 }, // Amount
                    { wch: 8 },  // Logo 2
                    { wch: 10 }, // Pieces
                    { wch: 10 }, // Weight
                    { wch: 30 }  // Remark
                ];
                
                // Add styles
                const range = XLSX.utils.decode_range(ws['!ref']);
                for(let R = range.s.r; R <= range.e.r; ++R) {
                    for(let C = range.s.c; C <= range.e.c; ++C) {
                        const cell_address = {c:C, r:R};
                        const cell_ref = XLSX.utils.encode_cell(cell_address);
                        
                        if(!ws[cell_ref]) ws[cell_ref] = {t:'s', v:''};
                        if (!ws[cell_ref].s) ws[cell_ref].s = {};
                        ws[cell_ref].s.font = { name: "微軟正黑體", sz: 12 };
                        
                        // Right-align numeric columns: Amount(4), Pieces(6), Weight(7)
                        if (C === 4 || C === 6 || C === 7) {
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
                
                // Data rows start at index 5
                const dataStartRow = 5;
                for (let i = 0; i < tableData.value.length; i++) {
                    const rowData = tableData.value[i];
                    const R = dataStartRow + i;
                    for(let C = range.s.c; C <= range.e.c; ++C) {
                        const cell_ref = XLSX.utils.encode_cell({c:C, r:R});
                        if (!ws[cell_ref]) ws[cell_ref] = {t:'s', v:''};
                        if (!ws[cell_ref].s) ws[cell_ref].s = {};
                        
                        // Map export column C to UI style index
                        let cellStyleIndex = -1;
                        if (C === 0) cellStyleIndex = 0; // date
                        else if (C === 1) cellStyleIndex = 1; // bill_no
                        else if (C === 2) cellStyleIndex = 2; // client_name
                        else if (C === 4) cellStyleIndex = 3; // amount
                        else if (C === 6) cellStyleIndex = 4; // pieces
                        else if (C === 7) cellStyleIndex = 5; // weight
                        else if (C === 8) cellStyleIndex = 7; // remark
                        
                        const customStyle = (cellStyleIndex >= 0 && rowData.styles) ? rowData.styles[cellStyleIndex] : null;
                        
                        if (customStyle) {
                            if (customStyle.backgroundColor) {
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
                XLSX.writeFile(wb, "206公成興運費明細.xlsx");
            };`;

if (exportFuncRegex.test(content)) {
    content = content.replace(exportFuncRegex, newExportFunc);
    fs.writeFileSync(file, content, 'utf-8');
    console.log('Successfully replaced exportExcel in client_206.blade.php');
} else {
    console.log('Regex did not match!');
}
