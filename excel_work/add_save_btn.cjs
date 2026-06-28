const fs = require('fs');
const path = require('path');

const viewsDir = path.join(__dirname, 'resources', 'views');
const files = fs.readdirSync(viewsDir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

for (const file of files) {
    const filePath = path.join(viewsDir, file);
    let content = fs.readFileSync(filePath, 'utf8');
    let updated = false;

    // Inject manualSave function
    if (!content.includes('const manualSave = async () => {')) {
        content = content.replace(
            /(const resetView = async \(\) => \{)/,
            `const manualSave = async () => {
                if (document.activeElement && document.activeElement.tagName === 'INPUT') {
                    document.activeElement.blur();
                }
                
                toastMessage.value = '資料已確認儲存！';
                showToast.value = true;
                setTimeout(() => { showToast.value = false; }, 3000);
            };
            
            $1`
        );
        updated = true;
    }

    // Inject the button
    if (!content.includes('儲存資料</button>')) {
        content = content.replace(
            /<button @click="exportExcel"/,
            `<button @click="manualSave" class="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded shadow transition-colors">
                儲存資料
            </button>
            <button @click="exportExcel"`
        );
        updated = true;
    }

    if (updated) {
        fs.writeFileSync(filePath, content, 'utf8');
        console.log(`Updated ${file}`);
    }
}
