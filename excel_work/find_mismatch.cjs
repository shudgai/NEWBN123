const fs = require('fs');
const content = fs.readFileSync('test.js', 'utf8');

let stack = [];
let inString = false;
let stringChar = null;
let inRegex = false;
let inComment = false;
let inMultiComment = false;

for (let i = 0; i < content.length; i++) {
    const c = content[i];
    const next = content[i+1];
    
    if (inMultiComment) {
        if (c === '*' && next === '/') {
            inMultiComment = false;
            i++;
        }
        continue;
    }
    if (inComment) {
        if (c === '\n') inComment = false;
        continue;
    }
    if (!inString && !inRegex) {
        if (c === '/' && next === '*') {
            inMultiComment = true;
            i++;
            continue;
        }
        if (c === '/' && next === '/') {
            inComment = true;
            i++;
            continue;
        }
    }
    
    if (inString) {
        if (c === '\\') i++;
        else if (c === stringChar) inString = false;
        continue;
    }
    
    if (inRegex) {
        if (c === '\\') i++;
        else if (c === '/') inRegex = false;
        continue;
    }
    
    if (c === "'" || c === '"' || c === '`') {
        inString = true;
        stringChar = c;
        continue;
    }
    
    // Very naive regex detection (if we see / and we aren't in string/comment, assume regex unless it's division, but we'll assume regex for test.js)
    // To be safer, just skip regex if preceded by certain characters, but this is a heuristic.
    if (c === '/' && '=(,:[!&|'.includes(content.slice(0,i).trim().slice(-1))) {
        inRegex = true;
        continue;
    }
    
    const line = content.slice(0, i).split('\n').length;
    if (c === '{') stack.push({c, line});
    else if (c === '(') stack.push({c, line});
    else if (c === '[') stack.push({c, line});
    else if (c === '}') {
        if (stack.length && stack[stack.length-1].c === '{') stack.pop();
        else { console.log(`Unmatched } at line ${line}`); break; }
    }
    else if (c === ')') {
        if (stack.length && stack[stack.length-1].c === '(') stack.pop();
        else { console.log(`Unmatched ) at line ${line}`); break; }
    }
    else if (c === ']') {
        if (stack.length && stack[stack.length-1].c === '[') stack.pop();
        else { console.log(`Unmatched ] at line ${line}`); break; }
    }
}
console.log("Remaining stack:", stack);
