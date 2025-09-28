# Dockerfile para el frontend
FROM node:18-slim

WORKDIR /app


# Copiar solo los archivos necesarios al contenedor
COPY package.json package-lock.json* ./
COPY . .

RUN npm install

EXPOSE 3000

CMD ["npm", "run", "dev"]
