<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>客戶225 帳單格式</title>
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Vue 3 -->
    <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
    <style>
        [v-cloak] { display: none; }
        /* Custom Excel-like styling */
        .excel-table {
            width: 100%;
        }
        .excel-table th, .excel-table td {
            border: 1px solid #000;
            padding: 4px 8px;
            white-space: nowrap;
        }
        .excel-table th {
            font-weight: bold;
            background-color: #fff;
            position: relative;
            user-select: none;
        }
        .resizer {
            position: absolute;
            top: 0;
            right: 0;
            width: 8px;
            height: 100%;
            cursor: col-resize;
            z-index: 10;
            background-color: transparent;
            transition: background-color 0.2s;
        }
        .resizer:hover, .resizer.resizing {
            background-color: rgba(59, 130, 246, 0.5); /* blue-500 with opacity */
        }
        .nav-input {
            font-family: inherit;
            font-size: inherit;
            min-width: 0;
        }
        .fill-handle {
            position: absolute;
            bottom: -2px;
            right: -2px;
            width: 8px;
            height: 8px;
            background-color: #3b82f6; /* blue-500 */
            border: 1px solid white;
            cursor: crosshair;
            display: none;
            z-index: 10;
        }
        .group:focus-within .fill-handle {
            display: block;
        }
        .fill-highlight {
            outline: 2px dashed #3b82f6;
            outline-offset: -2px;
            background-color: rgba(59, 130, 246, 0.1) !important;
        }
        .highlight-yellow {
            background-color: #FFFF00 !important;
        }
        .text-right { text-align: right; }
        .text-center { text-align: center; }
    </style>
</head>
<body class="bg-gray-100 p-8 font-sans antialiased text-black">

