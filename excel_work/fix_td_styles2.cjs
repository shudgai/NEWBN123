const fs = require('fs');

const dir = 'resources/views';
const files = fs.readdirSync(dir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

for (let file of files) {
    let content = fs.readFileSync(`${dir}/${file}`, 'utf-8');
    
    const fields = {
        'client_206': ['date', 'client_name', 'bill_no', 'pieces', 'weight', 'amount', 'remark'],
        'client_225': ['date', 'client_name', 'bill_no', 'pieces', 'weight', 'amount', 'location', 'remark'],
        'client_276': ['date', 'client_name', 'bill_no', 'pieces', 'weight', 'amount', 'location', 'remark'],
        'client_444': ['date', 'client_name', 'bill_no', 'pieces', 'weight', 'amount', 'remark'],
        'client_639': ['date', 'client_name', 'bill_no', 'pieces', 'weight', 'amount', 'forklift_fee', 'remark']
    };
    
    const fileFields = fields[file.replace('.blade.php', '')];
    if (fileFields) {
        fileFields.forEach((field, index) => {
            // Find the <td> that contains the v-model for this field
            const tdRegex = new RegExp(`<td([^>]*)>\\s*<input([^>]*?)v-model(?:\\.\\w+)?="row\\.${field}"`, 'g');
            content = content.replace(tdRegex, (match, p1, p2) => {
                if (p1.includes(':style="getCellStyle(row')) return match;
                
                const vModelMatch = match.match(/v-model(?:\.\w+)?="row\.\w+"/);
                if (!vModelMatch) return match;
                
                return `<td${p1} :style="getCellStyle(row, ${index})"><input${p2}${vModelMatch[0]}`;
            });
            
            // And for textarea if remark
            const tdTextareaRegex = new RegExp(`<td([^>]*)>\\s*<textarea([^>]*?)v-model(?:\\.\\w+)?="row\\.${field}"`, 'g');
            content = content.replace(tdTextareaRegex, (match, p1, p2) => {
                if (p1.includes(':style="getCellStyle(row')) return match;
                
                const vModelMatch = match.match(/v-model(?:\.\w+)?="row\.\w+"/);
                if (!vModelMatch) return match;
                
                return `<td${p1} :style="getCellStyle(row, ${index})"><textarea${p2}${vModelMatch[0]}`;
            });
        });
    }

    fs.writeFileSync(`${dir}/${file}`, content, 'utf-8');
    console.log(`Fixed TD styles in ${file}`);
}
