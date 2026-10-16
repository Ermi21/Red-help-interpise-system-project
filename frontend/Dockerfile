FROM nginx:alpine

# Copy built frontend assets to both root and /Redcloud subpath
COPY dist /usr/share/nginx/html
COPY dist /usr/share/nginx/html/Redcloud
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
