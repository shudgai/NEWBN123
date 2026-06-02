const fs = require('fs');
const content = fs.readFileSync('resources/views/client_276.blade.php', 'utf8');
const match = content.match(/const calculateFreight = \(weight, remark\) => \{([\s\S]*?)return amount;\n            \};/);
if (match) {
    const fnBody = match[1] + 'return amount;';
    const calculateFreight = new Function('weight', 'remark', fnBody);
    
    console.log("3.49噸, 冷泉港:", calculateFreight(0, "冷泉港 3.49噸"));
    console.log("20kg, 冷泉港:", calculateFreight(20, "冷泉港"));
    console.log("50kg, 冷泉港:", calculateFreight(50, "冷泉港"));
    console.log("301kg, 冷泉港:", calculateFreight(301, "冷泉港"));
} else {
    console.log("Could not parse function");
}
