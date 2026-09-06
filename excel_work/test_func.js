
const isAmountManual = { value: false };
html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>客戶206 帳單格式</title>
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
        <div class="flex gap-2">
            <a href="/" class="bg-gray-500 hover:bg-gray-600 text-white font-bold py-2 px-4 rounded shadow transition-colors focus:outline-none focus:ring-0 flex items-center justify-center">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                </svg>
                回首頁
            </a>
            </div>
        <div class="flex items-center justify-center gap-4">
            <label for="fontSizeSlider" class="font-bold text-sm text-gray-700 whitespace-nowrap">字體大小調整 (目前: @{{ fontSize }}px)</label>
            <input type="range" id="fontSizeSlider" v-model="fontSize" min="10" max="24" step="1" class="w-32 md:w-48 cursor-pointer focus:outline-none focus:ring-0">
        </div>
        <div>
            <div class="flex gap-2">
                <button @click="scrollToBottom" class="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded shadow transition-colors flex items-center gap-2 focus:outline-none focus:ring-0">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"></path></svg>
                移至最底
            </button>
                <button @click="clearAllData" class="bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded shadow transition-colors focus:outline-none focus:ring-0">
                清空全部資料
            </button>
            </div>
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
                <div class="font-bold w-24">叫車公司：</div>
                <div>公成興股份有限公司</div>
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
        <!-- 台北市區 -->
        <option value="台北"></option>
        <!-- 近郊 (+220) -->
        <option value="景美"></option>
        <option value="天母"></option>
        <option value="士林"></option>
        <option value="大直"></option>
        <option value="內湖"></option>
        <option value="松山"></option>
        <option value="萬華"></option>
        <option value="社子"></option>
        <!-- 近郊 (+330) -->
        <option value="三重"></option>
        <option value="中和"></option>
        <option value="永和"></option>
        <option value="南港"></option>
        <option value="板橋"></option>
        <option value="石牌"></option>
        <option value="北投"></option>
        <option value="木柵"></option>
        <option value="新店"></option>
        <option value="蘆洲"></option>
        <!-- 近郊 (+440) -->
        <option value="五股"></option>
        <option value="泰山"></option>
        <option value="新莊"></option>
        <option value="樹林"></option>
        <!-- 近郊 (+550) -->
        <option value="汐止"></option>
        <option value="土城"></option>
        <option value="楊梅"></option>
        <option value="深坑"></option>
        <!-- 近郊 (+660) -->
        <option value="淡水"></option>
        <option value="八里"></option>
        <!-- 桃園區 -->
        <option value="蘆竹"></option>
        <option value="大園"></option>
        <option value="中壢"></option>
        <option value="內壢"></option>
        <option value="林口"></option>
        <option value="龜山"></option>
        <option value="桃園"></option>
        <!-- 桃園遠區 -->
        <option value="新屋"></option>
        <option value="八德"></option>
        <option value="觀音"></option>
        <option value="平鎮"></option>
        <option value="龍潭"></option>
        <option value="三峽"></option>
        <option value="鶯歌"></option>
        <!-- 遠區 -->
        <option value="新竹"></option>
        <option value="湖口"></option>
        <option value="基隆"></option>
        <option value="大溪"></option>
        <option value="新豐"></option>
        <option value="七堵"></option>
        <option value="瑞芳"></option>
        <!-- 特殊 -->
        <option value="冷泉港"></option>
        <option value="台中"></option>
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
            <thead class="sticky top-0 z-10 bg-gray-100 shadow-sm">
                <tr class="border-b-2 border-black">
                    <th style="width: 100px;">日期</th>
                    <th @click="sortBy('bill_no')" style="width: 100px;" class="cursor-pointer hover:bg-gray-200 select-none">
                        帳單編號 <span v-if="sortState.column === 'bill_no'" class="text-xs">@{{ sortState.order === 'asc' ? '▲' : '▼' }}</span>
                    </th>
                    <th @click="sortBy('client_name')" style="width: 100px;" class="cursor-pointer hover:bg-gray-200 select-none">
                        客戶名稱 <span v-if="sortState.column === 'client_name'" class="text-xs">@{{ sortState.order === 'asc' ? '▲' : '▼' }}</span>
                    </th>
                    <th @click="sortBy('amount')" style="width: 100px;" class="text-right cursor-pointer hover:bg-gray-200 select-none">
                        運費金額 <span v-if="sortState.column === 'amount'" class="text-xs">@{{ sortState.order === 'asc' ? '▲' : '▼' }}</span>
                    </th>
                    <th @click="sortBy('pieces')" style="width: 60px;" class="text-right cursor-pointer hover:bg-gray-200 select-none">
                        件數 <span v-if="sortState.column === 'pieces'" class="text-xs">@{{ sortState.order === 'asc' ? '▲' : '▼' }}</span>
                    </th>
                    <th @click="sortBy('weight')" style="width: 60px;" class="text-right cursor-pointer hover:bg-gray-200 select-none">
                        重量 <span v-if="sortState.column === 'weight'" class="text-xs">@{{ sortState.order === 'asc' ? '▲' : '▼' }}</span>
                    </th>
                    <th style="width: 100px;">地點</th>
                    <th style="width: 150px;">備註</th>
                    <th style="width: 60px;" class="text-right">總重</th>
                    <th style="width: 60px;" class="text-center">
                        <input type="checkbox" @change="toggleAllSelection" :checked="isAllSelected" class="w-4 h-4 cursor-pointer align-middle" title="全選/取消全選">
                    </th>
                </tr>
            </thead>
            <tbody @paste="handlePaste">
                <!-- Data Rows -->
                <tr v-for="(row, index) in tableData" :key="row.id || index" :data-id="row.id" class="border-b border-gray-300 hover:bg-gray-50">
                    <td class="p-0 relative group" :class="{'fill-highlight': isFillHighlighted(index, 'date')}" :style="getCellStyle(row, 0)"><input autocomplete="off" @keydown="handleArrowKeys" @change="updateRow(row)" type="text" v-model.trim="row.date" class="nav-input w-full p-1 bg-transparent border-0 focus:outline-none focus:bg-white focus:ring-1 focus:ring-blue-400" @focus="$event.target.select()"><div class="fill-handle" @mousedown="startFill(index, 'date', $event)"></div></td>
                    <td class="p-0 relative group" :class="{'fill-highlight': isFillHighlighted(index, 'bill_no')}" :style="getCellStyle(row, 1)"><input autocomplete="off" @keydown="handleArrowKeys" @change="updateRow(row)" type="text" v-model.trim="row.bill_no" class="nav-input w-full p-1 bg-transparent border-0 focus:outline-none focus:bg-white focus:ring-1 focus:ring-blue-400" @focus="$event.target.select()"><div class="fill-handle" @mousedown="startFill(index, 'bill_no', $event)"></div></td>
                    <td class="p-0 relative group" :class="{'fill-highlight': isFillHighlighted(index, 'client_name')}" :style="getCellStyle(row, 2)"><input list="client-names" autocomplete="off" @keydown="handleArrowKeys" @change="updateRow(row)" type="text" v-model.trim="row.client_name" class="nav-input w-full p-1 bg-transparent border-0 focus:outline-none focus:bg-white focus:ring-1 focus:ring-blue-400" @focus="$event.target.select()"><div class="fill-handle" @mousedown="startFill(index, 'client_name', $event)"></div></td>
                    <td class="p-0 text-right relative group" :class="{'fill-highlight': isFillHighlighted(index, 'amount')}" :style="getCellStyle(row, 3)"><input autocomplete="off" @keydown="handleArrowKeys" @change="updateRow(row)" type="text" v-model.number="row.amount" class="nav-input w-full p-1 bg-transparent border-0 text-right focus:outline-none focus:bg-white focus:ring-1 focus:ring-blue-400" @focus="$event.target.select()"><div class="fill-handle" @mousedown="startFill(index, 'amount', $event)"></div></td>
                    <td class="p-0 relative group" :class="{'fill-highlight': isFillHighlighted(index, 'pieces')}" :style="getCellStyle(row, 4)"><input autocomplete="off" @keydown="handleArrowKeys" @change="updateRow(row)" type="text" v-model.number="row.pieces" class="nav-input w-full p-1 bg-transparent border-0 text-right focus:outline-none focus:bg-white focus:ring-1 focus:ring-blue-400" @focus="$event.target.select()"><div class="fill-handle" @mousedown="startFill(index, 'pieces', $event)"></div></td>
                    <td class="p-0 relative group" :class="{'fill-highlight': isFillHighlighted(index, 'weight')}" :style="getCellStyle(row, 5)"><input autocomplete="off" @keydown="handleArrowKeys" @input="previewFreight(row)" @change="recalculateAndSave(row)" type="text" v-model.number="row.weight" class="nav-input w-full p-1 bg-transparent border-0 text-right focus:outline-none focus:bg-white focus:ring-1 focus:ring-blue-400" @focus="$event.target.select()"><div class="fill-handle" @mousedown="startFill(index, 'weight', $event)"></div></td>
                    <td class="p-0 relative group" :class="{'fill-highlight': isFillHighlighted(index, 'location')}" :style="getCellStyle(row, 6)"><input list="location-names" autocomplete="off" @keydown="handleArrowKeys" @input="previewFreight(row)" @change="recalculateAndSave(row)" type="text" v-model.trim="row.location" class="nav-input w-full p-1 bg-transparent border-0 focus:outline-none focus:bg-white focus:ring-1 focus:ring-blue-400" @focus="$event.target.select()"><div class="fill-handle" @mousedown="startFill(index, 'location', $event)"></div></td>
                    <td class="p-0 relative group" :class="{'fill-highlight': isFillHighlighted(index, 'remark')}" :style="getCellStyle(row, 7)"><input list="remark-options" autocomplete="off" @keydown="handleArrowKeys" @input="previewFreight(row)" @change="handleRemarkChange(row, index)" type="text" v-model.trim="row.remark" class="nav-input w-full p-1 bg-transparent border-0 focus:outline-none focus:bg-white focus:ring-1 focus:ring-blue-400" @focus="$event.target.select()"><div class="fill-handle" @mousedown="startFill(index, 'remark', $event)"></div></td>
                    <td class="p-1 text-right text-blue-600 font-bold bg-gray-50 align-middle">@{{ getGroupTotalWeight(row) }}</td>
                    <td class="p-0 text-center align-middle relative group" :class="{'fill-highlight': isFillHighlighted(index, 'selected')}">
                        
                        <div class="flex items-center justify-center gap-1 min-w-[50px] py-1">
                            <input type="checkbox" v-model="selectedRows" :value="row.id" class="w-4 h-4 cursor-pointer align-middle opacity-50 group-hover:opacity-100 transition-opacity" :class="{'opacity-100': selectedRows.includes(row.id)}">
                            <button @click="insertRowAfter(index)" class="opacity-0 group-hover:opacity-100 bg-green-500 hover:bg-green-600 text-white font-bold px-1.5 py-0.5 rounded text-xs shadow focus:outline-none transition-opacity duration-200" title="在此行下方插入新行">＋</button>
                        </div>
                        <div class="fill-handle" @mousedown="startFill(index, 'selected', $event)"></div>
                    </td>
                </tr>

                <!-- Input Row (Moved to bottom) -->
                <tr class="bg-blue-50 border-t-2 border-blue-200">
                    <td><input autocomplete="off" @keyup.enter="addRow" @keydown="handleArrowKeys" type="text" v-model.trim="newRow.date" class="nav-input w-full border p-1" placeholder="日期" @focus="$event.target.select()"></td>
                    <td><input autocomplete="off" @keyup.enter="addRow" @keydown="handleArrowKeys" type="text" v-model.trim="newRow.bill_no" class="nav-input w-full border p-1" placeholder="帳單編號" @focus="$event.target.select()"></td>
                    <td><input list="client-names" autocomplete="off" @keyup.enter="addRow" @keydown="handleArrowKeys" type="text" v-model.trim="newRow.client_name" class="nav-input w-full border p-1" placeholder="客戶" @focus="$event.target.select()"></td>
                    <td><input autocomplete="off" @keyup.enter="addRow" @keydown="handleArrowKeys" @input="isAmountManual = true" type="text" v-model.number="newRow.amount" class="nav-input w-full border p-1 text-right" placeholder="金額" @focus="$event.target.select()"></td>
                    <td><input autocomplete="off" @keyup.enter="addRow" @keydown="handleArrowKeys" type="text" v-model.number="newRow.pieces" class="nav-input w-full border p-1 text-right" placeholder="件數" @focus="$event.target.select()"></td>
                    <td><input autocomplete="off" @keyup.enter="addRow" @keydown="handleArrowKeys" type="text" v-model.number="newRow.weight" class="nav-input w-full border p-1 text-right" placeholder="重量" @focus="$event.target.select()"></td>
                    <td><input list="location-names" autocomplete="off" @keyup.enter="addRow" @keydown="handleArrowKeys" type="text" v-model.trim="newRow.location" class="nav-input w-full border p-1" placeholder="地點" @focus="$event.target.select()"></td>
                    <td><input list="remark-options" autocomplete="off" @keyup.enter="addRow" @keydown="handleArrowKeys" type="text" v-model.trim="newRow.remark" class="nav-input w-full border p-1" placeholder="備註" @focus="$event.target.select()"></td>
                    <td></td>
                    <td class="text-center">
                        <button @click="addRow" class="bg-blue-500 hover:bg-blue-600 text-white px-3 py-1 rounded text-sm shadow">新增</button>
                    </td>
                </tr>

                <!-- Total Row -->
                <tr class="font-bold bg-gray-100 border-t-2 border-black">
                    <td colspan="3" class="text-center">總計</td>
                    <td class="text-right">@{{ totalAmount }}</td>
                    <td class="text-right"></td>
                    <td class="text-right"></td>
                    <td colspan="4"></td>
                </tr>
            </tbody>
        </table>
    </div>

    <!-- Bottom Controls -->
    <div class="mt-4 p-4 bg-gray-50 border border-gray-300 rounded-lg shadow-sm">
        <div class="flex flex-wrap gap-4 items-center justify-between">
            <div class="flex gap-4 items-center">
                <span class="text-gray-700 font-bold text-lg">快速排序：</span>
                <button @click="sortBy('bill_no')" class="bg-indigo-500 hover:bg-indigo-600 text-white font-bold py-2 px-4 rounded shadow transition-colors flex items-center gap-2">
                    <span>依帳單編號排序</span>
                    <span v-if="sortState.column === 'bill_no'" class="text-xs bg-indigo-700 px-1 rounded">@{{ sortState.order === 'asc' ? '▲' : '▼' }}</span>
                </button>
                <button @click="resetView" class="bg-gray-500 hover:bg-gray-600 text-white font-bold py-2 px-4 rounded shadow transition-colors flex items-center gap-2">
                    <span>恢復介面</span>
                </button>
            
                
            
            <button @click="scrollToTop" class="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded shadow transition-colors flex items-center gap-2">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18"></path></svg>
                移至最上方
            </button>
            <a href="/" class="bg-gray-700 hover:bg-gray-800 text-white font-bold py-2 px-4 rounded shadow transition-colors">
                回首頁
            </a>
            <button @click="manualSave" class="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded shadow transition-colors">
                儲存資料
            </button>
            <button @click="exportExcel" class="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded shadow transition-colors">
                匯出 Excel
            </button>
            <button v-if="selectedRows.length > 0" @click="deleteSelected" class="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded shadow transition-colors">
                刪除選取項目 (@{{ selectedRows.length }})
            </button>

            </div>
        </div>
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
            const dbSavedClients = ref([]);
            
            const getCellStyle = (row, colIndex) => {
                if (!row || !row.styles || !row.styles[colIndex]) return {};
                const s = { ...row.styles[colIndex] };
                return s;
            };
            
            const isAmountManual = ref(false);
            const sortState = ref({ column: null, order: 'asc' });

            const manualSave = async () => {
                if (document.activeElement && document.activeElement.tagName === 'INPUT') {
                    document.activeElement.blur();
                }
                
                await new Promise(resolve => setTimeout(resolve, 100)); // wait for blur to process
                
                const hasOtherData = newRow.value.bill_no || 
                                     (newRow.value.amount !== null && newRow.value.amount !== '' && newRow.value.amount !== 0) || 
                                     (newRow.value.pieces !== null && newRow.value.pieces !== '' && newRow.value.pieces !== 0) || 
                                     (newRow.value.weight !== null && newRow.value.weight !== '' && newRow.value.weight !== 0) || 
                                     newRow.value.location || 
                                     newRow.value.remark;
                                     
                if (newRow.value.date && newRow.value.client_name && hasOtherData) {
                    await addRow();
                }
                
                toastMessage.value = '資料已確認儲存！';
                showToast.value = true;
                setTimeout(() => { showToast.value = false; }, 3000);
            };
            
            const resetView = async () => {
                sortState.value = { column: null, order: 'asc' };
                selectedRows.value = [];
                await fetchData();
                fetchSavedClients();
                
                toastMessage.value = `介面已恢復`;
                showToast.value = true;
                setTimeout(() => { showToast.value = false; }, 3000);
            };

            const sortBy = (column) => {
                if (sortState.value.column === column) {
                    sortState.value.order = sortState.value.order === 'asc' ? 'desc' : 'asc';
                } else {
                    sortState.value.column = column;
                    sortState.value.order = 'asc';
                }

                const groups = [];
                let i = 0;
                while (i < tableData.value.length) {
                    const row = tableData.value[i];
                    let endIdx = i;
                    while (endIdx < tableData.value.length - 1) {
                        const curr = tableData.value[endIdx];
                        if (curr.remark && (curr.remark.includes('同下批') || curr.remark.includes('及下批') || curr.remark.includes('一齊'))) {
                            const next = tableData.value[endIdx + 1];
                            if (next.date === row.date && next.client_name === row.client_name) {
                                endIdx++;
                            } else {
                                break;
                            }
                        } else {
                            break;
                        }
                    }
                    groups.push(tableData.value.slice(i, endIdx + 1));
                    i = endIdx + 1;
                }

                // If multiple rows are selected, only sort those groups. Otherwise, sort all groups.
                const hasSelection = selectedRows.value.length > 1;
                
                const groupsToSort = [];
                const indicesToSort = [];

                groups.forEach((group, index) => {
                    if (!hasSelection || group.some(row => selectedRows.value.includes(row.id))) {
                        groupsToSort.push(group);
                        indicesToSort.push(index);
                    }
                });

                groupsToSort.sort((groupA, groupB) => {
                    let valA, valB;
                    
                    if (['amount', 'pieces', 'weight'].includes(column)) {
                        valA = groupA.reduce((sum, r) => sum + (parseFloat(r[column]) || 0), 0);
                        valB = groupB.reduce((sum, r) => sum + (parseFloat(r[column]) || 0), 0);
                    } else {
                        valA = groupA[0][column] || '';
                        valB = groupB[0][column] || '';
                    }

                    let cmp = 0;
                    if (typeof valA === 'number' && typeof valB === 'number') {
                        cmp = valA - valB;
                    } else {
                        if (column === 'client_name' || column === 'location') {
                            cmp = valA.toString().localeCompare(valB.toString(), 'zh-TW', { collation: 'stroke' });
                        } else {
                            cmp = valA.toString().localeCompare(valB.toString(), undefined, { numeric: true, sensitivity: 'base' });
                        }
                    }

                    if (cmp !== 0) {
                        return sortState.value.order === 'asc' ? cmp : -cmp;
                    }
                    return 0;
                });

                if (hasSelection) {
                    groupsToSort.forEach(group => {
                        if (group.length > 1) {
                            const originalIds = group.map(r => r.id);
                            const originalRemarks = group.map(r => r.remark);
                            
                            group.sort((rowA, rowB) => {
                                let valA = rowA[column] || '';
                                let valB = rowB[column] || '';
                                let cmp = 0;
                                if (typeof valA === 'number' && typeof valB === 'number') {
                                    cmp = valA - valB;
                                } else {
                                    cmp = valA.toString().localeCompare(valB.toString(), undefined, { numeric: true, sensitivity: 'base' });
                                }
                                if (cmp !== 0) {
                                    return sortState.value.order === 'asc' ? cmp : -cmp;
                                }
                                return 0;
                            });

                            group.forEach((r, i) => {
                                r.id = originalIds[i];
                                r.remark = originalRemarks[i];
                            });
                        }
                    });
                }

                for (let j = 0; j < indicesToSort.length; j++) {
                    groups[indicesToSort[j]] = groupsToSort[j];
                }

                tableData.value = groups.flat();

                if (hasSelection) {
                    groupsToSort.forEach(group => {
                        if (group.length > 1) {
                            recalculateAndSave(group[0]);
                        }
                    });
                }
            };
            
            const handleArrowKeys = (e) => {
                if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Enter'].includes(e.key)) return;
                
                const inputs = Array.from(document.querySelectorAll('.nav-input'));
                const index = inputs.indexOf(e.target);
                if (index === -1) return;

                let nextIndex = null;
                const row = e.target.closest('tr');
                const cols = row ? row.querySelectorAll('.nav-input').length : 8;

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
                        forklift_fee: row.forklift_fee || 0,
                        location: row.location || '',
                        remark: row.remark || '',
                        is_client_data: row.is_client_data || false,
                        client_code: '206'
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
                    if (prev.date === targetRow.date && prev.remark && (prev.remark.includes('同下批') || prev.remark.includes('及下批') || prev.remark.includes('一齊'))) {
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
                        if (next.date === targetRow.date) {
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
                    const newAmount = calculateFreight(row.weight, textToCheck, row.client_name);
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
                
                const clientName = group[0].client_name || '';
                // For client 206, freight should be displayed in the row with the max weight, especially for "共*批"
                const hasGongPi = group.some(r => r.remark && r.remark.includes('共'));
                const targetIndex = hasGongPi ? maxWeightIndex : (tongXiaPiIndex !== -1 ? tongXiaPiIndex : maxWeightIndex);
                
                const newAmount = calculateFreight(totalWeight, combinedText, clientName);
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

            const previewFreight = (row) => {
                const group = getGroupRows(row);
                if (group.length === 1) {
                    const textToCheck = (row.location || '') + ' ' + (row.remark || '');
                    const newAmount = calculateFreight(row.weight, textToCheck, row.client_name);
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
                
                const clientName = group[0].client_name || '';
                // For client 206, freight should be displayed in the row with the max weight, especially for "共*批"
                const hasGongPi = group.some(r => r.remark && r.remark.includes('共'));
                const targetIndex = hasGongPi ? maxWeightIndex : (tongXiaPiIndex !== -1 ? tongXiaPiIndex : maxWeightIndex);
                
                const newAmount = calculateFreight(totalWeight, combinedText, clientName);
                const finalAmount = newAmount > 0 ? newAmount : (newAmount === -1 ? 0 : 0);
                
                for (let i = 0; i < group.length; i++) {
                    group[i].amount = (i === targetIndex) ? finalAmount : 0;
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

                let baseMonth = null;
                let baseDay = null;
                let baseYear = null;
                let dateType = null;
                
                if (field === 'date' && typeof value === 'string') {
                    const matchZh = value.match(/^(\d{1,2})月(\d{1,2})日$/);
                    const matchTw = value.match(/^(\d{2,3})\/(\d{1,2})\/(\d{1,2})$/);
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
                            newValue = `${tempDate.getMonth() + 1}月${tempDate.getDate()}日`;
                        } else if (dateType === 'tw') {
                            const newTwYear = tempDate.getFullYear() - 1911;
                            const mm = String(tempDate.getMonth() + 1).padStart(2, '0');
                            const dd = String(tempDate.getDate()).padStart(2, '0');
                            newValue = `${newTwYear}/${mm}/${dd}`;
                        }
                    }

                    tableData.value[i][field] = newValue;
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
                bill_no: '',
                client_name: '',
                amount: null,
                pieces: null,
                weight: null,
                location: '',
                remark: '',
                client_code: '206'
            });

            const calculateFreight = (weight, remark, client) => {
                let amt = _calculateFreight(weight, remark, client);
                if (amt > 0 && remark) {
                    if (remark.includes('+尾門')) {
                        amt += 500;
                    }
                    const overtimeMatch = remark.match(/\+加班費\s*(\d+)/);
                    if (overtimeMatch) {
                        amt += parseInt(overtimeMatch[1], 10);
                    }
                }
                return amt;
            };

            
console.log("Test 1:", _calculateFreight(0, "共十九批6.8噸+15噸車", "206"));
console.log("Test 2:", _calculateFreight(0, "共十九批6.8噸+15噸車", "其他"));
