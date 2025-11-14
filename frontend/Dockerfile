# Dockerfile para Frontend Next.js - Desarrollo
FROM node:20-alpine

WORKDIR /app

# Copiar archivos de dependencias
COPY package*.json ./

# Instalar dependencias
RUN npm install

# Copiar código fuente
COPY . .

EXPOSE 3000

# Modo desarrollo con hot-reload
CMD ["npm", "run", "dev"]
