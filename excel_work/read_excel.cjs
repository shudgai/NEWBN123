const XLSX = require('xlsx');
const workbook = XLSX.readFile('public/206-2026報價.xlsx');
workbook.SheetNames.forEach(sheetName => {
  console.log(`\n--- Sheet: ${sheetName} ---`);
  const sheet = workbook.Sheets[sheetName];
  const data = XLSX.utils.sheet_to_json(sheet, { header: 1 });
  data.forEach((row, index) => {
    if (row.length > 0) {
      console.log(`${index}: ${row.join(" | ")}`);
    }
  });
});
