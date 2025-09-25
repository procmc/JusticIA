#!/usr/bin/env node

/**
 * Script para verificar el estado de los servicios de JusticIA
 */

const http = require('http');
const https = require('https');

// Función para hacer requests HTTP simples
function checkService(url, name) {
  return new Promise((resolve) => {
    const client = url.startsWith('https') ? https : http;
    const request = client.get(url, (res) => {
      resolve({
        name,
        url,
        status: res.statusCode,
        success: res.statusCode >= 200 && res.statusCode < 300,
        message: `✅ ${name} respondiendo (${res.statusCode})`
      });
    });

    request.on('error', (err) => {
      resolve({
        name,
        url,
        status: 0,
        success: false,
        message: `❌ ${name} no responde: ${err.message}`
      });
    });

    request.setTimeout(5000, () => {
      request.destroy();
      resolve({
        name,
        url,
        status: 0,
        success: false,
        message: `⏱️ ${name} timeout (5s)`
      });
    });
  });
}

async function checkAllServices() {
  console.log('🔍 Verificando estado de servicios JusticIA...\n');

  const services = [
    { url: 'http://localhost:3000', name: 'Frontend Next.js' },
    { url: 'http://localhost:8000', name: 'Backend FastAPI' },
    { url: 'http://localhost:8000/docs', name: 'API Docs (Swagger)' },
    { url: 'http://localhost:11434/api/tags', name: 'Ollama' },
  ];

  const results = await Promise.all(
    services.map(service => checkService(service.url, service.name))
  );

  results.forEach(result => {
    console.log(result.message);
  });

  const failedServices = results.filter(r => !r.success);
  
  if (failedServices.length === 0) {
    console.log('\n🎉 ¡Todos los servicios están funcionando correctamente!');
  } else {
    console.log('\n⚠️  Servicios con problemas:');
    failedServices.forEach(service => {
      console.log(`   - ${service.name}: ${service.url}`);
    });
    
    console.log('\n📋 Para solucionar:');
    if (failedServices.some(s => s.name.includes('Backend'))) {
      console.log('   • Backend: cd backend && python main.py');
    }
    if (failedServices.some(s => s.name.includes('Ollama'))) {
      console.log('   • Ollama: ollama serve');
    }
    if (failedServices.some(s => s.name.includes('Frontend'))) {
      console.log('   • Frontend: cd frontend && npm run dev');
    }
  }
}

checkAllServices().catch(console.error);