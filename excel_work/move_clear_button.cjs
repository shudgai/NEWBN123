const fs = require('fs');
const path = require('path');

const viewsDir = path.join(__dirname, 'resources', 'views');

const files = fs.readdirSync(viewsDir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

for (const file of files) {
    const filePath = path.join(viewsDir, file);
    let content = fs.readFileSync(filePath, 'utf8');

    const clearBtnRegex = /<button\s+@click="clearAllData"[\s\S]*?<\/button>\s*/;
    const match = content.match(clearBtnRegex);
    
    if (match) {
        const btnHtml = match[0].trim();
        
        // Remove it from its original place
        content = content.replace(clearBtnRegex, '');
        
        // Find the scrollToBottom button
        const bottomBtnRegex = /(<button\s+@click="scrollToBottom"[\s\S]*?<\/button>)/;
        
        if (bottomBtnRegex.test(content)) {
            content = content.replace(bottomBtnRegex, (m, p1) => {
                return `<div class="flex gap-2">\n                ` + p1 + '\n                ' + btnHtml + '\n            </div>';
            });
            
            fs.writeFileSync(filePath, content, 'utf8');
            console.log(`Updated ${file}`);
        } else {
             console.log(`scrollToBottom button not found in ${file}`);
        }
    } else {
        console.log(`clearAllData button not found in ${file}`);
    }
}
