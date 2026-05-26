<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>貨運帳務系統</title>
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Vue 3 -->
    <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
    <style>
        [v-cloak] { display: none; }
    </style>
</head>
<body class="bg-gray-100 p-8 font-sans antialiased text-gray-800">

<div id="app" v-cloak class="max-w-6xl mx-auto bg-white p-8 rounded-xl shadow-lg border border-gray-200">
    <div class="flex justify-between items-center mb-8 border-b pb-4 border-gray-200">
        <div>
            <h1 class="text-3xl font-bold text-gray-800 tracking-tight">每日貨運帳務系統</h1>
            <p class="text-sm text-gray-500 mt-1">動態單價與即時對帳面板</p>
        </div>
        <div class="flex items-center gap-4">
            <input type="date" v-model="currentDate" @change="fetchData" class="border rounded px-4 py-2 text-gray-700 shadow-sm focus:ring focus:ring-indigo-200 focus:outline-none">
            <button @click="saveData" class="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 px-6 rounded shadow transition duration-150 ease-in-out" :disabled="saving">
                <span v-if="saving">儲存中...</span>
                <span v-else>儲存當日對帳</span>
            </button>
        </div>
    </div>

    <div v-if="loading" class="text-center py-10 text-gray-500">
        載入資料中...
    </div>

    <div v-else>
        <!-- Data Table -->
        <div class="overflow-x-auto shadow rounded-lg border border-gray-200 mb-8">
            <table class="w-full text-left border-collapse">
                <thead>
                    <tr class="bg-gray-50 text-gray-700 uppercase text-xs tracking-wider border-b">
                        <th class="p-4 font-semibold">客戶名稱</th>
                        <th class="p-4 font-semibold">目的地</th>
                        <th class="p-4 font-semibold text-right">合約單價</th>
                        <th class="p-4 font-semibold text-center w-32">今日趟數</th>
                        <th class="p-4 font-semibold text-right">小計</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-200">
                    <tr v-for="(item, index) in tableData" :key="item.price.id" class="hover:bg-gray-50 transition">
                        <td class="p-4 text-gray-800 font-medium">@{{ item.price.client_name }}</td>
                        <td class="p-4 text-gray-600">@{{ item.price.destination }}</td>
                        <td class="p-4 text-right text-gray-600">@{{ formatCurrency(item.price.price) }}</td>
                        <td class="p-4 text-center">
                            <input type="number" min="0" v-model.number="item.trips_count" class="w-20 text-center border rounded px-2 py-1 shadow-sm focus:ring focus:ring-indigo-200 focus:outline-none">
                        </td>
                        <td class="p-4 text-right font-semibold text-indigo-600">
                            @{{ formatCurrency(item.price.price * item.trips_count) }}
                        </td>
                    </tr>
                    <tr v-if="tableData.length === 0">
                        <td colspan="5" class="p-8 text-center text-gray-500">目前沒有設定任何單價與路線。</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- Summary Panel -->
        <div class="bg-gray-50 p-6 rounded-lg border border-gray-200 shadow-sm flex flex-wrap justify-around items-center gap-6">
            <div class="text-center">
                <div class="text-gray-500 text-sm font-medium mb-1">今日總趟數</div>
                <div class="text-3xl font-bold text-gray-800">@{{ totalTrips }}</div>
            </div>
            <div class="text-center">
                <div class="text-gray-500 text-sm font-medium mb-1">今日總金額</div>
                <div class="text-3xl font-bold text-indigo-600">@{{ formatCurrency(totalAmount) }}</div>
            </div>
        </div>

        <!-- Client Summaries -->
        <div class="mt-8" v-if="Object.keys(clientSummaries).length > 0">
            <h2 class="text-xl font-bold text-gray-800 mb-4">各客戶帳務小計</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div v-for="(amount, client) in clientSummaries" :key="client" class="bg-white p-4 rounded-lg shadow-sm border border-gray-200 flex justify-between items-center">
                    <span class="font-medium text-gray-700">@{{ client }}</span>
                    <span class="font-bold text-indigo-600">@{{ formatCurrency(amount) }}</span>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
    const { createApp, ref, computed, onMounted } = Vue;

    createApp({
        setup() {
            const loading = ref(true);
            const saving = ref(false);
            const currentDate = ref(new Date().toISOString().split('T')[0]);
            
            // [{ price: {id, client_name, destination, price}, trips_count: 0 }]
            const tableData = ref([]);

            const fetchData = async () => {
                loading.value = true;
                try {
                    const response = await fetch(`/api/trips?date=${currentDate.value}`);
                    const data = await response.json();
                    
                    // Merge prices and trips
                    tableData.value = data.prices.map(price => {
                        const trip = data.trips.find(t => t.price_id === price.id);
                        return {
                            price: price,
                            trips_count: trip ? trip.trips_count : 0
                        };
                    });
                } catch (error) {
                    console.error("Error fetching data:", error);
                    alert("載入資料失敗！");
                } finally {
                    loading.value = false;
                }
            };

            const saveData = async () => {
                saving.value = true;
                try {
                    const payload = {
                        date: currentDate.value,
                        trips: tableData.value.map(item => ({
                            price_id: item.price.id,
                            trips_count: item.trips_count
                        }))
                    };

                    const response = await fetch('/api/trips', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Accept': 'application/json'
                        },
                        body: JSON.stringify(payload)
                    });

                    if (response.ok) {
                        alert("儲存成功！");
                    } else {
                        throw new Error("API Error");
                    }
                } catch (error) {
                    console.error("Error saving data:", error);
                    alert("儲存失敗！");
                } finally {
                    saving.value = false;
                }
            };

            const totalTrips = computed(() => {
                return tableData.value.reduce((sum, item) => sum + (item.trips_count || 0), 0);
            });

            const totalAmount = computed(() => {
                return tableData.value.reduce((sum, item) => sum + ((item.trips_count || 0) * item.price.price), 0);
            });

            const clientSummaries = computed(() => {
                const summaries = {};
                tableData.value.forEach(item => {
                    if (!summaries[item.price.client_name]) {
                        summaries[item.price.client_name] = 0;
                    }
                    summaries[item.price.client_name] += (item.trips_count || 0) * item.price.price;
                });
                // Only show clients that have > 0 amount or you can show all. Let's show all for clarity, 
                // but filter out those with 0 to keep it clean.
                const filtered = {};
                for (const client in summaries) {
                    if (summaries[client] > 0) {
                        filtered[client] = summaries[client];
                    }
                }
                return filtered;
            });

            const formatCurrency = (value) => {
                return new Intl.NumberFormat('zh-TW', { style: 'currency', currency: 'TWD', minimumFractionDigits: 0 }).format(value);
            };

            onMounted(() => {
                fetchData();
            });

            return {
                loading,
                saving,
                currentDate,
                tableData,
                fetchData,
                saveData,
                totalTrips,
                totalAmount,
                clientSummaries,
                formatCurrency
            };
        }
    }).mount('#app');
</script>

</body>
</html>
