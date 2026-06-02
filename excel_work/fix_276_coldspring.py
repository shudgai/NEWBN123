import sys
import re

filepath = 'resources/views/client_276.blade.php'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_logic = """                let region = 1; 
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
                }"""

new_logic = """                let region = 1; 
                let surcharge = 0;
                let isColdSpring = false;

                if (r.match(/冷泉港/)) {
                    isColdSpring = true;
                    region = 2; surcharge = 550; // Cold spring is treated as Xizhi for specific vehicles
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
                }"""

content = content.replace(old_logic, new_logic)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated 276 coldspring logic")
