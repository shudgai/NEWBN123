const fs = require('fs');
const path = require('path');

const viewsDir = path.join(__dirname, 'resources', 'views');
const files = fs.readdirSync(viewsDir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

for (const file of files) {
    const filePath = path.join(viewsDir, file);
    let content = fs.readFileSync(filePath, 'utf8');
    let updated = false;

    // We need to inject the split logic right after `if (rowVals.length === 0 || ...) continue;`
    // or right inside `try { let targetRow; ... }`
    // The safest place is right after `const rowVals = plainRows[r];` but before parsing.
    // Wait, rowVals is immutable? No, plainRows[r] is an array, we can modify it.
    // Let's inject it after:
    // const rowVals = plainRows[r];
    // const isClientData = htmlBgData[r] || false;
    
    const targetAnchor = "if (rowVals.length === 0 || (rowVals.length === 1 && rowVals[0] === '')) continue;";
    const injection = `
                    // Handle 7-column merged "Weight Location" Excel format
                    if (rowVals.length === 7) {
                        const weightLoc = rowVals[5].trim();
                        const match1 = weightLoc.match(/^([\\d\\.]+)\\s+([^\\d\\s].*)$/);
                        const match2 = weightLoc.match(/^([\\d\\.]+)([^\\d\\.\\s].*)$/);
                        if (match1) {
                            rowVals.splice(5, 1, match1[1].trim(), match1[2].trim());
                        } else if (match2) {
                            rowVals.splice(5, 1, match2[1].trim(), match2[2].trim());
                        } else if (/^[\\d\\.]+$/.test(weightLoc) || weightLoc === '') {
                            rowVals.splice(5, 1, weightLoc, '');
                        } else {
                            rowVals.splice(5, 1, '', weightLoc);
                        }
                    }
                    // Handle 8-column merged "Weight Location" format when forklift_fee exists (like 639)
                    // If the Excel has 7 columns, but the target table expects 9 columns (with forklift)
                    // Actually, if rowVals length becomes 8 after splice, and fields has 9, 
                    // remark goes into forklift, which is wrong.
                    // Let's just fix rowVals.length == 7 logic.
`;

    if (content.includes(targetAnchor) && !content.includes('Handle 7-column merged "Weight Location" Excel format')) {
        content = content.replace(targetAnchor, targetAnchor + "\n" + injection);
        updated = true;
    }
    
    // BUT WAIT! If fields has 'forklift_fee', it's at index 6!
    // fields = ['date', 'bill_no', 'client_name', 'amount', 'pieces', 'weight', 'forklift_fee', 'location', 'remark']
    // If rowVals has 8 elements (after splice), then rowVals[6] goes to forklift_fee!
    // So we need to shift the array again if forklift_fee exists!
    const fieldsMatch = content.match(/const fields = \['(.*?)'\];/);
    if (fieldsMatch) {
        const fieldsStr = fieldsMatch[1];
        if (fieldsStr.includes('forklift_fee')) {
            // Need to insert an empty forklift_fee at index 6!
            const forkliftInjection = `
                    // If this table has forklift_fee, insert an empty column for it at index 6
                    if (rowVals.length === 8 && !rowVals.includes('forklift_fee_marker_ignore')) {
                        // We assume if it's exactly 8 columns after the weight split, it's missing forklift_fee
                        rowVals.splice(6, 0, '0');
                    }
`;
            if (!content.includes('insert an empty column for it at index 6')) {
                content = content.replace(injection, injection + forkliftInjection);
                updated = true;
            }
        }
    }

    if (updated) {
        fs.writeFileSync(filePath, content, 'utf8');
        console.log(`Updated ${file}`);
    }
}
