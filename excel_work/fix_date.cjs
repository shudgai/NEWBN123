const fs = require('fs');
const path = require('path');

const viewsDir = path.join(__dirname, 'resources', 'views');
const files = fs.readdirSync(viewsDir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

for (const file of files) {
    const filePath = path.join(viewsDir, file);
    let content = fs.readFileSync(filePath, 'utf8');
    let updated = false;

    // Remove the bad watch block using string literal for safety
    const watchBlock = "            watch(() => newRow.value.date, (newVal) => {\n                if (newVal) {\n                    const match = newVal.match(/^(\\d{1,2})\\/(\\d{1,2})$/);\n                    if (match) {\n                        newRow.value.date = `${parseInt(match[1])}月${parseInt(match[2])}日`;\n                    }\n                }\n            });\n";
    if (content.includes(watchBlock)) {
        content = content.replace(watchBlock, "");
        updated = true;
    }

    if (file !== 'client_206.blade.php') {
        const oldInput = '<input autocomplete="off" @keyup.enter="addRow" @keydown="handleArrowKeys" type="text" v-model.trim="newRow.date"';
        const newInput = '<input autocomplete="off" @keyup.enter="addRow" @keydown="handleArrowKeys" @change="formatNewDate" type="text" v-model.trim="newRow.date"';
        if (content.includes(oldInput)) {
            content = content.replace(oldInput, newInput);
            updated = true;
        }

        const formatNewDateBlock = `
            const formatNewDate = () => {
                if (newRow.value.date) {
                    const match = newRow.value.date.match(/^(\\d{1,2})\\/(\\d{1,2})$/);
                    if (match) {
                        newRow.value.date = \`\${parseInt(match[1])}月\${parseInt(match[2])}日\`;
                    }
                }
            };
`;
        if (!content.includes('const formatNewDate = () => {')) {
            content = content.replace(
                /(const newRow = ref\(\{)/,
                `${formatNewDateBlock}\n            $1`
            );
            updated = true;
        }
    }

    if (updated) {
        fs.writeFileSync(filePath, content, 'utf8');
        console.log(`Updated ${file}`);
    }
}
