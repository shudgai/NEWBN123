const XLSX = require('xlsx');
const workbook = XLSX.readFile('public/206-2026報價.xlsx');
const sheetNames = workbook.SheetNames;
console.log("Sheets:", sheetNames);

sheetNames.forEach(sheetName => {
    console.log(`\n--- Sheet: ${sheetName} ---`);
    const worksheet = workbook.Sheets[sheetName];
    const data = XLSX.utils.sheet_to_json(worksheet, { header: 1 });
    // Print first 50 rows
    data.slice(0, 50).forEach((row, i) => {
        console.log(`Row ${i}:`, row);
    });
});
