from celery_app import celery_app

@celery_app.task
def procesar_ingesta(datos):
    # Aquí va la lógica de ingesta
    print(f"Procesando ingesta: {datos}")
    return "ok"

@celery_app.task
def guardar_historial(usuario_id, mensaje):
    # Aquí va la lógica para guardar historial de chat
    print(f"Guardando mensaje para usuario {usuario_id}: {mensaje}")
    return "guardado"
