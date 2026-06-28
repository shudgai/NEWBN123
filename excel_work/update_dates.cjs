const fs = require('fs');
const path = require('path');

const viewsDir = path.join(__dirname, 'resources', 'views');

const files = fs.readdirSync(viewsDir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

for (const file of files) {
    if (file === 'client_206.blade.php') continue;
    
    const filePath = path.join(viewsDir, file);
    let content = fs.readFileSync(filePath, 'utf8');

    let updated = false;

    // Replace default date input
    if (content.includes("date: '115/05/04'")) {
        content = content.replace(/date:\s*'115\/05\/04'/g, "date: '5月4日'");
        updated = true;
    }
    
    // Replace header date range
    if (content.includes("115/05/01-115/05/31")) {
        content = content.replace(/115\/05\/01-115\/05\/31/g, "5月1日-5月31日");
        updated = true;
    }

    if (updated) {
        fs.writeFileSync(filePath, content, 'utf8');
        console.log(`Updated dates in ${file}`);
    }
}
