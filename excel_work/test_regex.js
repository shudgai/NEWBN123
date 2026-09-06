const r = '共十九批6.8噸+15噸車';
let vehicles = [];
const vehicleRegex = /(3\.49|6\.8|8\.8|10\.5|15|17)噸/g;
let match;
while ((match = vehicleRegex.exec(r)) !== null) {
    vehicles.push(match[1]);
}
console.log('Vehicles:', vehicles);
