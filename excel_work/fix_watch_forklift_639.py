import sys

filepath = 'resources/views/client_639.blade.php'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

watch_old = """            watch([() => newRow.value.weight, () => newRow.value.location, () => newRow.value.remark], ([newWeight, newLoc, newRemark]) => {
                if (newRow.value.weight) {
                    newRow.value.weight = Math.round(newRow.value.weight);
                    newWeight = newRow.value.weight;
                }
                if (isAmountManual.value) return;
                const textToCheck = (newLoc || '') + ' ' + (newRemark || '');
                const newAmount = calculateFreight(newWeight, textToCheck);
                if (newAmount > 0) {
                    newRow.value.amount = newAmount;
                } else if (newAmount === -1) {
                    newRow.value.amount = 0;
                }
            });"""
watch_new = """            watch([() => newRow.value.weight, () => newRow.value.location, () => newRow.value.remark, () => newRow.value.pieces], ([newWeight, newLoc, newRemark, newPieces]) => {
                if (newRow.value.weight) {
                    newRow.value.weight = Math.round(newRow.value.weight);
                    newWeight = newRow.value.weight;
                }
                
                // Calculate forklift fee
                const newForklift = calculateForkliftFee(newWeight, newPieces);
                if (newForklift > 0) {
                    newRow.value.forklift_fee = newForklift;
                } else if (newForklift === -1 || newForklift === 0) {
                    newRow.value.forklift_fee = null;
                }
                
                if (isAmountManual.value) return;
                const textToCheck = (newLoc || '') + ' ' + (newRemark || '');
                const newAmount = calculateFreight(newWeight, textToCheck);
                if (newAmount > 0) {
                    newRow.value.amount = newAmount;
                } else if (newAmount === -1) {
                    newRow.value.amount = 0;
                }
            });"""
if watch_old in content:
    content = content.replace(watch_old, watch_new)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed watch forklift in 639")
else:
    print("Could not find watch section")
