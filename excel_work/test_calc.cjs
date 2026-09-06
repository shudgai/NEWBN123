const fs = require('fs');

const content = fs.readFileSync('/home/shudgai999/project/excel_work/resources/views/client_206.blade.php', 'utf-8');

// extract the _calculateFreight function
const start = content.indexOf('const _calculateFreight = (weight, remark, client) => {');
const end = content.indexOf('return amt;', start) + 11;

let funcCode = content.substring(start, end);
// Mock references
funcCode = `
const isAmountManual = { value: false };
` + funcCode;

// test it
funcCode += `
console.log("Test 1:", _calculateFreight(0, "共十九批6.8噸+15噸車", "206"));
console.log("Test 2:", _calculateFreight(0, "共十九批6.8噸+15噸車", "其他"));
`;

fs.writeFileSync('test_func.js', funcCode);
