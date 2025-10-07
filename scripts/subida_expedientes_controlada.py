import os
import requests
import time
from pathlib import Path

# --- Configuración ---
BASE_URL = "http://127.0.0.1:8000"
INGESTA_URL = f"{BASE_URL}/ingesta/archivos"
EXPEDIENTES_DIR = r"c:\Users\Roger Calderon\Downloads\expedientes_50_txt_unicos_largos"

# Token JWT - PEGA TU TOKEN AQUÍ
JWT_TOKEN = ""  # Pega tu token entre las comillas

# Configuración para evitar saturación
BATCH_SIZE = 3  # Procesar solo 3 archivos por lote
BATCH_DELAY = 10  # Esperar 10 segundos entre lotes
FILE_DELAY = 5   # Esperar 5 segundos entre archivos individuales

# Headers con autorización
HEADERS = {
    "Authorization": f"Bearer {JWT_TOKEN}"
} if JWT_TOKEN else {}

def extraer_numero_expediente(nombre_archivo):
    """Extrae el número de expediente del nombre del archivo."""
    sin_extension = Path(nombre_archivo).stem
    numero_expediente = sin_extension.replace("_", "-")
    return numero_expediente

def verificar_proceso_completado(process_id, max_intentos=12):
    """
    Verifica si un proceso ha completado consultando su estado.
    Espera hasta 1 minuto (12 intentos x 5 segundos) por proceso.
    """
    for intento in range(max_intentos):
        try:
            response = requests.get(f"{BASE_URL}/ingesta/status/{process_id}", timeout=10)
            if response.status_code == 200:
                status_data = response.json()
                status = status_data.get("status", "unknown")
                
                if status in ["completed", "failed", "cancelled"]:
                    return status, status_data.get("message", "")
                
                # Si aún está procesando, esperar
                print(f"      Estado: {status} - {status_data.get('message', '')[:50]}...")
                time.sleep(5)
            else:
                print(f"      ⚠️ No se pudo consultar estado (HTTP {response.status_code})")
                time.sleep(5)
        except Exception as e:
            print(f"      ⚠️ Error consultando estado: {str(e)[:50]}...")
            time.sleep(5)
    
    return "timeout", "Tiempo límite agotado esperando completar"

def subir_archivo_con_seguimiento(ruta_archivo, numero_expediente):
    """Sube un archivo y espera a que complete el procesamiento."""
    nombre_archivo = os.path.basename(ruta_archivo)
    
    print(f"📄 Subiendo: {nombre_archivo}")
    print(f"   Expediente: {numero_expediente}")
    
    try:
        # Subir archivo
        with open(ruta_archivo, 'rb') as archivo:
            files = {'files': (nombre_archivo, archivo, 'text/plain')}
            data = {'CT_Num_expediente': numero_expediente}
            
            response = requests.post(INGESTA_URL, headers=HEADERS, data=data, files=files, timeout=30)
            
            if response.status_code == 200:
                resultado = response.json()
                print(f"   ✅ Subida exitosa: {resultado.get('message', '')}")
                
                # Obtener ID de proceso para seguimiento
                process_ids = resultado.get('file_process_ids', [])
                if process_ids:
                    process_id = process_ids[0]
                    print(f"   🔍 Siguiendo proceso: {process_id}")
                    
                    # Esperar a que complete
                    status, message = verificar_proceso_completado(process_id)
                    
                    if status == "completed":
                        print(f"   🎉 PROCESADO EXITOSAMENTE")
                        return True
                    elif status == "failed":
                        print(f"   ❌ PROCESAMIENTO FALLÓ: {message}")
                        return False
                    else:
                        print(f"   ⏰ TIMEOUT O ESTADO DESCONOCIDO: {status}")
                        return False
                else:
                    print(f"   ⚠️ No se obtuvo ID de proceso, asumiendo éxito")
                    return True
            else:
                print(f"   ❌ ERROR HTTP {response.status_code}: {response.text[:100]}...")
                return False
                
    except Exception as e:
        print(f"   💥 ERROR: {str(e)}")
        return False

