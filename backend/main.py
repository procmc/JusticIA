import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.vectorstore.vectorstore import get_vectorstore
from app.routes import ingesta, consulta, health, llm

@asynccontextmanager
async def lifespan(app: FastAPI):
	await get_vectorstore()
	yield

app = FastAPI(title="Demo Ingesta & Consulta - JusticIA", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite cualquier origen. Puedes poner ["http://localhost"] si quieres restringir.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingesta.router)
app.include_router(consulta.router)
app.include_router(health.router)
app.include_router(llm.router)
