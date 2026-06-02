import sys

filepath = 'resources/views/client_639.blade.php'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Define calculateForkliftFee before previewFreight
calc_func = """
            const calculateForkliftFee = (weight, pieces) => {
                weight = parseFloat(weight) || 0;
                pieces = parseInt(pieces) || 0;
                if (weight <= 0 && pieces <= 0) return 0;
                
                if (weight >= 2000) return -1; // 另計 (we use >= 2000 just in case, wait, > 2000)
                if (weight >= 1000) return 500;
                if (pieces >= 4) return 500;
                if (weight >= 100) return 250;
                return 0;
            };

            const previewFreight = (row) => {"""
content = content.replace("            const previewFreight = (row) => {", calc_func)

# Fix previewFreight to use calculateForkliftFee
preview_old = """                    if (newAmount > 0) {
                        row.amount = newAmount;
                    } else if (newAmount === -1) {
                        row.amount = 0;
                    }
                    return;"""
preview_new = """                    if (newAmount > 0) {
                        row.amount = newAmount;
                    } else if (newAmount === -1) {
                        row.amount = 0;
                    }
                    
                    const newForklift = calculateForkliftFee(row.weight, row.pieces);
                    if (newForklift > 0) row.forklift_fee = newForklift;
                    else if (newForklift === -1) row.forklift_fee = null;
                    else if (newForklift === 0) row.forklift_fee = null;
                    return;"""
content = content.replace(preview_old, preview_new)

# Fix previewFreight grouped section
preview_grp_old = """                const targetIndex = tongXiaPiIndex !== -1 ? tongXiaPiIndex : maxWeightIndex;
                
                const newAmount = calculateFreight(totalWeight, combinedText);
                const finalAmount = newAmount > 0 ? newAmount : 0;
                
                for (let i = 0; i < group.length; i++) {
                    if (i === targetIndex) {
                        group[i].amount = finalAmount;
                    } else {
                        group[i].amount = 0;
                    }
                }"""
preview_grp_new = """                const targetIndex = tongXiaPiIndex !== -1 ? tongXiaPiIndex : maxWeightIndex;
                
                let totalPieces = 0;
                for (let i = 0; i < group.length; i++) {
                    totalPieces += parseInt(group[i].pieces) || 0;
                }
                
                const newAmount = calculateFreight(totalWeight, combinedText);
                const finalAmount = newAmount > 0 ? newAmount : 0;
                
                const newForklift = calculateForkliftFee(totalWeight, totalPieces);
                
                for (let i = 0; i < group.length; i++) {
                    if (i === targetIndex) {
                        group[i].amount = finalAmount;
                        if (newForklift > 0) group[i].forklift_fee = newForklift;
                        else if (newForklift === -1 || newForklift === 0) group[i].forklift_fee = null;
                    } else {
                        group[i].amount = 0;
                        group[i].forklift_fee = null;
                    }
                }"""
content = content.replace(preview_grp_old, preview_grp_new)

# Fix recalculateAndSave
recalc_old = """                const targetIndex = tongXiaPiIndex !== -1 ? tongXiaPiIndex : maxWeightIndex;
                
                const newAmount = calculateFreight(totalWeight, combinedText);
                const finalAmount = newAmount > 0 ? newAmount : 0;
                
                for (let i = 0; i < group.length; i++) {
                    if (i === targetIndex) {
                        group[i].amount = finalAmount;
                    } else {
                        group[i].amount = 0;
                    }
                    await updateRow(group[i]);
                }"""
recalc_new = """                const targetIndex = tongXiaPiIndex !== -1 ? tongXiaPiIndex : maxWeightIndex;
                
                let totalPieces = 0;
                for (let i = 0; i < group.length; i++) {
                    totalPieces += parseInt(group[i].pieces) || 0;
                }
                
                const newAmount = calculateFreight(totalWeight, combinedText);
                const finalAmount = newAmount > 0 ? newAmount : 0;
                
                const newForklift = calculateForkliftFee(totalWeight, totalPieces);
                
                for (let i = 0; i < group.length; i++) {
                    if (i === targetIndex) {
                        group[i].amount = finalAmount;
                        if (newForklift > 0) group[i].forklift_fee = newForklift;
                        else if (newForklift === -1 || newForklift === 0) group[i].forklift_fee = null;
                    } else {
                        group[i].amount = 0;
                        group[i].forklift_fee = null;
                    }
                    await updateRow(group[i]);
                }"""
content = content.replace(recalc_old, recalc_new)

recalc_single_old = """                if (group.length === 1) {
                    const textToCheck = (row.location || '') + ' ' + (row.remark || '');
                    const newAmount = calculateFreight(row.weight, textToCheck);
                    if (newAmount > 0) row.amount = newAmount;
                    await updateRow(row);
                    return;
                }"""
recalc_single_new = """                if (group.length === 1) {
                    const textToCheck = (row.location || '') + ' ' + (row.remark || '');
                    const newAmount = calculateFreight(row.weight, textToCheck);
                    if (newAmount > 0) row.amount = newAmount;
                    
                    const newForklift = calculateForkliftFee(row.weight, row.pieces);
                    if (newForklift > 0) row.forklift_fee = newForklift;
                    else if (newForklift === -1 || newForklift === 0) row.forklift_fee = null;
                    
                    await updateRow(row);
                    return;
                }"""
content = content.replace(recalc_single_old, recalc_single_new)

# Also need to trigger previewFreight on pieces change
pieces_old = '<td><input autocomplete="off" @keyup.enter="addRow" @keydown="handleArrowKeys" type="text" v-model.number="newRow.pieces"'
pieces_new = '<td><input autocomplete="off" @keyup.enter="addRow" @keydown="handleArrowKeys" @input="previewFreight(newRow)" type="text" v-model.number="newRow.pieces"'
content = content.replace(pieces_old, pieces_new)

pieces_row_old = '@change="updateRow(row)" type="text" v-model.number="row.pieces"'
pieces_row_new = '@input="previewFreight(row)" @change="recalculateAndSave(row)" type="text" v-model.number="row.pieces"'
content = content.replace(pieces_row_old, pieces_row_new)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Added forklift calculation to 639")
