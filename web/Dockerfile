FROM node:22-slim AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.sh /docker-entrypoint.d/40-caltrack-config.sh
RUN chmod +x /docker-entrypoint.d/40-caltrack-config.sh \
    && chown -R nginx:nginx /usr/share/nginx/html /etc/nginx/conf.d/default.conf \
    && chown nginx:nginx /docker-entrypoint.d/40-caltrack-config.sh
USER nginx
EXPOSE 80
