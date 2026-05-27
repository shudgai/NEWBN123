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
            // we look for v-model, v-model.trim, v-model.number
            const tdRegex = new RegExp(`<td([^>]*)>\\s*<input([^>]*?)v-model(?:\\.\\w+)?="row\\.${field}"`, 'g');
            content = content.replace(tdRegex, (match, p1, p2) => {
                if (p1.includes(':style="getCellStyle(row')) return match;
                return `<td${p1} :style="getCellStyle(row, ${index})"><input${p2}v-model="row.${field}"`.replace(`v-model="row.${field}"`, match.match(/v-model(?:\\.\\w+)?="row\\.\\w+"/)[0]);
            });
            // What if it's already there? The check above prevents it.
            // Let's do it simply: find `<td class="p-0 relative group" ...><input ... v-model.trim="row.date"`
            // Wait, my replacement logic above is a bit complex. Let's write a simpler regex.
        });
    }

    fs.writeFileSync(`${dir}/${file}`, content, 'utf-8');
    console.log(`Fixed TD styles in ${file}`);
}
