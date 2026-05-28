<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="csrf-token" content="{{ csrf_token() }}">
    <title>合併 Excel 報表</title>
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Vue 3 -->
    <script src="https://unpkg.com/vue@3/dist/vue.global.prod.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700;900&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Noto Sans TC', sans-serif;
            background-color: #f3f4f6;
        }
        [v-cloak] { display: none; }
        .drag-active {
            border-color: #3b82f6 !important;
            background-color: #eff6ff !important;
        }
        .file-item {
            transition: all 0.2s;
        }
        .file-item.dragging {
            opacity: 0.5;
            background-color: #f3f4f6;
        }
    </style>
</head>
<body class="p-8 antialiased text-gray-800">

<div id="app" v-cloak class="max-w-4xl mx-auto bg-white rounded-2xl shadow-xl overflow-hidden">
    <!-- Header -->
    <div class="bg-gradient-to-r from-blue-500 to-indigo-600 p-6 text-white flex justify-between items-center">
        <div>
            <h1 class="text-3xl font-bold flex items-center gap-3">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2" />
                </svg>
                Excel 報表合併工具
            </h1>
            <p class="text-blue-100 mt-2">上傳多個 Excel 檔案，將它們合併為一個檔案。</p>
        </div>
        <a href="/" class="bg-white/20 hover:bg-white/30 backdrop-blur border border-white/30 text-white font-medium py-2 px-4 rounded-lg transition-colors flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clip-rule="evenodd" />
            </svg>
            回首頁
        </a>
    </div>

    <div class="p-8">
        <!-- Settings -->
        <div class="mb-8 bg-gray-50 p-6 rounded-xl border border-gray-200">
            <h2 class="text-lg font-bold mb-4 text-gray-700 flex items-center gap-2">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                合併設定
            </h2>
            <div class="grid md:grid-cols-2 gap-6">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">合併模式</label>
                    <div class="flex gap-4">
                        <label class="flex items-center gap-2 cursor-pointer">
                            <input type="radio" v-model="settings.mode" value="single" class="w-4 h-4 text-blue-600 focus:ring-blue-500 border-gray-300">
                                <span>合併成同一個工作表 (Sheet)</span>
                        </label>
                        <label class="flex items-center gap-2 cursor-pointer">
                            <input type="radio" v-model="settings.mode" value="multi" class="w-4 h-4 text-blue-600 focus:ring-blue-500 border-gray-300">
                            <span>每個檔案獨立工作表 (Sheets)</span>
                        </label>
                    </div>
                </div>
                <div v-if="settings.mode === 'single'">
                    <label class="block text-sm font-medium text-gray-700 mb-2">標題列處理</label>
                    <label class="flex items-center gap-2 cursor-pointer">
                        <input type="checkbox" v-model="settings.skipHeader" class="w-4 h-4 text-blue-600 rounded focus:ring-blue-500 border-gray-300">
                        <span>自動跳過後續檔案的第一列 (標題列)</span>
                    </label>
                </div>
            </div>
        </div>

        <!-- Drag & Drop Zone -->
        <div 
            class="border-2 border-dashed border-gray-300 rounded-2xl p-10 text-center cursor-pointer hover:bg-gray-50 transition-colors relative"
            :class="{'drag-active': isDragging}"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="handleDrop"
            @click="$refs.fileInput.click()"
        >
            <input type="file" ref="fileInput" multiple accept=".xlsx,.xls,.csv" class="hidden" @change="handleFileSelect">
            
            <div class="pointer-events-none">
                <svg class="mx-auto h-16 w-16 text-gray-400 mb-4" stroke="currentColor" fill="none" viewBox="0 0 48 48" aria-hidden="true">
                    <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
                <p class="text-xl text-gray-700 font-medium">點擊選擇檔案 或 拖曳檔案至此</p>
                <p class="text-sm text-gray-500 mt-2">支援 .xlsx, .xls 格式</p>
            </div>
        </div>

        <!-- File List -->
        <div v-if="files.length > 0" class="mt-8">
            <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-4 gap-4">
                <div>
                    <h3 class="text-lg font-bold text-gray-700">已選擇的檔案 (@{{ files.length }})</h3>
                    <p class="text-sm text-gray-500 mt-1">上下拖曳可調整合併順序</p>
                </div>
                
                <!-- Action Buttons (Top) -->
                <div class="flex justify-end gap-3 w-full sm:w-auto">
                    <button @click="clearFiles" class="px-5 py-2 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 transition-colors text-sm flex-1 sm:flex-none text-center">
                        清空列表
                    </button>
                    <button 
                        @click="submitMerge" 
                        :disabled="isSubmitting"
                        class="px-6 py-2 bg-blue-600 text-white font-bold rounded-lg shadow-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center gap-2 text-sm flex-1 sm:flex-none"
                    >
                        <svg v-if="isSubmitting" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        <span>@{{ isSubmitting ? '合併中...' : '開始合併並下載' }}</span>
                    </button>
                </div>
            </div>
            
            <ul class="border border-gray-200 rounded-xl divide-y divide-gray-200 bg-white shadow-sm overflow-hidden">
                <li 
                    v-for="(file, index) in files" 
                    :key="file.name + index"
                    draggable="true"
                    @dragstart="dragStart(index, $event)"
                    @dragover.prevent="dragOver(index)"
                    @drop="drop(index)"
                    @dragend="dragEnd"
                    class="file-item p-4 flex items-center justify-between hover:bg-gray-50 bg-white group cursor-move"
                    :class="{'dragging': draggedIndex === index}"
                >
                    <div class="flex items-center gap-4 truncate">
                        <div class="text-gray-400 cursor-move group-hover:text-gray-600">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
                            </svg>
                        </div>
                        <div class="w-10 h-10 bg-green-100 text-green-600 rounded-lg flex items-center justify-center flex-shrink-0">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                        </div>
                        <div class="truncate">
                            <p class="font-medium text-gray-800 truncate">@{{ file.name }}</p>
                            <p class="text-xs text-gray-500">@{{ formatSize(file.size) }}</p>
                        </div>
                    </div>
                    
                    <button @click="removeFile(index)" class="text-gray-400 hover:text-red-500 p-2 rounded-full hover:bg-red-50 transition-colors focus:outline-none flex-shrink-0">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                            <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
                        </svg>
                    </button>
                </li>
            </ul>

            <!-- Action Buttons -->
            <div class="mt-8 flex justify-end gap-4">
                <button @click="clearFiles" class="px-6 py-2 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 transition-colors">
                    清空列表
                </button>
                <button 
                    @click="submitMerge" 
                    :disabled="isSubmitting"
                    class="px-8 py-2 bg-blue-600 text-white font-bold rounded-lg shadow-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                    <svg v-if="isSubmitting" class="animate-spin -ml-1 mr-2 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span>@{{ isSubmitting ? '合併中，請稍候...' : '開始合併並下載' }}</span>
                </button>
            </div>
        </div>
    </div>
