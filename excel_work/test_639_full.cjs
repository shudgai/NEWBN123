const fs = require('fs');
const content = fs.readFileSync('/home/shudgai999/project/excel_work/resources/views/client_639.blade.php', 'utf-8');

const regex = /const _calculateFreight = \(weight, remark\) => \{([\s\S]*?)return basePrice;\n            \};/m;
const match = content.match(regex);
if (match) {
    const funcBody = match[1] + "return basePrice;";
    const func = new Function('weight', 'remark', funcBody);
    console.log("Func result:", func(278, "三重"));
} else {
    console.log("Not found");
}