<div id="app" v-cloak class="max-w-7xl mx-auto bg-white p-8 shadow-sm">
    
    <!-- Controls Section -->
    <div class="mb-4 flex justify-between items-center bg-gray-50 p-3 rounded border w-full">
        <div>
            <button @click="clearAllData" class="bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded shadow transition-colors focus:outline-none focus:ring-0">
                清空全部資料
            </button>
        </div>
        <div class="flex items-center justify-center gap-4">
            <label for="fontSizeSlider" class="font-bold text-sm text-gray-700 whitespace-nowrap">字體大小調整 (目前: @{{ fontSize }}px)</label>
            <input type="range" id="fontSizeSlider" v-model="fontSize" min="10" max="24" step="1" class="w-32 md:w-48 cursor-pointer focus:outline-none focus:ring-0">
        </div>
        <div>
            <button @click="scrollToBottom" class="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded shadow transition-colors flex items-center gap-2 focus:outline-none focus:ring-0">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"></path></svg>
                移至最底
            </button>
        </div>
    </div>

    <!-- Excel Header Section -->
    <div class="mb-6 grid grid-cols-2 gap-4 text-sm" :style="{ fontSize: fontSize + 'px' }">
        <div>
            <div class="flex mb-1">
                <div class="font-bold w-24">運送公司：</div>
                <div>欣華運通有限公司</div>
            </div>
            <div class="flex">
                <div class="font-bold w-24">運送日期：</div>
                <div>115/05/01-115/05/31</div>
            </div>
        </div>
        <div>
            <div class="flex mb-1">
                <div class="font-bold w-24">客戶名稱：</div>
                <div>225 輝鴻</div>
            </div>
            <div class="flex">
                <div class="font-bold w-24">製表日期：</div>
                <div></div>
            </div>
        </div>
    </div>

    <!-- Data Table -->
    <datalist id="client-names">
        <option v-for="name in uniqueClientNames" :key="name" :value="name"></option>
    </datalist>
    <datalist id="location-names">
        <option v-for="loc in uniqueLocations" :key="loc" :value="loc"></option>
    </datalist>
    <datalist id="remark-options">
        <option value="同下批"></option>
        <option value="及下批"></option>
        <option value="共"></option>
        <option value="3.49噸車"></option>
        <option value="6.8噸車"></option>
        <option value="15噸車"></option>
        <option value="17噸車"></option>
    </datalist>
    <div class="overflow-x-auto border-t-2 border-b-2 border-black py-1">
        <table class="text-left border-collapse excel-table" :style="{ fontSize: fontSize + 'px' }" ref="excelTable">
            <thead>
                <tr class="bg-gray-100 border-b-2 border-black">
                    <th style="width: 100px;">日期</th>
                    <th style="width: 100px;">客戶名稱</th>
                    <th style="width: 150px;">提單號碼</th>
                    <th style="width: 60px;" class="text-right">件數</th>
                    <th style="width: 60px;" class="text-right">重量</th>
                    <th style="width: 100px;" class="text-right">運費</th>
                    <th style="width: 100px;">地點</th>
                    <th style="width: 150px;">備註</th>
                    <th style="width: 60px;" class="text-right">總重</th>
                    <th style="width: 40px;" class="text-center">
                        <input type="checkbox" @change="toggleAllSelection" :checked="isAllSelected" class="w-4 h-4 cursor-pointer align-middle" title="全選/取消全選">
                    </th>
                </tr>
            </thead>
            <tbody @paste="handlePaste">
                <!-- Data Rows -->
                <tr v-for="(row, index) in tableData" :key="row.id || index" :data-id="row.id" class="border-b border-gray-300 hover:bg-gray-50">
                    <td class="p-0 relative group" :class="{'fill-highlight': isFillHighlighted(index, 'date')}" :style="getCellStyle(row, 0)"><input autocomplete="off" @keydown="handleArrowKeys" @change="updateRow(row)" type="text" v-model.trim="row.date" class="nav-input w-full p-1 bg-transparent border-0 focus:outline-none focus:bg-white focus:ring-1 focus:ring-blue-400"><div class="fill-handle" @mousedown="startFill(index, 'date', $event)"></div></td>
                    <td class="p-0 relative group" :class="{'fill-highlight': isFillHighlighted(index, 'client_name')}" :style="getCellStyle(row, 1)"><input list="client-names" autocomplete="off" @keydown="handleArrowKeys" @change="updateRow(row)" type="text" v-model.trim="row.client_name" class="nav-input w-full p-1 bg-transparent border-0 focus:outline-none focus:bg-white focus:ring-1 focus:ring-blue-400"><div class="fill-handle" @mousedown="startFill(index, 'client_name', $event)"></div></td>
                    <td class="p-0 relative group" :class="{'fill-highlight': isFillHighlighted(index, 'bill_no')}" :style="getCellStyle(row, 2)"><input autocomplete="off" @keydown="handleArrowKeys" @change="updateRow(row)" type="text" v-model.trim="row.bill_no" class="nav-input w-full p-1 bg-transparent border-0 focus:outline-none focus:bg-white focus:ring-1 focus:ring-blue-400"><div class="fill-handle" @mousedown="startFill(index, 'bill_no', $event)"></div></td>
                    <td class="p-0 relative group" :class="{'fill-highlight': isFillHighlighted(index, 'pieces')}" :style="getCellStyle(row, 3)"><input autocomplete="off" @keydown="handleArrowKeys" @change="updateRow(row)" type="text" v-model.number="row.pieces" class="nav-input w-full p-1 bg-transparent border-0 text-right focus:outline-none focus:bg-white focus:ring-1 focus:ring-blue-400"><div class="fill-handle" @mousedown="startFill(index, 'pieces', $event)"></div></td>
                    <td class="p-0 relative group" :class="{'fill-highlight': isFillHighlighted(index, 'weight')}" :style="getCellStyle(row, 4)"><input autocomplete="off" @keydown="handleArrowKeys" @input="previewFreight(row)" @change="recalculateAndSave(row)" type="text" v-model.number="row.weight" class="nav-input w-full p-1 bg-transparent border-0 text-right focus:outline-none focus:bg-white focus:ring-1 focus:ring-blue-400"><div class="fill-handle" @mousedown="startFill(index, 'weight', $event)"></div></td>
                    <td class="p-0 text-right relative group" :class="{'fill-highlight': isFillHighlighted(index, 'amount')}" :style="getCellStyle(row, 5)"><input autocomplete="off" @keydown="handleArrowKeys" @change="updateRow(row)" type="text" v-model.number="row.amount" class="nav-input w-full p-1 bg-transparent border-0 text-right focus:outline-none focus:bg-white focus:ring-1 focus:ring-blue-400"><div class="fill-handle" @mousedown="startFill(index, 'amount', $event)"></div></td>
                    <td class="p-0 relative group" :class="{'fill-highlight': isFillHighlighted(index, 'location')}" :style="getCellStyle(row, 6)"><input list="location-names" autocomplete="off" @keydown="handleArrowKeys" @input="previewFreight(row)" @change="recalculateAndSave(row)" type="text" v-model.trim="row.location" class="nav-input w-full p-1 bg-transparent border-0 focus:outline-none focus:bg-white focus:ring-1 focus:ring-blue-400"><div class="fill-handle" @mousedown="startFill(index, 'location', $event)"></div></td>
                    <td class="p-0 relative group" :class="{'fill-highlight': isFillHighlighted(index, 'remark')}" :style="getCellStyle(row, 7)"><input list="remark-options" autocomplete="off" @keydown="handleArrowKeys" @input="previewFreight(row)" @change="handleRemarkChange(row, index)" type="text" v-model.trim="row.remark" class="nav-input w-full p-1 bg-transparent border-0 focus:outline-none focus:bg-white focus:ring-1 focus:ring-blue-400"><div class="fill-handle" @mousedown="startFill(index, 'remark', $event)"></div></td>
                    <td class="p-1 text-right text-blue-600 font-bold bg-gray-50 align-middle">@{{ getGroupTotalWeight(row) }}</td>
                    <td class="p-0 text-center align-middle relative group" :class="{'fill-highlight': isFillHighlighted(index, 'selected')}">
                        <input type="checkbox" v-model="selectedRows" :value="row.id" class="w-4 h-4 cursor-pointer align-middle opacity-50 group-hover:opacity-100 transition-opacity" :class="{'opacity-100': selectedRows.includes(row.id)}">
                        <div class="fill-handle" @mousedown="startFill(index, 'selected', $event)"></div>
                    </td>
                </tr>

                <!-- Input Row (Moved to bottom) -->
                <tr class="bg-blue-50 border-t-2 border-blue-200">
                    <td><input autocomplete="off" @keyup.enter="addRow" @keydown="handleArrowKeys" type="text" v-model.trim="newRow.date" class="nav-input w-full border p-1" placeholder="日期"></td>
                    <td><input list="client-names" autocomplete="off" @keyup.enter="addRow" @keydown="handleArrowKeys" type="text" v-model.trim="newRow.client_name" class="nav-input w-full border p-1" placeholder="客戶名稱"></td>
                    <td><input autocomplete="off" @keyup.enter="addRow" @keydown="handleArrowKeys" type="text" v-model.trim="newRow.bill_no" class="nav-input w-full border p-1" placeholder="提單號碼"></td>
                    <td><input autocomplete="off" @keyup.enter="addRow" @keydown="handleArrowKeys" type="text" v-model.number="newRow.pieces" class="nav-input w-full border p-1 text-right" placeholder="件數"></td>
                    <td><input autocomplete="off" @keyup.enter="addRow" @keydown="handleArrowKeys" type="text" v-model.number="newRow.weight" class="nav-input w-full border p-1 text-right" placeholder="重量"></td>
                    <td><input autocomplete="off" @keyup.enter="addRow" @keydown="handleArrowKeys" @input="isAmountManual = true" type="text" v-model.number="newRow.amount" class="nav-input w-full border p-1 text-right" placeholder="運費"></td>
                    <td><input list="location-names" autocomplete="off" @keyup.enter="addRow" @keydown="handleArrowKeys" type="text" v-model.trim="newRow.location" class="nav-input w-full border p-1" placeholder="地點"></td>
                    <td><input list="remark-options" autocomplete="off" @keyup.enter="addRow" @keydown="handleArrowKeys" type="text" v-model.trim="newRow.remark" class="nav-input w-full border p-1" placeholder="備註"></td>
                    <td></td>
                    <td class="text-center">
                        <button @click="addRow" class="bg-blue-500 hover:bg-blue-600 text-white px-3 py-1 rounded text-sm shadow">新增</button>
                    </td>
                </tr>

                <!-- Total Row -->
                <tr class="font-bold bg-gray-100 border-t-2 border-black">
                    <td colspan="5" class="text-center">總計</td>
                    <td class="text-right">@{{ totalAmount }}</td>
                    <td colspan="4"></td>
                </tr>
            </tbody>
        </table>
    </div>

    <!-- Bottom Controls -->
    <div class="mt-4 flex justify-end p-3 bg-gray-50 rounded border border-gray-300 shadow-sm">
        <button v-if="selectedRows.length > 0" @click="deleteSelected" class="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded shadow transition-colors">
            刪除選取項目 (@{{ selectedRows.length }})
        </button>
    </div>

    <!-- Undo Toast Notification -->
    
    <!-- Bottom Controls -->
    <div class="mt-4 p-4 bg-gray-50 border border-gray-300 rounded-lg shadow-sm flex flex-wrap gap-4 items-center justify-start">
        
            
            <button @click="scrollToTop" class="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded shadow transition-colors flex items-center gap-2">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18"></path></svg>
                移至最上方
            </button>
            <a href="/" class="bg-gray-700 hover:bg-gray-800 text-white font-bold py-2 px-4 rounded shadow transition-colors">
                回首頁
            </a>
            <button @click="exportExcel" class="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded shadow transition-colors">
                匯出 Excel
            </button>
            <button v-if="selectedRows.length > 0" @click="deleteSelected" class="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded shadow transition-colors">
                刪除選取項目 (@{{ selectedRows.length }})
            </button>

    </div>

    <div v-if="showToast" class="fixed bottom-4 right-4 bg-gray-800 text-white px-6 py-3 rounded shadow-lg flex items-center gap-4 z-50 transition-opacity duration-300">
        <span>@{{ toastMessage }}</span>
        <button @click="undoAction" class="text-yellow-400 font-bold hover:text-yellow-300 underline">復原 (Undo)</button>
        <button @click="showToast = false" class="text-gray-400 hover:text-white text-xl leading-none">&times;</button>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/xlsx-js-style@1.2.0/dist/xlsx.bundle.js"></script>
