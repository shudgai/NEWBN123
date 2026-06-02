import sys

filepath = 'resources/views/client_639.blade.php'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

paste_old = """                        if (!pastedFields.includes('amount')) {
                            const textToCheck = (targetRow.location || '') + ' ' + (targetRow.remark || '');
                            const amt = calculateFreight(targetRow.weight, textToCheck);
                            if (amt > 0) {
                                targetRow.amount = amt;
                            } else if (amt === -1) {
                                targetRow.amount = 0;
                            }
                        }"""
paste_new = """                        if (!pastedFields.includes('amount')) {
                            const textToCheck = (targetRow.location || '') + ' ' + (targetRow.remark || '');
                            const amt = calculateFreight(targetRow.weight, textToCheck);
                            if (amt > 0) {
                                targetRow.amount = amt;
                            } else if (amt === -1) {
                                targetRow.amount = 0;
                            }
                        }
                        
                        if (!pastedFields.includes('forklift_fee')) {
                            const newForklift = calculateForkliftFee(targetRow.weight, targetRow.pieces);
                            if (newForklift > 0) {
                                targetRow.forklift_fee = newForklift;
                            } else if (newForklift === -1 || newForklift === 0) {
                                targetRow.forklift_fee = null;
                            }
                        }"""
if paste_old in content:
    content = content.replace(paste_old, paste_new)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed paste forklift in 639")
else:
    print("Could not find paste section")
