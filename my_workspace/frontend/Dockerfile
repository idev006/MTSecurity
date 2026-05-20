# Stage 1: Build — compile Vue SPA
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency manifests first for layer caching
COPY package.json package-lock.json ./

RUN npm ci

# Copy the rest of the source and build
COPY . .

RUN npm run build


# Stage 2: Lean nginx runtime
FROM nginx:1.27-alpine AS runtime

# Remove the default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Write a production nginx config inline
RUN cat > /etc/nginx/conf.d/default.conf <<'EOF'
server {
    listen 80;
    server_tokens off;

    root /usr/share/nginx/html;
    index index.html;

    # Enable gzip compression
    gzip on;
    gzip_vary on;
    gzip_types
        application/json
        text/css
        application/javascript
        text/plain;

    # Immutable cache for hashed assets
    location /assets/ {
        add_header Cache-Control "max-age=31536000, immutable";
        try_files $uri =404;
    }

    # Vue router SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }
}
EOF

# Copy built dist from the builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
