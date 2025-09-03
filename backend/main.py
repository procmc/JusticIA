import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.vectorstore.vectorstore import get_vectorstore
from app.routes import ingesta, consulta, health, llm, usuarios_simple, archivos
from app.db import database

@asynccontextmanager
async def lifespan(app: FastAPI):
	await get_vectorstore()
	yield

app = FastAPI(title="JusticIA API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingesta.router, prefix="/ingesta", tags=["ingesta"])
app.include_router(consulta.router, prefix="/consulta", tags=["consulta"])
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(llm.router, prefix="/llm", tags=["llm"])
app.include_router(usuarios_simple.router)
app.include_router(archivos.router, prefix="/archivos", tags=["archivos"])

@app.get("/")
async def root():
    return {"message": "JusticIA API está funcionando", "version": "1.0.0"}
