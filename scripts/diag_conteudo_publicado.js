const https = require('https');
function buscar(url) {
  return new Promise((resolve, reject) => {
    const cab = {};
    if (process.env.PREVIA_BASIC_AUTH) cab['Authorization'] = 'Basic ' + Buffer.from(process.env.PREVIA_BASIC_AUTH).toString('base64');
    https.get(url, { headers: cab }, res => {
      let dados = '';
      res.on('data', c => dados += c);
      res.on('end', () => resolve({ status: res.statusCode, corpo: dados }));
    }).on('error', reject);
  });
}
(async () => {
  for (const pagina of ['', 'saude.html']) {
    const r = await buscar('https://monitorelnino.com.br/' + pagina);
    console.log('=== ' + (pagina || 'index.html') + ' · status ' + r.status + ' · ' + r.corpo.length + ' bytes ===');
    console.log('tem "contadorTempo":', r.corpo.includes('contadorTempo'));
    console.log('tem "Semana" + "primeiro boletim":', /Semana\s*<strong[^>]*>\d+/.test(r.corpo) && r.corpo.includes('primeiro boletim'));
    console.log('tem "Monitor de Antecipação":', r.corpo.includes('Monitor de Antecipação'));
    console.log('tem "Medida de Antecipação" (deveria ser 0):', r.corpo.includes('Medida de Antecipação'));
    console.log('tem "MARÉ Legal" no nav:', r.corpo.includes('MARÉ Legal'));
    console.log('trecho ao redor de "contadorTempo":', r.corpo.includes('contadorTempo') ? r.corpo.slice(r.corpo.indexOf('contadorTempo') - 60, r.corpo.indexOf('contadorTempo') + 200) : '(não encontrado)');
    console.log('');
  }
})();