<script>
    const { createApp, ref, computed, onMounted, nextTick, watch } = Vue;

    createApp({
        setup() {
            const fontSize = ref(14);
            const tableData = ref([]);
            
            const getCellStyle = (row, colIndex) => {
                if (!row || !row.styles || !row.styles[colIndex]) return {};
                const s = { ...row.styles[colIndex] };
                delete s.border;
                delete s.borderTop;
                delete s.borderBottom;
                delete s.borderLeft;
                delete s.borderRight;
                return s;
            };
            
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
                        is_client_data: row.is_client_data || false,
                        client_code: '225'
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

            const getGroupRows = (targetRow) => {
                const idx = tableData.value.findIndex(r => r.id === targetRow.id);
                if (idx === -1) return [targetRow];
                
                let startIdx = idx;
                while (startIdx > 0) {
                    const prev = tableData.value[startIdx - 1];
                    if (prev.date === targetRow.date && prev.client_name === targetRow.client_name && prev.remark && (prev.remark.includes('同下批') || prev.remark.includes('及下批') || prev.remark.includes('一齊'))) {
                        startIdx--;
                    } else {
                        break;
                    }
                }
                
                let endIdx = idx;
                while (endIdx < tableData.value.length - 1) {
                    const curr = tableData.value[endIdx];
                    if (curr.remark && (curr.remark.includes('同下批') || curr.remark.includes('及下批') || curr.remark.includes('一齊'))) {
                        const next = tableData.value[endIdx + 1];
                        if (next.date === targetRow.date && next.client_name === targetRow.client_name) {
                            endIdx++;
                        } else {
                            break;
                        }
                    } else {
                        break;
                    }
                }
                
                const group = tableData.value.slice(startIdx, endIdx + 1);
                const hasGrouping = group.some(r => r.remark && (r.remark.includes('同下批') || r.remark.includes('及下批') || r.remark.includes('共') || r.remark.includes('一齊')));
                
                if (hasGrouping && group.length > 1) {
                    return group;
                }
                return [targetRow];
            };

            const getGroupTotalWeight = (row) => {
                const group = getGroupRows(row);
                if (group.length <= 1) return '';
                
                let maxWeight = -1;
                let maxWeightId = null;
                let totalW = 0;
                for (let i = 0; i < group.length; i++) {
                    const r = group[i];
                    const w = parseFloat(r.weight) || 0;
                    totalW += w;
                    if (w > maxWeight) {
                        maxWeight = w;
                        maxWeightId = r.id;
                    }
                }
                
                if (row.id === maxWeightId) {
                    return totalW;
                }
                return '';
            };

            const recalculateAndSave = async (row) => {
                if (row.weight) row.weight = Math.round(row.weight);
                
                const group = getGroupRows(row);
                
                if (group.length === 1) {
                    const textToCheck = (row.location || '') + ' ' + (row.remark || '');
                    const newAmount = calculateFreight(row.weight, textToCheck);
                    if (newAmount > 0) row.amount = newAmount;
                    await updateRow(row);
                    return;
                }
                
                let totalWeight = 0;
                let combinedText = '';
                let maxWeight = -1;
                let maxWeightIndex = 0;
                let tongXiaPiIndex = -1;
                
                for (let i = 0; i < group.length; i++) {
                    const r = group[i];
                    if (r.weight) {
                        r.weight = Math.round(r.weight);
                        totalWeight += r.weight;
                        if (r.weight > maxWeight) {
                            maxWeight = r.weight;
                            maxWeightIndex = i;
                        }
                    }
                    if (tongXiaPiIndex === -1 && r.remark && r.remark.includes('同下批')) {
                        tongXiaPiIndex = i;
                    }
                    combinedText += (r.location || '') + ' ' + (r.remark || '') + ' ';
                }
                
                const targetIndex = tongXiaPiIndex !== -1 ? tongXiaPiIndex : maxWeightIndex;
                
                const newAmount = calculateFreight(totalWeight, combinedText);
                const finalAmount = newAmount > 0 ? newAmount : 0;
                
                for (let i = 0; i < group.length; i++) {
                    if (i === targetIndex) {
                        group[i].amount = finalAmount;
                    } else {
                        group[i].amount = 0;
                    }
                    await updateRow(group[i]);
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
                    value: field === 'selected' ? selectedRows.value.includes(tableData.value[index].id) : tableData.value[index][field]
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
                    
                    if (field === 'selected') {
                        const rowId = tableData.value[i].id;
                        if (value === true && !selectedRows.value.includes(rowId)) {
                            selectedRows.value.push(rowId);
                        } else if (value === false) {
                            selectedRows.value = selectedRows.value.filter(id => id !== rowId);
                        }
                        continue;
                    }

                    tableData.value[i][field] = value;
                    if (field === 'remark') {
                        await handleRemarkChange(tableData.value[i], i);
                    } else if (field === 'weight' || field === 'location') {
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
                client_name: '',
                bill_no: '',
                pieces: null,
                weight: null,
                amount: null,
                location: '',
                remark: '',
                client_code: '225'
            });

            const calculateFreight = (weight, remark) => {
                const r = remark || '';

                let vehicle = null;
                if (r.match(/3\.49噸/)) vehicle = '3.49';
                else if (r.match(/6\.8噸/)) vehicle = '6.8';
                else if (r.match(/8\.8噸/)) vehicle = '8.8';
                else if (r.match(/15噸/)) vehicle = '15';
                else if (r.match(/17噸/)) vehicle = '17';

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
                    const finalPrice = matrixA_FTL[regionA]?.[vehicle];
                    return finalPrice !== undefined ? finalPrice : -1;
                }

                if (!weight) return 0;
                const w = parseFloat(weight);
                if (isNaN(w) || w <= 0) return 0;

                let basePrice = 0;
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

                if (typeof regionA === 'string' && regionA.startsWith('2')) {
                    if (regionA === '2a') basePrice += 220;
                    if (regionA === '2b') basePrice += 330;
                    if (regionA === '2c') basePrice += 440;
                    if (regionA === '2d') basePrice += 550;
                    if (regionA === '2e') basePrice += 660;
                    return basePrice;
                } else if (regionA === 3) {
                    if (w <= 100) return 440;
                    if (w <= 300) return 770;
                    if (w <= 500) return 990;
                    return 1320; 
                } else if (regionA === 4) {
                    if (w <= 100) return 550;
                    if (w <= 300) return 880;
                    if (w <= 400) return 1100;
                    if (w <= 500) return 1210;
                    return 1430;
                } else if (regionA === 5) {
                    if (w <= 100) return 660;
                    if (w <= 300) return 880;
                    if (w <= 400) return 1100;
                    if (w <= 500) return 1320;
                    return 1540;
                }

                return basePrice;
            };

            watch([() => newRow.value.weight, () => newRow.value.location, () => newRow.value.remark], ([newWeight, newLoc, newRemark]) => {
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
            });

            const previewFreight = (row) => {
                const group = getGroupRows(row);
                if (group.length === 1) {
                    const textToCheck = (row.location || '') + ' ' + (row.remark || '');
                    const newAmount = calculateFreight(row.weight, textToCheck);
                    if (newAmount > 0) {
                        row.amount = newAmount;
                    } else if (newAmount === -1) {
                        row.amount = 0;
                    }
                    return;
                }
                
                let totalWeight = 0;
                let combinedText = '';
                let maxWeight = -1;
                let maxWeightIndex = 0;
                let tongXiaPiIndex = -1;
                
                for (let i = 0; i < group.length; i++) {
                    const r = group[i];
                    const w = parseFloat(r.weight) || 0;
                    totalWeight += w;
                    if (w > maxWeight) {
                        maxWeight = w;
                        maxWeightIndex = i;
                    }
                    if (tongXiaPiIndex === -1 && r.remark && r.remark.includes('同下批')) {
                        tongXiaPiIndex = i;
                    }
                    combinedText += (r.location || '') + ' ' + (r.remark || '') + ' ';
                }
                
                const targetIndex = tongXiaPiIndex !== -1 ? tongXiaPiIndex : maxWeightIndex;
                
                const newAmount = calculateFreight(totalWeight, combinedText);
                const finalAmount = newAmount > 0 ? newAmount : (newAmount === -1 ? 0 : 0);
                
                for (let i = 0; i < group.length; i++) {
                    group[i].amount = (i === targetIndex) ? finalAmount : 0;
                }
            };

            const fetchData = async () => {
                try {
                    const response = await fetch('/api/waybills?client_code=225');
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
                    let isGrouped = false;
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
                        isGrouped = true;
                    } else if (newRow.value.remark && (newRow.value.remark.includes('同下批') || newRow.value.remark.includes('及下批') || newRow.value.remark.includes('一齊'))) {
                        isGrouped = true;
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
                        is_client_data: false,
                        client_code: '225'
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
                        const savedDate = newRow.value.date;
                        const savedClientName = newRow.value.client_name;
                        const savedRemark = newRow.value.remark;

                        newRow.value.bill_no = '';
                        newRow.value.amount = null;
                        newRow.value.pieces = null;
                        newRow.value.weight = null;
                        newRow.value.location = '';
                        newRow.value.remark = '';
                        isAmountManual.value = false;
                        
                        await fetchData();
                        
                        if (isGrouped) {
                            // Find the newly added row and trigger recalculate
                            const rows = tableData.value.filter(r => r.date === savedDate && r.client_name === savedClientName && r.remark === savedRemark);
                            if (rows.length > 0) {
                                await recalculateAndSave(rows[rows.length - 1]);
                            }
                        }
                        
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
                let htmlStylesData = [];
                
                if (htmlText) {
                    try {
                        const parser = new DOMParser();
                        const doc = parser.parseFromString(htmlText, 'text/html');
                        
                        // Parse style block for classes
                        let classStyles = {};
                        const styleTags = doc.querySelectorAll('style');
                        styleTags.forEach(style => {
                            const css = style.innerHTML;
                            const regex = /\.(\w+)\s*\{([^}]+)\}/g;
                            let match;
                            while ((match = regex.exec(css)) !== null) {
                                const className = match[1];
                                const rules = match[2].split(';');
                                let styleObj = {};
                                rules.forEach(rule => {
                                    const parts = rule.split(':');
                                    if (parts.length === 2) {
                                        const prop = parts[0].trim();
                                        const val = parts[1].trim();
                                        if (prop.includes('background')) styleObj.backgroundColor = val;
                                        if (prop.includes('border')) {
                                            const jsProp = prop.replace(/-([a-z])/g, g => g[1].toUpperCase());
                                            styleObj[jsProp] = val.replace(/windowtext/gi, 'black');
                                        }
                                        if (prop.includes('color')) styleObj.color = val;
                                        if (prop.includes('font-weight')) styleObj.fontWeight = val;
                                    }
                                });
                                classStyles[className] = styleObj;
                            }
                        });

                        const rows = doc.querySelectorAll('tr');
                        for (let r = 0; r < rows.length; r++) {
                            const cells = rows[r].querySelectorAll('td, th');
                            if (cells.length === 0) continue;
                            let isClientData = false;
                            let rowStyles = [];
                            
                            for (let c = 0; c < cells.length; c++) {
                                const cell = cells[c];
                                let cellStyle = {};
                                
                                // Merge from class
                                const className = cell.className || '';
                                className.split(' ').forEach(cls => {
                                    if (classStyles[cls]) {
                                        Object.assign(cellStyle, classStyles[cls]);
                                    }
                                });
                                
                                // Merge from inline
                                const bg = cell.style.backgroundColor || cell.style.background || cell.getAttribute('bgcolor');
                                if (bg) cellStyle.backgroundColor = bg;
                                
                                ['borderTop', 'borderBottom', 'borderLeft', 'borderRight', 'border'].forEach(prop => {
                                    if (cell.style[prop]) {
                                        cellStyle[prop] = cell.style[prop].replace(/windowtext/gi, 'black');
                                    }
                                });
                                if (cell.style.fontWeight) cellStyle.fontWeight = cell.style.fontWeight;
                                if (cell.style.color) cellStyle.color = cell.style.color;

                                // Check yellow background for legacy is_client_data
                                if (cellStyle.backgroundColor && (cellStyle.backgroundColor.includes('255, 255, 0') || cellStyle.backgroundColor.toLowerCase().includes('ffff00') || cellStyle.backgroundColor.toLowerCase() === 'yellow' || cellStyle.backgroundColor.includes('rgb(255, 255,'))) {
                                    isClientData = true;
                                }
                                rowStyles.push(cellStyle);
                            }
                            htmlBgData.push(isClientData);
                            htmlStylesData.push(rowStyles);
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

                const fields = ['date', 'client_name', 'bill_no', 'pieces', 'weight', 'amount', 'location', 'remark'];
                
                const isNewRowTr = tr.classList.contains('bg-blue-50');
                let rowIndex = isNewRowTr ? tableData.value.length : tableData.value.findIndex(row => row.id == tr.getAttribute('data-id'));

                let pastedNewRows = [];
                let modifiedOldRows = [];
                let errorMessages = [];

                for (let r = 0; r < plainRows.length; r++) {
                    const rowVals = plainRows[r];
                    const isClientData = htmlBgData[r] || false;
                    const rowStyles = htmlStylesData[r] || [];
                    
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
                        if (rowStyles.length > 0) {
                            if (!targetRow.styles) targetRow.styles = [];
                            // Ensure the array has enough elements
                            while(targetRow.styles.length < fields.length) targetRow.styles.push({});
                            
                            // Align pasted styles with the columns
                            for (let i = 0; i < rowStyles.length; i++) {
                                if (startColIndex + i < fields.length) {
                                    targetRow.styles[startColIndex + i] = rowStyles[i];
                                }
                            }
                            
                            // Force reactivity update in Vue by replacing the array reference
                            targetRow.styles = [...targetRow.styles];
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
                            const amt = calculateFreight(targetRow.weight, textToCheck);
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

            const undoAction = async () => {
                if (!undoData) return;
                showToast.value = false;
                
                if (undoData.type === 'delete') {
                    // Restore deleted rows by creating them again
                    for (const row of undoData.deletedRows) {
                        try {
                            await fetch('/api/waybills', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                                body: JSON.stringify(row)
                            });
                        } catch (e) { console.error(e); }
                    }
                } else {
                    // Default to undo paste behavior
                    for (const id of undoData.newRowIds || []) {
                        try {
                            await fetch(`/api/waybills/${id}`, { method: 'DELETE' });
                        } catch (e) { console.error(e); }
                    }
                    
                    for (const oldRow of undoData.oldRows || []) {
                        try {
                            await fetch(`/api/waybills/${oldRow.id}`, {
                                method: 'PUT',
                                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                                body: JSON.stringify(oldRow)
                            });
                        } catch (e) { console.error(e); }
                    }
                }
                
                undoData = null;
                await fetchData();
            };

            const selectedRows = ref([]);
            
            const isAllSelected = computed(() => {
                return tableData.value.length > 0 && selectedRows.value.length === tableData.value.length;
            });
            
            const toggleAllSelection = (e) => {
                if (e.target.checked) {
                    selectedRows.value = tableData.value.map(r => r.id);
                } else {
                    selectedRows.value = [];
                }
            };
            
            const deleteSelected = async () => {
                if (!confirm(`確定要刪除選取的 ${selectedRows.value.length} 筆資料嗎？`)) return;
                
                // Save rows to be deleted for undo functionality
                const rowsToDelete = tableData.value.filter(row => selectedRows.value.includes(row.id));
                undoData = {
                    type: 'delete',
                    deletedRows: rowsToDelete
                };
                
                try {
                    let hasError = false;
                    for (const id of selectedRows.value) {
                        const response = await fetch(`/api/waybills/${id}`, { method: 'DELETE' });
                        if (!response.ok) hasError = true;
                    }
                    
                    if (hasError) {
                        alert("部分資料刪除失敗");
                    }
                    
                    selectedRows.value = [];
                    await fetchData();
                    
                    toastMessage.value = `已刪除 ${undoData.deletedRows.length} 筆資料`;
                    showToast.value = true;
                    setTimeout(() => { showToast.value = false; }, 8000);
                } catch (error) {
                    console.error("Error deleting data:", error);
                    alert("刪除失敗");
                }
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
                    const response = await fetch('/api/waybills/truncate?client_code=225', {
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

            const uniqueLocations = computed(() => {
                const locs = new Set();
                tableData.value.forEach(row => {
                    if (row.location) locs.add(row.location);
                });
                return Array.from(locs).sort();
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

            const scrollToTop = () => {
                window.scrollTo({
                    top: 0,
                    behavior: 'smooth'
                });
            };

            const scrollToBottom = () => {
                window.scrollTo({
                    top: document.body.scrollHeight,
                    behavior: 'smooth'
                });
            };

            const exportExcel = () => {
                if (typeof XLSX === 'undefined') {
                    alert('Excel 匯出模組尚未載入完成，請稍後再試。');
                    return;
                }
                const wsData = tableData.value.map(row => ({
                    '日期': row.date,
                    '客戶名稱': row.client_name,
                    '提單號碼': row.bill_no,
                    '件數': row.pieces,
                    '重量': row.weight,
                    '運費': row.amount,
                    '地點': row.location,
                    '備註': row.remark
                }));
                                let minDate = '';
                let maxDate = '';
                let clientName = '';
                if (tableData.value.length > 0) {
                    const dates = tableData.value.map(r => r.date).filter(d => !!d).sort();
                    if (dates.length > 0) {
                        minDate = dates[0];
                        maxDate = dates[dates.length - 1];
                    }
                    clientName = tableData.value[0].client_name || '';
                }
                const dateRange = (minDate && maxDate) ? `${minDate}-${maxDate}` : '';
                const today = new Date();
                const formattedToday = `${today.getFullYear() - 1911}/${String(today.getMonth()+1).padStart(2, '0')}/${String(today.getDate()).padStart(2, '0')}`;
                
                const colHeaders = wsData.length > 0 ? Object.keys(wsData[0]) : [];
                const aoa = [
                    ['', '', '', '', '', '', '', ''],
                    ['運送公司:', '欣華運通有限公司', '叫車公司:', clientName, '', '', '', ''],
                    ['運送日期:', dateRange, '製表日期 :', formattedToday, '', '', '', ''],
                    ['', '', '', '', '', '', '', ''],
                    colHeaders
                ];
                let totalPieces = 0, totalWeight = 0, totalAmount = 0;
                wsData.forEach(row => {
                    aoa.push(Object.values(row));
                    totalPieces += (Number(row['件數']) || 0);
                    totalWeight += (Number(row['重量']) || 0);
                    totalAmount += (Number(row['運費']) || 0);
                });
                aoa.push(['', '', '總計', totalPieces, totalWeight, totalAmount, '', '']);
                const ws = XLSX.utils.aoa_to_sheet(aoa);
                ws['!cols'] = [
                    { wch: 15 }, // Date
                    { wch: 25 }, // Client Name
                    { wch: 25 }, // Bill No
                    { wch: 12 }, // Pieces
                    { wch: 12 }, // Weight
                    { wch: 15 }, // Amount
                    { wch: 18 }, // Location
                    { wch: 30 }  // Remark
                ];
                
                // Add styles
                const range = XLSX.utils.decode_range(ws['!ref']);
                for(let R = range.s.r; R <= range.e.r; ++R) {
                    for(let C = range.s.c; C <= range.e.c; ++C) {
                        const cell_address = {c:C, r:R};
                        const cell_ref = XLSX.utils.encode_cell(cell_address);
                        
                        // FIX: Ensure empty cells are created so they can get background color!
                        if(!ws[cell_ref]) ws[cell_ref] = {t:'s', v:''};
                        if (!ws[cell_ref].s) ws[cell_ref].s = {};
                        ws[cell_ref].s.font = { name: "微軟正黑體", sz: 12 };
                        
                        // Right-align numeric columns (Pieces, Weight, Amount)
                        if (C === 3 || C === 4 || C === 5) {
                            ws[cell_ref].s.alignment = { horizontal: "right" };
                        }
                        
                        // Header styling for Row 5 (index 4)
                        if (R === 4) {
                            ws[cell_ref].s.border = {
                                top: { style: 'medium', color: { auto: 1 } },
                                bottom: { style: 'medium', color: { auto: 1 } }
                            };
                            ws[cell_ref].s.font.bold = true;
                        }
                        
                        // Total row styling (last row)
                        if (R === range.e.r && R > 4) {
                            if (C === 2) ws[cell_ref].s.alignment = { horizontal: "right" };
                            ws[cell_ref].s.font = { name: "微軟正黑體", sz: 12, bold: true };
                            ws[cell_ref].s.border = {
                                top: { style: 'thin', color: { auto: 1 } },
                                bottom: { style: 'double', color: { auto: 1 } }
                            };
                        }
                    }
                }
                
                // Data rows start at index 5
                const dataStartRow = 5;
                for (let i = 0; i < tableData.value.length; i++) {
                    const rowData = tableData.value[i];
                    const R = dataStartRow + i;
                    for(let C = range.s.c; C <= range.e.c; ++C) {
                        const cell_ref = XLSX.utils.encode_cell({c:C, r:R});
                        
                        // Ensure cell exists
                        if (!ws[cell_ref]) ws[cell_ref] = {t:'s', v:''};
                        if (!ws[cell_ref].s) ws[cell_ref].s = {};
                        
                        const cellStyleIndex = C - range.s.c;
                        const customStyle = rowData.styles ? rowData.styles[cellStyleIndex] : null;
                        

                        
                        if (customStyle) {
                            // Background
                            if (customStyle.backgroundColor) {
                                let bg = customStyle.backgroundColor;
                                if (bg.includes('255, 255, 0') || bg.toLowerCase().includes('ffff00') || bg.toLowerCase() === 'yellow' || bg.includes('rgb(255, 255,')) {
                                    ws[cell_ref].s.fill = { patternType: "solid", fgColor: { rgb: "FFFF00" } };
                                } else {
                                    const hexMatch = bg.match(/#([0-9a-fA-F]{6})/);
                                    if (hexMatch) {
                                        ws[cell_ref].s.fill = { patternType: "solid", fgColor: { rgb: hexMatch[1].toUpperCase() } };
                                    }
                                }
                            }
                            // Border
                            ws[cell_ref].s.border = {
                                top: { style: thin, color: { auto: 1 } },
                                bottom: { style: thin, color: { auto: 1 } },
                                left: { style: thin, color: { auto: 1 } },
                                right: { style: thin, color: { auto: 1 } }
                            };
                    }
                }
                
                const wb = XLSX.utils.book_new();
                XLSX.utils.book_append_sheet(wb, ws, "運費明細");
                XLSX.writeFile(wb, "225鴻天運費明細.xlsx");
            };

            return {
                fontSize,
                tableData,
                uniqueClientNames,
                uniqueLocations,
                newRow,
                addRow,
                updateRow,
                deleteRow,
                handleArrowKeys,
                handlePaste,
                scrollToTop,
                scrollToBottom,
                exportExcel,
                getCellStyle,
                undoAction,
                clearAllData,
                selectedRows,
                isAllSelected,
                toggleAllSelection,
                deleteSelected,
                totalAmount,
                totalPieces,
                totalWeight,
                getGroupTotalWeight,
                startFill,
                isFillHighlighted,
                showToast,
                toastMessage,
                undoAction,
                handleRemarkChange,
                previewFreight
            };
        }
    }).mount('#app');
</script>

</body>
</html>