</div>

<script>
    const { createApp, ref } = Vue;

    createApp({
        setup() {
            const isDragging = ref(false);
            const files = ref([]);
            const isSubmitting = ref(false);
            const draggedIndex = ref(null);
            
            const settings = ref({
                mode: 'single', // single or multi
                skipHeader: true
            });

            const handleDrop = (e) => {
                isDragging.value = false;
                const droppedFiles = Array.from(e.dataTransfer.files);
                addFiles(droppedFiles);
            };

            const handleFileSelect = (e) => {
                const selectedFiles = Array.from(e.target.files);
                addFiles(selectedFiles);
                e.target.value = ''; // Reset input
            };

            const addFiles = (newFiles) => {
                const validFiles = newFiles.filter(file => {
                    return file.name.endsWith('.xlsx') || file.name.endsWith('.xls') || file.name.endsWith('.csv');
                });
                
                if (validFiles.length !== newFiles.length) {
                    alert('部分檔案格式不支援，僅支援 .xlsx, .xls, .csv 檔案');
                }
                
                files.value = [...files.value, ...validFiles];
            };

            const removeFile = (index) => {
                files.value.splice(index, 1);
            };

            const clearFiles = () => {
                files.value = [];
            };

            const formatSize = (bytes) => {
                if (bytes === 0) return '0 Bytes';
                const k = 1024;
                const sizes = ['Bytes', 'KB', 'MB', 'GB'];
                const i = Math.floor(Math.log(bytes) / Math.log(k));
                return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
            };

            // Drag and Drop reordering logic
            const dragStart = (index, e) => {
                draggedIndex.value = index;
                e.dataTransfer.effectAllowed = 'move';
                // Firefox requires dataTransfer data to be set
                e.dataTransfer.setData('text/plain', index);
            };

            const dragOver = (index) => {
                // Allows drop
            };

            const drop = (index) => {
                if (draggedIndex.value !== null && draggedIndex.value !== index) {
                    const items = [...files.value];
                    const draggedItem = items.splice(draggedIndex.value, 1)[0];
                    items.splice(index, 0, draggedItem);
                    files.value = items;
                }
            };

            const dragEnd = () => {
                draggedIndex.value = null;
            };

            const submitMerge = async () => {
                if (files.value.length === 0) {
                    alert('請先選擇檔案');
                    return;
                }

                isSubmitting.value = true;
                
                const formData = new FormData();
                files.value.forEach((file, index) => {
                    formData.append(`files[${index}]`, file);
                });
                formData.append('mode', settings.value.mode);
                formData.append('skip_header', settings.value.skipHeader ? '1' : '0');

                // CSRF Token
                const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

                try {
                    const response = await fetch('/merge-excel', {
                        method: 'POST',
                        headers: {
                            'X-CSRF-TOKEN': csrfToken || ''
                        },
                        body: formData
                    });

                    if (!response.ok) {
                        throw new Error('Server returned ' + response.status);
                    }

                    // Handle file download
                    const blob = await response.blob();
                    const contentDisposition = response.headers.get('Content-Disposition');
                    let filename = 'merged.xlsx';
                    if (contentDisposition) {
                        const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
                        if (filenameMatch && filenameMatch.length === 2)
                            filename = decodeURIComponent(filenameMatch[1]);
                    }

                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    window.URL.revokeObjectURL(url);
                    
                } catch (error) {
                    console.error('Error merging files:', error);
                    alert('合併過程中發生錯誤，請稍後再試。\n' + error.message);
                } finally {
                    isSubmitting.value = false;
                }
            };

            return {
                isDragging,
                files,
                settings,
                isSubmitting,
                draggedIndex,
                handleDrop,
                handleFileSelect,
                removeFile,
                clearFiles,
                formatSize,
                dragStart,
                dragOver,
                drop,
                dragEnd,
                submitMerge
            };
        }
    }).mount('#app');
</script>
</body>
</html>
