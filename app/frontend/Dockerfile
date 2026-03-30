FROM node:24-bookworm-slim AS build

WORKDIR /workspace/app/frontend

COPY app/frontend/package.json app/frontend/package-lock.json ./
RUN npm ci

COPY app/frontend ./
RUN npm run build

FROM nginx:1.27-alpine AS runtime

COPY app/frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /workspace/app/frontend/dist /usr/share/nginx/html

EXPOSE 80
