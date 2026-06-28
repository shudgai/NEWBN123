const fs = require('fs');
const path = require('path');

const viewsDir = path.join(__dirname, 'resources', 'views');
const files = fs.readdirSync(viewsDir).filter(f => f.startsWith('client_') && f.endsWith('.blade.php'));

const parseFunc = `
            const parseAndFormatDate = (dateStr) => {
                if (!dateStr || typeof dateStr !== 'string') return dateStr;
                let m = null, d = null;
                const slashMatch = dateStr.match(/^(\\d{1,2})[\\/\\-](\\d{1,2})$/);
                if (slashMatch) {
                    m = parseInt(slashMatch[1], 10);
                    d = parseInt(slashMatch[2], 10);
                } else if (/^\\d{3,4}$/.test(dateStr)) {
                    if (dateStr.length === 4) {
                        m = parseInt(dateStr.substring(0, 2), 10);
                        d = parseInt(dateStr.substring(2, 4), 10);
                    } else if (dateStr.length === 3) {
                        m = parseInt(dateStr.substring(0, 1), 10);
                        d = parseInt(dateStr.substring(1, 3), 10);
                    }
                }
                if (m !== null && d !== null && m >= 1 && m <= 12 && d >= 1 && d <= 31) {
                    return \`\${m}月\${d}日\`;
                }
                return dateStr;
            };
`;

const handleFillUpBody = `
                let baseMonth = null;
                let baseDay = null;
                let baseYear = null;
                let dateType = null;
                
                if (field === 'date' && typeof value === 'string') {
                    const matchZh = value.match(/^(\\d{1,2})月(\\d{1,2})日$/);
                    const matchTw = value.match(/^(\\d{2,3})\\/(\\d{1,2})\\/(\\d{1,2})$/);
                    if (matchZh) {
                        baseMonth = parseInt(matchZh[1]);
                        baseDay = parseInt(matchZh[2]);
                        dateType = 'zh';
                    } else if (matchTw) {
                        baseYear = parseInt(matchTw[1]);
                        baseMonth = parseInt(matchTw[2]);
                        baseDay = parseInt(matchTw[3]);
                        dateType = 'tw';
                    }
                }

                for (let i = minIdx; i <= maxIdx; i++) {
                    if (i === startIdx) continue;
                    
                    if (field === 'selected') {
                        const rowId = tableData.value[i].id;
                        if (value === true && !selectedRows.value.includes(rowId)) {
                            selectedRows.value.push(rowId);
                        } else if (value === false) {
                            selectedRows.value = selectedRows.value.filter(id => id !== rowId);
                        }
                        continue;
                    }

                    let newValue = value;
                    if (field === 'date' && dateType !== null) {
                        const daysToAdd = i - startIdx;
                        const y = dateType === 'tw' ? (baseYear + 1911) : 2026;
                        const tempDate = new Date(y, baseMonth - 1, baseDay + daysToAdd);
                        
                        if (dateType === 'zh') {
                            newValue = \`\${tempDate.getMonth() + 1}月\${tempDate.getDate()}日\`;
                        } else if (dateType === 'tw') {
                            const newTwYear = tempDate.getFullYear() - 1911;
                            const mm = String(tempDate.getMonth() + 1).padStart(2, '0');
                            const dd = String(tempDate.getDate()).padStart(2, '0');
                            newValue = \`\${newTwYear}/\${mm}/\${dd}\`;
                        }
                    }

                    tableData.value[i][field] = newValue;
`;

for (const file of files) {
    const filePath = path.join(viewsDir, file);
    let content = fs.readFileSync(filePath, 'utf8');
    let updated = false;

    // Feature 1: Add @focus to select all text
    const inputMatches = content.match(/<input[^>]+class="nav-input[^>]+>/g);
    if (inputMatches) {
        for (const match of inputMatches) {
            if (!match.includes('@focus=')) {
                const newMatch = match.replace('>', ' @focus="$event.target.select()">');
                content = content.replace(match, newMatch);
                updated = true;
            }
        }
    }

    // Feature 3: Auto-increment date in handleFillUp
    const fillLoopRegex = /for\s*\(\s*let\s+i\s*=\s*minIdx;\s*i\s*<=\s*maxIdx;\s*i\+\+\s*\)\s*\{\s*if\s*\(\s*i\s*===\s*startIdx\s*\)\s*continue;\s*if\s*\(\s*field\s*===\s*'selected'\s*\)\s*\{[\s\S]*?continue;\s*\}\s*tableData\.value\[i\]\[field\]\s*=\s*value;/;
    if (fillLoopRegex.test(content)) {
        content = content.replace(fillLoopRegex, handleFillUpBody.trim());
        updated = true;
    }

    // Feature 2: Flexible date parsing
    if (file !== 'client_206.blade.php') {
        // inject the helper
        if (!content.includes('const parseAndFormatDate = (dateStr) => {')) {
            content = content.replace(
                /(const newRow = ref\(\{)/,
                `${parseFunc}\n            $1`
            );
            updated = true;
        }

        // replace formatNewDate
        const oldFormatNewDate = /const formatNewDate = \(\) => \{[\s\S]*?\};\n/;
        if (oldFormatNewDate.test(content)) {
            content = content.replace(oldFormatNewDate, `const formatNewDate = () => {
                newRow.value.date = parseAndFormatDate(newRow.value.date);
            };\n`);
            updated = true;
        }

        // replace updateRow date logic
        const oldUpdateRowFormat = /if \(row\.date\) \{\s*const match = row\.date\.match\(\/\^\(\\\\d\{1,2\}\)\\\\\/\(\\\\d\{1,2\}\)\$\/\);\s*if \(match\) \{\s*row\.date = `\$\{parseInt\(match\[1\]\)\}月\$\{parseInt\(match\[2\]\)\}日`;\s*\}\s*\}/g;
        // Wait, the regex might be tricky due to escapes. I'll just use string replace.
        const targetStr1 = "if (row.date) {\n                    const match = row.date.match(/^(\\d{1,2})\\/(\\d{1,2})$/);\n                    if (match) {\n                        row.date = `${parseInt(match[1])}月${parseInt(match[2])}日`;\n                    }\n                }";
        
        if (content.includes(targetStr1)) {
            content = content.replace(targetStr1, "row.date = parseAndFormatDate(row.date);");
            updated = true;
        }
    }

    if (updated) {
        fs.writeFileSync(filePath, content, 'utf8');
        console.log(`Updated ${file}`);
    }
}
