const fs = require('fs');
const files = ['resources/views/client_206.blade.php', 'resources/views/client_225.blade.php'];
files.forEach(file => {
    let content = fs.readFileSync(file, 'utf-8');
    
    const badBlockRegex = /const getCellStyle = \(row, colIndex\) => \{\s*const s = \{ \.\.\.row\.styles\[colIndex\] \};\s*delete s\.border;\s*delete s\.borderTop;\s*delete s\.borderBottom;\s*delete s\.borderLeft;\s*delete s\.borderRight;\s*return s;\s*\};/;
    
    const fixedBlock = `const getCellStyle = (row, colIndex) => {
                if (!row || !row.styles || !row.styles[colIndex]) return {};
                const s = { ...row.styles[colIndex] };
                delete s.border;
                delete s.borderTop;
                delete s.borderBottom;
                delete s.borderLeft;
                delete s.borderRight;
                return s;
            };`;
            
    if (badBlockRegex.test(content)) {
        content = content.replace(badBlockRegex, fixedBlock);
        fs.writeFileSync(file, content, 'utf-8');
        console.log('Fixed ' + file);
    } else {
        console.log('Could not find bad block in ' + file);
    }
});
