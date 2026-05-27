const XLSX = require('xlsx');
const workbook = XLSX.readFile('public/20260419欣葦運費(油價變動).xlsx');
const sheetNames = workbook.SheetNames;
console.log("Sheets:", sheetNames);

sheetNames.forEach(sheetName => {
    console.log(`\n--- Sheet: ${sheetName} ---`);
    const worksheet = workbook.Sheets[sheetName];
    const data = XLSX.utils.sheet_to_json(worksheet, { header: 1 });
    // Print first 20 rows to understand the structure
    data.slice(0, 20).forEach((row, i) => {
        console.log(`Row ${i}:`, row);
    });
});
