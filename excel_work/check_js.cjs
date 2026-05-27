const fs = require('fs');
const content = fs.readFileSync('resources/views/client_225.blade.php', 'utf-8');
const scriptMatch = content.match(/<script>([\s\S]*?)<\/script>/);
if (scriptMatch) {
    fs.writeFileSync('temp.cjs', scriptMatch[1]);
    try {
        const { execSync } = require('child_process');
        execSync('node --check temp.cjs');
        console.log('Syntax is OK');
    } catch (e) {
        console.error('Syntax error', e.stdout.toString(), e.stderr.toString());
    }
}
