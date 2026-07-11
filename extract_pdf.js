const fs = require('fs');
const pdf = require('pdf-parse');

let dataBuffer = fs.readFileSync('temp_oferta.xyz');

pdf(dataBuffer).then(function(data) {
    console.log(data.text);
}).catch(err => {
    console.error(err);
});
