const fs = require('fs');
const path = require('path');

const viewsDir = path.join(__dirname, 'resources', 'views');
const files = fs.readdirSync(viewsDir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

for (const file of files) {
    const filePath = path.join(viewsDir, file);
    let content = fs.readFileSync(filePath, 'utf8');
    let updated = false;

    const oldSave = /const manualSave = async \(\) => \{[\s\S]*?setTimeout\(\(\) => \{ showToast\.value = false; \}, 3000\);\s*\};/;
    
    const newSave = `const manualSave = async () => {
                if (document.activeElement && document.activeElement.tagName === 'INPUT') {
                    document.activeElement.blur();
                }
                
                await new Promise(resolve => setTimeout(resolve, 100)); // wait for blur to process
                
                const hasOtherData = newRow.value.bill_no || 
                                     (newRow.value.amount !== null && newRow.value.amount !== '' && newRow.value.amount !== 0) || 
                                     (newRow.value.pieces !== null && newRow.value.pieces !== '' && newRow.value.pieces !== 0) || 
                                     (newRow.value.weight !== null && newRow.value.weight !== '' && newRow.value.weight !== 0) || 
                                     newRow.value.location || 
                                     newRow.value.remark;
                                     
                if (newRow.value.date && newRow.value.client_name && hasOtherData) {
                    await addRow();
                }
                
                toastMessage.value = '資料已確認儲存！';
                showToast.value = true;
                setTimeout(() => { showToast.value = false; }, 3000);
            };`;

    if (content.match(oldSave)) {
        content = content.replace(oldSave, newSave);
        updated = true;
    }

    if (updated) {
        fs.writeFileSync(filePath, content, 'utf8');
        console.log(`Updated ${file}`);
    }
}
