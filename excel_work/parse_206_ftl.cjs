const XLSX = require('xlsx');
const workbook = XLSX.readFile('public/206-2026報價.xlsx');
const sheet = workbook.Sheets[workbook.SheetNames[0]];
const data = XLSX.utils.sheet_to_json(sheet, { header: 1 });
for(let i=20; i<45; i++) {
  if (data[i]) console.log(i, data[i].join(" | "));
}
