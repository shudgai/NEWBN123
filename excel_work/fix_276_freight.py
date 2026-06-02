import sys

filepath = 'resources/views/client_276.blade.php'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# We need to replace everything from "const calculateFreight = (weight, remark) => {" to its closing brace "};"
# I will use a simple regex or find/rfind.
import re

pattern = re.compile(r'            const calculateFreight = \(weight, remark\) => \{.*?\n            \};', re.DOTALL)

new_func = """            const calculateFreight = (weight, remark) => {
                const r = remark || '';

                // Special fees check first
                if (r.match(/棧板回收/)) return 800;
                if (r.match(/搬運工資|搬運費/)) return 800;
                if (r.match(/人力/)) return 1500;

                // Vehicle check
                let vehicle = null;
                if (r.match(/3\.49噸/)) vehicle = '3.49';
                else if (r.match(/6\.8噸/)) vehicle = '6.8';
                else if (r.match(/8\.8噸/)) vehicle = '8.8';
                else if (r.match(/10\.5噸/)) vehicle = '10.5';
                else if (r.match(/15噸/)) vehicle = '15';
                else if (r.match(/17噸/)) vehicle = '17';

                // Determine Region
                // Region 1: Taipei city (Base)
                // Region 2: Suburbs (Base + surcharge)
                // Region 3: 中壢、內壢、桃園、大園、林口、龜山
                // Region 4: 新屋、八德、三峽、鶯歌、觀音、平鎮、龍潭
                // Region 5: 楊梅 (Taipei + 550) => maps to 2d basically
                // Region 6: 新竹、湖口、基隆 (Only specific vehicles)
                // Region 7: 冷泉港

                let region = 1; 
                let surcharge = 0;
                let isColdSpring = false;

                if (r.match(/冷泉港/)) {
                    isColdSpring = true;
                    region = 7;
                } else if (r.match(/新竹|湖口|基隆/)) {
                    region = 6;
                } else if (r.match(/新屋|八德|三峽|鶯歌|觀音|平鎮|龍潭/)) {
                    region = 4;
                } else if (r.match(/中壢|內壢|桃園|大園|林口|龜山/)) {
                    region = 3;
                } else if (r.match(/淡水|八里/)) {
                    region = 2; surcharge = 660;
                } else if (r.match(/汐止|土城|楊梅/)) {
                    region = 2; surcharge = 550;
                } else if (r.match(/新莊|樹林|五股|泰山/)) {
                    region = 2; surcharge = 440;
                } else if (r.match(/中和|永和|三重|南港|板橋|石牌|北投|木柵|新店|蘆洲/)) {
                    region = 2; surcharge = 330;
                } else if (r.match(/景美|天母|士林|大直|內湖|松山|萬華|社子/)) {
                    region = 2; surcharge = 220;
                }

                if (vehicle) {
                    if (region === 1 || region === 3 || region === 4 || region === 2) {
                        // Region 1,2,3,4 cars
                        // We map them according to the rules. If not specific, we use Taipei standard
                        if (region === 2 && surcharge === 660) {
                            if (vehicle === '3.49') return 2310;
                            if (vehicle === '6.8') return 2520;
                        } else if (region === 2 && surcharge === 550) {
                            if (vehicle === '3.49') return 2100;
                            if (vehicle === '6.8') return 2520;
                            if (vehicle === '8.8') return 3360;
                            if (vehicle === '10.5') return 4200;
                            if (vehicle === '15') return 4725;
                            if (vehicle === '17') return 5250;
                        } else if (region === 2 && surcharge === 440) {
                            if (vehicle === '3.49') return 2100;
                            if (vehicle === '6.8') return 2310;
                            if (vehicle === '8.8') return 3150;
                            if (vehicle === '15') return 4410;
                            if (vehicle === '17') return 4725;
                        } else if (region === 2 && surcharge === 330) {
                            if (vehicle === '3.49') return 2100;
                            if (vehicle === '6.8') return 2310;
                            if (vehicle === '8.8') return 3150;
                            if (vehicle === '10.5') return 4200;
                            if (vehicle === '15') return 4725;
                        } else if (region === 2 && surcharge === 220) {
                            if (vehicle === '3.49') return 1995;
                            if (vehicle === '6.8') return 2205;
                        } else if (region === 3) {
                            if (vehicle === '3.49') return 1890;
                            if (vehicle === '6.8') return 2100;
                            if (vehicle === '8.8') return 2940;
                        } else if (region === 4) {
                            if (vehicle === '3.49') return 2100;
                            if (vehicle === '6.8') return 2310;
                            if (vehicle === '15') return 4200;
                        }
                        
                        // Default fallback to Region 1 (Taipei city)
                        if (vehicle === '3.49') return 1890;
                        if (vehicle === '6.8') return 2100;
                        if (vehicle === '8.8') return 3675;
                    } else if (region === 6) {
                        if (vehicle === '3.49') return 2520;
                        if (vehicle === '6.8') return 3255;
                        if (vehicle === '8.8') return 3570;
                    }
                    
                    return -1; // Specific vehicle not defined, leave empty
                }

                if (!weight) return 0;
                const w = parseFloat(weight);
                if (isNaN(w) || w <= 0) return 0;

                // Scattered goods
                let amount = 0;
                let addInsurance = true;

                if (isColdSpring) {
                    addInsurance = false;
                    if (w <= 20) amount = 605;
                    else if (w <= 50) amount = 754;
                    else if (w <= 100) amount = 853;
                    else if (w <= 200) amount = 963;
                    else if (w <= 300) amount = 1073;
                    else amount = Math.round(1073 + (w - 300) * 0.88);
                } else if (region === 6) {
                    return -1; // 另計
                } else if (region === 3) {
                    if (w <= 100) amount = 660;
                    else if (w <= 300) amount = 990;
                    else if (w <= 500) amount = 1100;
                    else if (w <= 800) amount = 1320;
                    else return -1;
                } else if (region === 4) {
                    if (w <= 100) amount = 770;
                    else if (w <= 300) amount = 1100;
                    else if (w <= 500) amount = 1320;
                    else if (w <= 800) amount = 1540;
                    else return -1;
                } else {
                    // Region 1 & 2
                    if (w <= 50) amount = 253;
                    else if (w <= 100) amount = 440;
                    else if (w <= 200) amount = 550;
                    else if (w <= 300) amount = 660;
                    else if (w <= 400) amount = 880;
                    else if (w <= 500) amount = 1100;
                    else if (w <= 700) amount = 1320;
                    else if (w <= 800) amount = 1430;
                    else return -1;

                    if (region === 2) {
                        amount += surcharge;
                    }
                }

                if (addInsurance && amount > 0) {
                    amount += 20; // 基本備註：每筆散貨貨物另加 $20 保險費
                }

                return amount;
            };"""

if re.search(pattern, content):
    content = re.sub(pattern, new_func, content)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Replaced calculateFreight in 276.")
else:
    print("Pattern not found!")
