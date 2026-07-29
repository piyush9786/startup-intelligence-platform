FROM node:22-alpine

WORKDIR /app
RUN chown node:node /app

# Keep installed dependencies readable and writable by the non-root Node user.
COPY --chown=node:node package.json package-lock.json ./
USER node
RUN npm ci --no-audit --no-fund

COPY --chown=node:node . .

ENV PATH=/app/node_modules/.bin:$PATH
EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
