FROM node:22-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

RUN adduser -D appuser
USER appuser

EXPOSE 3000

CMD ["npm", "run", "dev"]
