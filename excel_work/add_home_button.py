import sys

files = ['206', '225', '276', '444', '639']
for client in files:
    filepath = f'resources/views/client_{client}.blade.php'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    old_html = """        <div>
            <button @click="clearAllData" class="bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded shadow transition-colors focus:outline-none focus:ring-0">"""
            
    new_html = """        <div class="flex gap-2">
            <a href="/" class="bg-gray-500 hover:bg-gray-600 text-white font-bold py-2 px-4 rounded shadow transition-colors focus:outline-none focus:ring-0 flex items-center justify-center">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                </svg>
                回首頁
            </a>
            <button @click="clearAllData" class="bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded shadow transition-colors focus:outline-none focus:ring-0">"""
            
    if old_html in content:
        content = content.replace(old_html, new_html)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Added home button to {filepath}")
    else:
        print(f"Could not find target HTML in {filepath}")
