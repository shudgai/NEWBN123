const r = '17噸車*2 + 6.8噸x 3 + 3.49噸 * 2';
let vehicles = [];
const vehicleRegex = /(3\.49|6\.8|8\.8|10\.5|15|17)噸(?:車)?\s*(?:[*xX]\s*(\d+))?/g;
let match;
while ((match = vehicleRegex.exec(r)) !== null) {
    let count = match[2] ? parseInt(match[2], 10) : 1;
    for (let i = 0; i < count; i++) {
        vehicles.push(match[1]);
    }
}
console.log(vehicles);
