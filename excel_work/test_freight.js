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

    let regionA = 1;
    if (r.match(/林口/) || r.match(/龜山/) || r.match(/桃園/) || r.match(/南崁/) || r.match(/大園/) || r.match(/蘆竹/)) regionA = 1;
    else if (r.match(/中壢/) || r.match(/平鎮/) || r.match(/楊梅/) || r.match(/新屋/) || r.match(/觀音/) || r.match(/新豐/)) regionA = '2a';
    else if (r.match(/新埔/) || r.match(/竹北/) || r.match(/湖口/) || r.match(/新竹/) || r.match(/竹東/)) regionA = '2b';
    else if (r.match(/頭份/) || r.match(/竹南/) || r.match(/苗栗/)) regionA = '2c';
    else if (r.match(/台中/) || r.match(/豐原/) || r.match(/大甲/)) regionA = '2d';
    else if (r.match(/彰化/) || r.match(/南投/)) regionA = '2e';
    else if (r.match(/基隆/) || r.match(/汐止/) || r.match(/南港/) || r.match(/內湖/) || r.match(/五堵/) || r.match(/深坑/)) regionA = 3;
    else if (r.match(/台北/) || r.match(/新店/) || r.match(/中和/) || r.match(/永和/) || r.match(/板橋/) || r.match(/三重/) || r.match(/新莊/) || r.match(/樹林/)) regionA = 4;
    else if (r.match(/三峽/) || r.match(/鶯歌/) || r.match(/土城/) || r.match(/五股/) || r.match(/泰山/) || r.match(/林口/)) regionA = 5;

    if (vehicle) {
        const matrixB_FTL = {
            1: { '3.49': 1600, '6.8': 2000, '8.8': 3000, '17': 4500 },
            '2a': { '3.49': 1700, '6.8': 2200, '8.8': 3000, '17': 4500 },
            '2b': { '3.49': 1700, '6.8': 2200, '8.8': 3000, '17': 4800 },
            '2c': { '3.49': 1800, '6.8': 2400, '8.8': 3500, '17': 4800 },
            '2d': { '3.49': 2000, '6.8': 2800, '8.8': 3600, '17': 5000 },
            '2e': { '3.49': 2400, '6.8': 3200, '8.8': 3800, '17': 5200 },
            3: { '3.49': 1500, '6.8': 2000, '8.8': 2500, '17': 4000 },
            4: { '3.49': 1600, '6.8': 2100, '8.8': 2800, '17': 4200 },
            5: { '3.49': 1700, '6.8': 2200, '8.8': 3000, '17': 4500 }
        };
        return matrixB_FTL[regionA]?.[vehicle] || 0;
    }
    return -1;
};

console.log(calculateFreight(0, "楊梅 共10批17噸車", "206"));
