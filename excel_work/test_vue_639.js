const calculateFreight = (weight, remark) => {
    let amt = _calculateFreight(weight, remark);
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

const _calculateFreight = (weight, remark) => {
    const r = (remark || '').replace(/竹北/g, '新竹');

    let vehicles = [];
    const vehicleRegex = /(3\.49|6\.8|8\.8|10\.5|15|17)噸(?:車)?\s*(?:[*xX]\s*(\d+))?/g;
    let match;
    while ((match = vehicleRegex.exec(r)) !== null) {
        let count = match[2] ? parseInt(match[2], 10) : 1;
        for (let i = 0; i < count; i++) {
            vehicles.push(match[1]);
        }
    }

    let regionA = 1;
    if (r.match(/三重|五股|泰山|新莊|蘆洲|板橋|樹林|中和|永和/)) { regionA = '2a'; }
    else if (r.match(/南港|內湖|大直|天母|景美/)) { regionA = '2b'; }
    else if (r.match(/新店|汐止|深坑|木柵|八里|土城|鶯歌|三峽|北投|社子/)) { regionA = '2c'; }
    else if (r.match(/大溪|龍潭|新豐|湖口|七堵|瑞芳/)) { regionA = '2d'; }
    else if (r.match(/新竹|基隆|淡水/)) { regionA = '2e'; }
    else if (r.match(/蘆竹|大園/)) { regionA = 3; }
    else if (r.match(/中壢|林口|龜山|桃園/)) { regionA = 4; }
    else if (r.match(/新屋|八德|觀音|平鎮|楊梅/)) { regionA = 5; }

    if (vehicles.length > 0) {
        return 9999;
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

    if (typeof regionA === 'string' && regionA.startsWith('2')) {
        if (regionA === '2a') basePrice += 220;
        if (regionA === '2b') basePrice += 330;
        if (regionA === '2c') basePrice += 440;
        if (regionA === '2d') basePrice += 550;
        if (regionA === '2e') basePrice += 660;
        return basePrice;
    } else if (regionA === 3) {
        return basePrice;
    }

    return basePrice;
};

const loc = "台北";
const remark = "三重";
const textToCheck = (loc || '') + ' ' + (remark || '');
console.log(calculateFreight(278, textToCheck));
