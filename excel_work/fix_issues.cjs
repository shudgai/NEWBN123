const fs = require('fs');
const path = require('path');

const viewsDir = path.join(__dirname, 'resources', 'views');
const files = fs.readdirSync(viewsDir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

for (const file of files) {
    const filePath = path.join(viewsDir, file);
    let content = fs.readFileSync(filePath, 'utf8');
    let updated = false;

    // Fix location missing in updateRow payload
    if (content.includes('forklift_fee: row.forklift_fee || 0,') && !content.includes('location: row.location || \'\',')) {
        content = content.replace(
            /(forklift_fee:\s*row\.forklift_fee\s*\|\|\s*0,\s*remark:\s*row\.remark\s*\|\|\s*'',)/g,
            "forklift_fee: row.forklift_fee || 0,\n                        location: row.location || '',\n                        remark: row.remark || '',"
        );
        updated = true;
    }

    // Fix location missing in handlePaste existing row payload
    if (content.includes('forklift_fee: targetRow.forklift_fee || 0,') && !content.includes('location: targetRow.location || \'\',')) {
        content = content.replace(
            /(forklift_fee:\s*targetRow\.forklift_fee\s*\|\|\s*0,\s*remark:\s*targetRow\.remark\s*\|\|\s*'',)/g,
            "forklift_fee: targetRow.forklift_fee || 0,\n                                location: targetRow.location || '',\n                                remark: targetRow.remark || '',"
        );
        updated = true;
    }

    // Fix date format logic
    if (file !== 'client_206.blade.php') {
        const dateWatchCode = `
            watch(() => newRow.value.date, (newVal) => {
                if (newVal) {
                    const match = newVal.match(/^(\\d{1,2})\\/(\\d{1,2})$/);
                    if (match) {
                        newRow.value.date = \`\${parseInt(match[1])}月\${parseInt(match[2])}日\`;
                    }
                }
            });
`;

        if (!content.includes('watch(() => newRow.value.date')) {
            content = content.replace(
                /(watch\(\[\(\) => newRow\.value\.weight)/,
                `${dateWatchCode}\n            $1`
            );
            updated = true;
        }

        if (content.includes('const updateRow = async (row) => {') && !content.includes('row.date.match(/^(\\d{1,2})\\/(\\d{1,2})$/)')) {
            const updateRowFormatCode = `
                if (row.date) {
                    const match = row.date.match(/^(\\d{1,2})\\/(\\d{1,2})$/);
                    if (match) {
                        row.date = \`\${parseInt(match[1])}月\${parseInt(match[2])}日\`;
                    }
                }
`;
            content = content.replace(
                /(const updateRow = async \(row\) => {\s*try {)/,
                `$1${updateRowFormatCode}`
            );
            updated = true;
        }
    }

    if (updated) {
        fs.writeFileSync(filePath, content, 'utf8');
        console.log(`Updated ${file}`);
    }
}
