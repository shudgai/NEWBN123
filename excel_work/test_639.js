const r = "三重";
let regionA = 1;
if (r.match(/三重|五股|泰山|新莊|蘆洲|板橋|樹林|中和|永和/)) { regionA = '2a'; }
else if (r.match(/南港|內湖|大直|天母|景美/)) { regionA = '2b'; }
else if (r.match(/新店|汐止|深坑|木柵|八里|土城|鶯歌|三峽|北投|社子/)) { regionA = '2c'; }
else if (r.match(/大溪|龍潭|新豐|湖口|七堵|瑞芳/)) { regionA = '2d'; }
else if (r.match(/新竹|基隆|淡水/)) { regionA = '2e'; }
else if (r.match(/蘆竹|大園/)) { regionA = 3; }
else if (r.match(/中壢|林口|龜山|桃園/)) { regionA = 4; }
else if (r.match(/新屋|八德|觀音|平鎮|楊梅/)) { regionA = 5; }

let w = 278;
let basePrice = 0;
if (w <= 20) basePrice = 330;
else if (w <= 50) basePrice = 440;
else if (w <= 100) basePrice = 660;
else if (w <= 200) basePrice = 770;
else if (w <= 300) basePrice = 880;

if (typeof regionA === 'string' && regionA.startsWith('2')) {
    if (regionA === '2a') basePrice += 220;
    console.log(basePrice);
}
