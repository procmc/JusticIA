import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.vectorstore.vectorstore import get_vectorstore
from app.routes import ingesta, health, llm, usuarios, archivos, email
from app.db import database

# Crear app sin lifespan primero
app = FastAPI(title="JusticIA API")

# Inicializar vectorstore en el evento startup
@app.on_event("startup")
async def startup_event():
    """Inicializar recursos al arranque"""
    try:
        await get_vectorstore()
        print("Milvus inicializado correctamente")
    except Exception as e:
        print(f"Error inicializando Milvus: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Limpiar recursos al apagado"""
    print("Aplicación cerrando...")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingesta.router, prefix="/ingesta", tags=["ingesta"])
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(llm.router, prefix="/llm", tags=["llm"])
app.include_router(usuarios.router, prefix="/usuarios", tags=["usuarios"])
app.include_router(archivos.router, prefix="/archivos", tags=["archivos"])
app.include_router(email.router, prefix="/email", tags=["email"])

@app.get("/")
async def root():
    return {"message": "JusticIA API está funcionando", "version": "1.0.0"}
