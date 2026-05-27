    const { createApp, ref, computed, onMounted, nextTick, watch } = Vue;

    createApp({
        setup() {
            const fontSize = ref(14);
            const tableData = ref([]);
            
            const isAmountManual = ref(false);
            
            const handleArrowKeys = (e) => {
                if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Enter'].includes(e.key)) return;
                
                const inputs = Array.from(document.querySelectorAll('.nav-input'));
                const index = inputs.indexOf(e.target);
                if (index === -1) return;

                let nextIndex = null;
                const cols = 8; // Number of input columns

                if (e.key === 'ArrowLeft') {
                    if (e.target.selectionStart === 0 && e.target.selectionEnd === 0) {
                        nextIndex = index - 1;
                    }
                } else if (e.key === 'ArrowRight') {
                    if (e.target.selectionStart === e.target.value.length && e.target.selectionEnd === e.target.value.length) {
                        nextIndex = index + 1;
                    }
                } else if (e.key === 'ArrowUp') {
                    nextIndex = index - cols;
                } else if (e.key === 'ArrowDown' || e.key === 'Enter') {
                    nextIndex = index + cols;
                }

                if (nextIndex !== null && nextIndex >= 0 && nextIndex < inputs.length) {
                    e.preventDefault();
                    inputs[nextIndex].focus();
                    if (inputs[nextIndex].tagName === 'INPUT') {
                        setTimeout(() => inputs[nextIndex].select(), 0);
                    }
                }
            };

            const numberToChinese = (num) => {
                const chars = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十'];
                if (num <= 10) return chars[num];
                if (num < 20) return '十' + (num % 10 === 0 ? '' : chars[num % 10]);
                const tens = Math.floor(num / 10);
                const units = num % 10;
                return chars[tens] + '十' + (units === 0 ? '' : chars[units]);
            };

            const updateRow = async (row) => {
                try {
                    const payload = {
                        date: row.date,
                        bill_no: row.bill_no,
                        client_name: row.client_name,
                        amount: row.amount || 0,
                        pieces: row.pieces || 0,
                        weight: row.weight || 0,
                        location: row.location || '',
                        remark: row.remark || '',
                        is_client_data: row.is_client_data || false
                    };

                    const response = await fetch(`/api/waybills/${row.id}`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                            'Accept': 'application/json'
                        },
                        body: JSON.stringify(payload)
                    });

                    if (!response.ok) {
                        throw new Error('Update failed');
                    }
                } catch (error) {
                    console.error("Error updating data:", error);
                    alert("自動存檔失敗，請確認網路連線！");
                }
            };

            const recalculateAndSave = async (row) => {
                if (row.weight) {
                    row.weight = Math.round(row.weight);
                }
                const textToCheck = (row.location || '') + ' ' + (row.remark || '');
                const newAmount = calculateFreight(row.weight, textToCheck, row.client_name);
                if (newAmount > 0) {
                    row.amount = newAmount;
                }
                await updateRow(row);
            };

            const previewFreight = (row) => {
                const textToCheck = (row.location || '') + ' ' + (row.remark || '');
                const newAmount = calculateFreight(row.weight, textToCheck, row.client_name);
                if (newAmount > 0) {
                    row.amount = newAmount;
                } else if (newAmount === -1) {
                    row.amount = 0;
                }
            };

            const handleRemarkChange = async (row, index) => {
                if (row.remark === '共') {
                    let count = 1;
                    for (let i = index - 1; i >= 0; i--) {
                        if (tableData.value[i].date === row.date && tableData.value[i].client_name === row.client_name) {
                            count++;
                            if (tableData.value[i].remark && tableData.value[i].remark.includes('同下批')) {
                                break;
                            }
                        } else {
                            break;
                        }
                    }
                    row.remark = `共${numberToChinese(count)}批`;
                }
                await recalculateAndSave(row);
            };

            const fillState = ref({ active: false, startIdx: -1, endIdx: -1, field: null, value: null });

            const startFill = (index, field, e) => {
                e.preventDefault(); // prevent input blur
                fillState.value = {
                    active: true,
                    startIdx: index,
                    endIdx: index,
                    field: field,
                    value: tableData.value[index][field]
                };
                document.addEventListener('mousemove', handleFillMove);
                document.addEventListener('mouseup', handleFillUp);
            };

            const handleFillMove = (e) => {
                if (!fillState.value.active) return;
                const el = document.elementFromPoint(e.clientX, e.clientY);
                if (!el) return;
                const tr = el.closest('tr[data-id]');
                if (tr) {
                    const id = tr.getAttribute('data-id');
                    const idx = tableData.value.findIndex(r => r.id == id);
                    if (idx !== -1) {
                        fillState.value.endIdx = idx;
                    }
                }
            };

            const handleFillUp = async () => {
                if (!fillState.value.active) return;
                fillState.value.active = false;
                document.removeEventListener('mousemove', handleFillMove);
                document.removeEventListener('mouseup', handleFillUp);

                const { startIdx, endIdx, field, value } = fillState.value;
                if (startIdx === -1 || endIdx === -1 || startIdx === endIdx) return;

                const minIdx = Math.min(startIdx, endIdx);
                const maxIdx = Math.max(startIdx, endIdx);

                for (let i = minIdx; i <= maxIdx; i++) {
                    if (i === startIdx) continue;
                    tableData.value[i][field] = value;
                    if (field === 'weight' || field === 'location' || field === 'remark') {
                        await recalculateAndSave(tableData.value[i]);
                    } else {
                        await updateRow(tableData.value[i]);
                    }
                }
            };

            const isFillHighlighted = (index, field) => {
                if (!fillState.value.active || fillState.value.field !== field) return false;
                const min = Math.min(fillState.value.startIdx, fillState.value.endIdx);
                const max = Math.max(fillState.value.startIdx, fillState.value.endIdx);
                return index >= min && index <= max;
            };

            const newRow = ref({
                date: '115/05/04',
                bill_no: '',
                client_name: '',
                amount: null,
                pieces: null,
                weight: null,
                location: '',
                remark: ''
            });

            const calculateFreight = (weight, remark, client) => {
                const r = remark || '';
                const c = client || '';
                let isTypeA = c.includes('225') || c.includes('鴻天') || c.includes('639');
                let isFox = c.includes('福斯');
                let isTypeB_Normal = c.includes('206') || c.includes('235') || c.includes('276') || c.includes('282') || c.includes('太古');

                if (!isTypeA && !isFox && !isTypeB_Normal) {
                    isTypeB_Normal = true;
                }

                let vehicle = null;
                if (r.match(/3\.49噸/)) vehicle = '3.49';
                else if (r.match(/6\.8噸/)) vehicle = '6.8';
                else if (r.match(/8\.8噸/)) vehicle = '8.8';
                else if (r.match(/15噸/)) vehicle = '15';
                else if (r.match(/17噸/)) vehicle = '17';

                if (isFox) {
                    let locB = null;
                    if (r.match(/內湖/)) locB = '內湖';
                    else if (r.match(/楊梅/)) locB = '楊梅';
                    else if (r.match(/湖口/)) locB = '湖口';
                    else if (r.match(/台中/)) locB = '台中';

                    if (vehicle && locB) {
                        const matrix_Fox_FTL = {
                            '內湖': { '3.49': 1500, '6.8': 1700, '8.8': 2600, '15': 3400, '17': 4000 },
                            '楊梅': { '3.49': 1500, '6.8': 1700, '8.8': 2600, '15': 3400, '17': 4000 },
                            '湖口': { '3.49': 2100, '6.8': 3000, '8.8': 3600, '15': 4500, '17': 5000 },
                        };
                        const price = matrix_Fox_FTL[locB][vehicle];
                        return price !== undefined ? price : -1;
                    }

                    if (!weight) return 0;
                    const w = parseFloat(weight);
                    if (isNaN(w) || w <= 0) return 0;

                    if (locB) {
                        const matrix_Fox_LTL = {
                            '內湖': [ {max: 100, price: 500}, {max: 300, price: 700}, {max: Infinity, price: 900} ],
                            '楊梅': [ {max: 100, price: 600}, {max: 300, price: 800}, {max: Infinity, price: 1000} ],
                            '湖口': [ {max: 100, price: 800}, {max: 300, price: 1000}, {max: Infinity, price: 1200} ],
                            '台中': [ {max: 100, price: 1500}, {max: 300, price: 2000}, {max: Infinity, price: 2500} ]
                        };
                        const tiers = matrix_Fox_LTL[locB];
                        for (let t of tiers) {
                            if (w <= t.max) return t.price;
                        }
                    }
                    return 0;
                }

                // --- Original Type A and Type B logic ---
                let regionA = 1;
                if (r.match(/三重|五股|泰山|新莊|蘆洲|板橋|樹林|中和|永和/)) { regionA = '2a'; }
                else if (r.match(/南港|內湖|大直|天母|景美/)) { regionA = '2b'; }
                else if (r.match(/新店|汐止|深坑|木柵|八里|土城|鶯歌|三峽|北投|社子/)) { regionA = '2c'; }
                else if (r.match(/大溪|龍潭|新豐|湖口|七堵|瑞芳/)) { regionA = '2d'; }
                else if (r.match(/新竹|基隆|淡水/)) { regionA = '2e'; }
                else if (r.match(/蘆竹|大園/)) { regionA = 3; }
                else if (r.match(/中壢|林口|龜山|桃園/)) { regionA = 4; }
                else if (r.match(/新屋|八德|觀音|平鎮|楊梅/)) { regionA = 5; }

                if (vehicle) {
                    const matrixA_FTL = {
                        1: { '3.49': 1680, '6.8': 2100, '8.8': 3150, '17': 4725 },
                        '2a': { '3.49': 1785, '6.8': 2310, '8.8': 3150, '17': 4725 },
                        '2b': { '3.49': 1785, '6.8': 2310, '8.8': 3150, '17': 5040 },
                        '2c': { '3.49': 1890, '6.8': 2520, '8.8': 3675, '17': 5040 },
                        '2d': { '3.49': 2100, '6.8': 2940, '8.8': 3780, '17': 5250 },
                        '2e': { '3.49': 2520, '6.8': 3360, '8.8': 3990, '17': 5460 },
                        3: { '3.49': 1575, '6.8': 2100, '8.8': 2625, '17': 4200 },
                        4: { '3.49': 1680, '6.8': 2205, '8.8': 2940, '17': 4410 },
                        5: { '3.49': 1785, '6.8': 2310, '8.8': 3150, '17': 4725 }
                    };
                    const matrixB_FTL = {
                        1: { '3.49': 1600, '6.8': 2000, '8.8': 3000, '17': 4500 },
                        '2a': { '3.49': 1700, '6.8': 2200, '8.8': 3000, '17': 4500 },
                        '2b': { '3.49': 1700, '6.8': 2200, '8.8': 3000, '17': 4800 },
                        '2c': { '3.49': 1800, '6.8': 2400, '8.8': 3500, '17': 4800 },
                        '2d': { '3.49': 2000, '6.8': 2800, '8.8': 3600, '17': 5000 },
                        '2e': { '3.49': 2400, '6.8': 3200, '8.8': 3800, '17': 5200 },
                        3: { '3.49': 1500, '6.8': 2000, '8.8': 2500, '17': 4000 },
                        4: { '3.49': 1600, '6.8': 2100, '8.8': 2800, '17': 4200 },
                    };
                    const typeAPrice = matrixA_FTL[regionA]?.[vehicle];
                    const typeBPrice = matrixB_FTL[regionA]?.[vehicle];
                    const finalPrice = isTypeA ? typeAPrice : typeBPrice;
                    return finalPrice !== undefined ? finalPrice : -1;
                }

                if (!weight) return 0;
                const w = parseFloat(weight);
                if (isNaN(w) || w <= 0) return 0;

                let basePrice = 0;
                if (isTypeA) {
                    if (w <= 20) basePrice = 330;
                    else if (w <= 50) basePrice = 440;
                    else if (w <= 100) basePrice = 660;
                    else if (w <= 200) basePrice = 770;
                    else if (w <= 300) basePrice = 880;
                    else if (w <= 400) basePrice = 990;
                    else if (w <= 500) basePrice = 1100;
                    else if (w <= 600) basePrice = 1210;
                    else if (w <= 700) basePrice = 1320;
                    else {
                        const extraHundreds = Math.ceil((w - 700) / 100);
                        basePrice = 1320 + extraHundreds * 110;
                    }
                } else {
                    if (w <= 20) basePrice = 300;
                    else if (w <= 50) basePrice = 400;
                    else if (w <= 100) basePrice = 600;
                    else if (w <= 200) basePrice = 700;
                    else if (w <= 300) basePrice = 800;
                    else if (w <= 400) basePrice = 900;
                    else if (w <= 500) basePrice = 1000;
                    else if (w <= 600) basePrice = 1100;
                    else if (w <= 700) basePrice = 1200;
                    else if (w <= 799) basePrice = 1400;
                    else {
                        const extraHundreds = Math.ceil((w - 799) / 100);
                        basePrice = 1400 + extraHundreds * 100;
                    }
                }

                if (typeof regionA === 'string' && regionA.startsWith('2')) {
                    if (isTypeA) {
                        if (regionA === '2a') basePrice += 220;
                        if (regionA === '2b') basePrice += 330;
                        if (regionA === '2c') basePrice += 440;
                        if (regionA === '2d') basePrice += 550;
                        if (regionA === '2e') basePrice += 660;
                    } else {
                        if (regionA === '2a') basePrice += 200;
                        if (regionA === '2b') basePrice += 300;
                        if (regionA === '2c') basePrice += 400;
                        if (regionA === '2d') basePrice += 500;
                        if (regionA === '2e') basePrice += 600;
                    }
                    return basePrice;
                } else if (regionA === 3) {
                    if (isTypeA) {
                        if (w <= 100) return 440;
                        if (w <= 300) return 770;
                        if (w <= 500) return 990;
                        return 1320; 
                    } else {
                        if (w <= 100) return 400;
                        if (w <= 300) return 700;
                        if (w <= 500) return 900;
                        return 1200; 
                    }
                } else if (regionA === 4) {
                    if (isTypeA) {
                        if (w <= 100) return 550;
                        if (w <= 300) return 880;
                        if (w <= 400) return 1100;
                        if (w <= 500) return 1210;
                        return 1430;
                    } else {
                        if (w <= 100) return 500;
                        if (w <= 300) return 800;
                        if (w <= 400) return 1000;
                        if (w <= 500) return 1100;
                        return 1300;
                    }
                } else if (regionA === 5) {
                    if (isTypeA) {
                        if (w <= 100) return 660;
                        if (w <= 300) return 880;
                        if (w <= 400) return 1100;
                        if (w <= 500) return 1320;
                        return 1540;
                    } else {
                        if (w <= 100) return 600;
                        if (w <= 300) return 800;
                        if (w <= 400) return 1000;
                        if (w <= 500) return 1200;
                        return 1400;
                    }
                }

                return basePrice;
            };

            watch([() => newRow.value.weight, () => newRow.value.location, () => newRow.value.remark, () => newRow.value.client_name], ([newWeight, newLoc, newRemark, newClient]) => {
                if (newRow.value.weight) {
                    newRow.value.weight = Math.round(newRow.value.weight);
                    newWeight = newRow.value.weight;
                }
                if (isAmountManual.value) return;
                const textToCheck = (newLoc || '') + ' ' + (newRemark || '');
                const newAmount = calculateFreight(newWeight, textToCheck, newClient);
                if (newAmount > 0) {
                    newRow.value.amount = newAmount;
                } else if (newAmount === -1) {
                    newRow.value.amount = 0;
                }
            });

            const fetchData = async () => {
                try {
                    const response = await fetch('/api/waybills');
                    const data = await response.json();
                    tableData.value = data;
                } catch (error) {
                    console.error("Error fetching data:", error);
                }
            };

            const addRow = async () => {
                if (!newRow.value.client_name) {
                    alert('請填寫客戶名稱');
                    return;
                }
                
                try {
                    if (newRow.value.remark === '共') {
                        let count = 1;
                        for (let i = tableData.value.length - 1; i >= 0; i--) {
                            if (tableData.value[i].date === newRow.value.date && tableData.value[i].client_name === newRow.value.client_name) {
                                count++;
                                if (tableData.value[i].remark && tableData.value[i].remark.includes('同下批')) {
                                    break;
                                }
                            } else {
                                break;
                            }
                        }
                        newRow.value.remark = `共${numberToChinese(count)}批`;
                    }

                    const payload = {
                        date: newRow.value.date,
                        bill_no: newRow.value.bill_no,
                        client_name: newRow.value.client_name,
                        amount: newRow.value.amount || 0,
                        pieces: newRow.value.pieces || 0,
                        weight: newRow.value.weight || 0,
                        location: newRow.value.location || '',
                        remark: newRow.value.remark || '',
                        is_client_data: false
                    };

                    const response = await fetch('/api/waybills', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Accept': 'application/json'
                        },
                        body: JSON.stringify(payload)
                    });

                    if (response.ok) {
                        newRow.value.bill_no = '';
                        newRow.value.amount = null;
                        newRow.value.pieces = null;
                        newRow.value.weight = null;
                        newRow.value.location = '';
                        newRow.value.remark = '';
                        isAmountManual.value = false;
                        
                        await fetchData();
                        
                        setTimeout(() => {
                            if (document.activeElement && document.activeElement.tagName === 'INPUT') {
                                document.activeElement.select();
                            }
                        }, 50);
                    } else {
                        throw new Error('Save failed');
                    }
                } catch (error) {
                    console.error("Error saving data:", error);
                    alert("儲存失敗");
                }
            };

            const toastMessage = ref('');
            const showToast = ref(false);
            let undoData = null;
            let toastTimeout = null;


            const handlePaste = async (e) => {
                const plainText = (e.clipboardData || window.clipboardData).getData('Text');
                const htmlText = (e.clipboardData || window.clipboardData).getData('text/html');
                if (!plainText.includes('\t') && !plainText.includes('\n')) return;

                e.preventDefault();
                
                const plainRows = plainText.split(/\r?\n/).map(r => r.split('\t')).filter(r => r.length > 0 && !(r.length === 1 && r[0] === ''));
                let htmlBgData = [];
                
                if (htmlText) {
                    try {
                        const parser = new DOMParser();
                        const doc = parser.parseFromString(htmlText, 'text/html');
                        
                        // Parse style block for yellow classes (Excel uses classes like .xl65)
                        let yellowClasses = [];
                        const styleTags = doc.querySelectorAll('style');
                        styleTags.forEach(style => {
                            const css = style.innerHTML;
                            const regex = /\.([a-zA-Z0-9_-]+)\s*\{[^}]*background[^:]*:\s*(yellow|#ffff00|rgb\(255,\s*255,\s*0\)|#ff0)[^;}]*;/gi;
                            let match;
                            while ((match = regex.exec(css)) !== null) {
                                yellowClasses.push(match[1]);
                            }
                        });

                        const rows = doc.querySelectorAll('tr');
                        for (let r = 0; r < rows.length; r++) {
                            const cells = rows[r].querySelectorAll('td, th');
                            if (cells.length === 0) continue;
                            let isClientData = false;
                            
                            for (let c = 0; c < cells.length; c++) {
                                const cell = cells[c];
                                
                                // Check background
                                const className = cell.className || '';
                                if (yellowClasses.some(cls => className.includes(cls))) {
                                    isClientData = true;
                                }
                                const bg = cell.style.backgroundColor || cell.style.background || cell.getAttribute('bgcolor');
                                if (bg) {
                                    if (bg.includes('255, 255, 0') || bg.toLowerCase().includes('ffff00') || bg.toLowerCase() === 'yellow' || bg.includes('rgb(255, 255,')) {
                                        isClientData = true;
                                    }
                                }
                            }
                            htmlBgData.push(isClientData);
                        }
                    } catch (err) {
                        console.error('Error parsing HTML paste:', err);
                    }
                }
                
                const target = e.target;
                const tr = target.closest('tr');
                if (!tr) return;

                const inputsInRow = Array.from(tr.querySelectorAll('input:not([type="hidden"])'));
                const startColIndex = inputsInRow.indexOf(target);
                if (startColIndex === -1) return;

                const fields = ['date', 'bill_no', 'client_name', 'amount', 'pieces', 'weight', 'location', 'remark'];
                
                const isNewRowTr = tr.classList.contains('bg-blue-50');
                let rowIndex = isNewRowTr ? tableData.value.length : tableData.value.findIndex(row => row.id == tr.getAttribute('data-id'));

                let pastedNewRows = [];
                let modifiedOldRows = [];
                let errorMessages = [];

                for (let r = 0; r < plainRows.length; r++) {
                    const rowVals = plainRows[r];
                    const isClientData = htmlBgData[r] || false;
                    
                    if (rowVals.length === 0 || (rowVals.length === 1 && rowVals[0] === '')) continue;
                    
                    try {
                        let targetRow;
                        let isNew = false;
                        let oldRowSnapshot = null;
                        
                        if (rowIndex < tableData.value.length && !isNewRowTr) {
                            oldRowSnapshot = { ...tableData.value[rowIndex] };
                            targetRow = tableData.value[rowIndex];
                        } else {
                            targetRow = { ...newRow.value };
                            isNew = true;
                        }

                        if (isClientData) {
                            targetRow.is_client_data = true;
                        }

                        for (let c = 0; c < rowVals.length; c++) {
                            const colField = fields[startColIndex + c];
                            if (colField) {
                                let val = rowVals[c].trim();
                                if (['amount', 'pieces', 'weight'].includes(colField)) {
                                    val = val === '' ? null : (parseFloat(val) || 0);
                                }
                                targetRow[colField] = val;
                            }
                        }

                        const pastedFields = rowVals.map((_, c) => fields[startColIndex + c]);
                        if (!pastedFields.includes('amount')) {
                            const textToCheck = (targetRow.location || '') + ' ' + (targetRow.remark || '');
                            const amt = calculateFreight(targetRow.weight, textToCheck, targetRow.client_name);
                            if (amt > 0) {
                                targetRow.amount = amt;
                            } else if (amt === -1) {
                                targetRow.amount = 0;
                            }
                        }

                        if (!targetRow.client_name) targetRow.client_name = '未知客戶';
                        if (!targetRow.date) targetRow.date = '未填日期';
                        if (targetRow.amount === null || targetRow.amount === '' || isNaN(targetRow.amount)) targetRow.amount = 0;
                        if (targetRow.pieces === null || targetRow.pieces === '' || isNaN(targetRow.pieces)) targetRow.pieces = 0;
                        if (targetRow.weight === null || targetRow.weight === '' || isNaN(targetRow.weight)) targetRow.weight = 0;

                        if (isNew) {
                            const res = await fetch('/api/waybills', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                                body: JSON.stringify(targetRow)
                            });
                            if (res.ok) {
                                const saved = await res.json();
                                tableData.value.push(saved.data);
                                pastedNewRows.push(saved.data.id);
                            } else {
                                const errText = await res.text();
                                console.error('Save failed:', errText);
                                errorMessages.push(`第 ${r+1} 行存檔失敗: (${res.status}) ${errText.substring(0, 50)}`);
                            }
                        } else {
                            modifiedOldRows.push(oldRowSnapshot);
                            await updateRow(targetRow, true); 
                        }
                    } catch (e) {
                        console.error('Row process error:', e);
                        errorMessages.push(`第 ${r+1} 行發生程式錯誤`);
                    }
                    rowIndex++;
                }

                if (errorMessages.length > 0) {
                    alert(`貼上完成，但有 ${errorMessages.length} 筆資料無法存檔！\n例如：\n` + errorMessages.slice(0, 3).join('\n'));
                }

                undoData = { newRowIds: pastedNewRows, oldRows: modifiedOldRows };
                toastMessage.value = `成功貼上了 ${pastedNewRows.length + modifiedOldRows.length} 筆資料`;
                showToast.value = true;
                
                if (toastTimeout) clearTimeout(toastTimeout);
                toastTimeout = setTimeout(() => { showToast.value = false; }, 10000);
            };

            const undoPaste = async () => {
                if (!undoData) return;
                showToast.value = false;
                
                // 1. Delete new rows
                for (const id of undoData.newRowIds) {
                    try {
                        await fetch(`/api/waybills/${id}`, { method: 'DELETE' });
                    } catch (e) { console.error(e); }
                }
                
                // 2. Revert old rows
                for (const oldRow of undoData.oldRows) {
                    try {
                        await fetch(`/api/waybills/${oldRow.id}`, {
                            method: 'PUT',
                            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                            body: JSON.stringify(oldRow)
                        });
                    } catch (e) { console.error(e); }
                }
                
                undoData = null;
                await fetchData();
            };

            const deleteRow = async (id) => {
                if (!confirm('確定要刪除這筆資料嗎？')) return;
                
                try {
                    const response = await fetch(`/api/waybills/${id}`, {
                        method: 'DELETE'
                    });
                    if (response.ok) {
                        await fetchData();
                    }
                } catch (error) {
                    console.error("Error deleting data:", error);
                    alert("刪除失敗");
                }
            };

            const clearAllData = async () => {
                if (!confirm('您確定要清空畫面上「所有」的資料嗎？這個動作無法復原！')) return;
                try {
                    const response = await fetch('/api/waybills/truncate', {
                        method: 'DELETE'
                    });
                    if (response.ok) {
                        tableData.value = [];
                    } else {
                        alert('清空失敗，請稍後再試！');
                    }
                } catch (e) {
                    console.error(e);
                    alert('清空失敗，請確認網路連線！');
                }
            };

            const totalAmount = computed(() => {
                return tableData.value.reduce((sum, row) => sum + (parseFloat(row.amount) || 0), 0);
            });

            const totalPieces = computed(() => {
                return tableData.value.reduce((sum, row) => sum + (parseInt(row.pieces) || 0), 0);
            });

            const totalWeight = computed(() => {
                const total = tableData.value.reduce((sum, row) => sum + (parseFloat(row.weight) || 0), 0);
                return Math.round(total);
            });

            const uniqueClientNames = computed(() => {
                const names = new Set();
                tableData.value.forEach(row => {
                    if (row.client_name) names.add(row.client_name);
                });
                return Array.from(names).sort();
            });

            const handleGlobalKeyDown = (e) => {
                if (e.ctrlKey && (e.key === 'z' || e.key === 'Z')) {
                    if (undoData) {
                        e.preventDefault();
                        e.stopPropagation();
                        undoPaste();
                    }
                }
            };

            onMounted(() => {
                fetchData();
                initResizer();
                window.addEventListener('keydown', handleGlobalKeyDown, true);
            });

            const initResizer = () => {
                const table = document.querySelector('.excel-table');
                if (!table) return;
                const cols = table.querySelectorAll('th');
                [].forEach.call(cols, function (col) {
                    if (col.innerHTML === '') return; // Skip empty column like action column
                    const resizer = document.createElement('div');
                    resizer.classList.add('resizer');
                    col.appendChild(resizer);
                    createResizableColumn(col, resizer);
                });
            };

            const createResizableColumn = (col, resizer) => {
                let x = 0;
                let w = 0;
                
                const mouseDownHandler = function (e) {
                    x = e.clientX;
                    const styles = window.getComputedStyle(col);
                    w = parseInt(styles.width, 10);
                    
                    document.addEventListener('mousemove', mouseMoveHandler);
                    document.addEventListener('mouseup', mouseUpHandler);
                    resizer.classList.add('resizing');
                };
                
                const mouseMoveHandler = function (e) {
                    const dx = e.clientX - x;
                    col.style.width = `${w + dx}px`;
                };
                
                const mouseUpHandler = function () {
                    resizer.classList.remove('resizing');
                    document.removeEventListener('mousemove', mouseMoveHandler);
                    document.removeEventListener('mouseup', mouseUpHandler);
                };
                
                resizer.addEventListener('mousedown', mouseDownHandler);
            };

            const exportExcel = () => {
                if (typeof XLSX === 'undefined') {
                    alert('Excel 匯出模組尚未載入完成，請稍後再試。');
                    return;
                }
                const wsData = tableData.value.map(row => ({
                    '日期': row.date,
                    '帳單編號': row.bill_no,
                    '客戶': row.client_name,
                    '金額': row.amount,
                    '件數': row.pieces,
                    '重量': row.weight,
                    '地點': row.location,
                    '備註': row.remark
                }));
                const ws = XLSX.utils.json_to_sheet(wsData);
                const wb = XLSX.utils.book_new();
                XLSX.utils.book_append_sheet(wb, ws, "運費明細");
                XLSX.writeFile(wb, "欣華運費明細.xlsx");
            };

            return {
                fontSize,
                tableData,
                uniqueClientNames,
                newRow,
                addRow,
                updateRow,
                deleteRow,
                handleArrowKeys,
                handlePaste,
                exportExcel,
                clearAllData,
                totalAmount,
                totalPieces,
                totalWeight,
                startFill,
                isFillHighlighted,
                showToast,
                toastMessage,
                undoPaste,
                handleRemarkChange,
                previewFreight
            };
        }
    }).mount('#app');
