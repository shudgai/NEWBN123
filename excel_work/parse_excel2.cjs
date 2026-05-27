const XLSX = require('xlsx');
const workbook = XLSX.readFile('public/20260419欣葦運費(油價變動).xlsx');
const sheetName = workbook.SheetNames[0];
const worksheet = workbook.Sheets[sheetName];
const data = XLSX.utils.sheet_to_json(worksheet, { header: 1 });
data.slice(20, 50).forEach((row, i) => {
    console.log(`Row ${i+20}:`, row);
});