def main():
    """Función principal con procesamiento por lotes."""
    print("🚀 Iniciando subida masiva con control de concurrencia...")
    print(f"📁 Directorio: {EXPEDIENTES_DIR}")
    print(f"🌐 Endpoint: {INGESTA_URL}")
    print(f"� Token configurado: {'✅ Sí' if JWT_TOKEN else '❌ No (requerido)'}")
    print(f"�📦 Tamaño de lote: {BATCH_SIZE} archivos")
    print(f"⏰ Pausa entre lotes: {BATCH_DELAY} segundos")
    print(f"⏱️  Pausa entre archivos: {FILE_DELAY} segundos")
    print("-" * 70)
    
    # Validar que el token esté configurado
    if not JWT_TOKEN:
        print("❌ ERROR: Debes configurar JWT_TOKEN en el script")
        print("   1. Inicia sesión en el frontend")
        print("   2. Abre DevTools (F12) > Console")
        print("   3. Ejecuta: sessionStorage.getItem('token')")
        print("   4. Copia el token y pégalo en la variable JWT_TOKEN")
        return
    
    if not os.path.isdir(EXPEDIENTES_DIR):
        print(f"❌ ERROR: El directorio no existe: {EXPEDIENTES_DIR}")
        return
    
    # Obtener archivos .txt
    archivos_txt = [
        f for f in os.listdir(EXPEDIENTES_DIR) 
        if f.endswith('.txt') and os.path.isfile(os.path.join(EXPEDIENTES_DIR, f))
    ]
    
    if not archivos_txt:
        print(f"❌ No se encontraron archivos .txt")
        return
    
    print(f"📊 Encontrados {len(archivos_txt)} archivos .txt")
    print("-" * 70)
    
    # Procesar en lotes
    exitosos = 0
    fallidos = 0
    tiempo_inicio = time.time()
    
    for i in range(0, len(archivos_txt), BATCH_SIZE):
        # Obtener lote actual
        lote = archivos_txt[i:i+BATCH_SIZE]
        numero_lote = (i // BATCH_SIZE) + 1
        total_lotes = (len(archivos_txt) + BATCH_SIZE - 1) // BATCH_SIZE
        
        print(f"\n🔄 LOTE {numero_lote}/{total_lotes} - Procesando {len(lote)} archivos:")
        print("-" * 50)
        
        # Procesar archivos del lote secuencialmente
        for j, nombre_archivo in enumerate(lote, 1):
            archivo_global = i + j
            print(f"\n[{archivo_global}/{len(archivos_txt)}] ", end="")
            
            numero_expediente = extraer_numero_expediente(nombre_archivo)
            ruta_archivo = os.path.join(EXPEDIENTES_DIR, nombre_archivo)
            
            if subir_archivo_con_seguimiento(ruta_archivo, numero_expediente):
                exitosos += 1
            else:
                fallidos += 1
            
            # Pausa entre archivos (excepto el último del lote)
            if j < len(lote):
                print(f"   ⏳ Esperando {FILE_DELAY} segundos...")
                time.sleep(FILE_DELAY)
        
        # Pausa entre lotes (excepto el último)
        if numero_lote < total_lotes:
            print(f"\n🛑 Fin del lote {numero_lote}. Esperando {BATCH_DELAY} segundos antes del siguiente lote...")
            time.sleep(BATCH_DELAY)
    
    # Estadísticas finales
    tiempo_total = time.time() - tiempo_inicio
    print("\n" + "=" * 70)
    print("📈 RESUMEN FINAL:")
    print(f"   ✅ Exitosos: {exitosos}")
    print(f"   ❌ Fallidos: {fallidos}")
    print(f"   📁 Total procesados: {exitosos + fallidos}")
    print(f"   ⏱️  Tiempo total: {tiempo_total:.2f} segundos ({tiempo_total/60:.1f} minutos)")
    if exitosos + fallidos > 0:
        print(f"   📊 Promedio por archivo: {tiempo_total/(exitosos + fallidos):.2f} segundos")
    print("=" * 70)
    
    if fallidos > 0:
        print(f"⚠️  ATENCIÓN: {fallidos} archivos fallaron")
    else:
        print("🎉 ¡Todos los archivos se procesaron exitosamente!")

if __name__ == "__main__":
    main()