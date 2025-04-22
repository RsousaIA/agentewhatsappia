#!/bin/bash

# Configuração do ambiente de produção
echo "Configurando ambiente de produção..."

# 1. Instalar dependências
echo "Instalando dependências..."
npm install
pip install -r requirements.txt

# 2. Configurar variáveis de ambiente
echo "Configurando variáveis de ambiente..."
cp .env.example .env.production

# 3. Configurar SSL
echo "Configurando SSL..."
mkdir -p ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/private.key \
  -out ssl/certificate.crt \
  -subj "/C=BR/ST=Sao_Paulo/L=Sao_Paulo/O=AgenteSuporte/CN=seusistema.com"

# 4. Configurar domínios
echo "Configurando domínios..."
echo "seusistema.com" > domains.txt
echo "api.seusistema.com" >> domains.txt

# 5. Configurar Nginx
echo "Configurando Nginx..."
cat > nginx.conf << EOL
server {
    listen 80;
    server_name seusistema.com;
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl;
    server_name seusistema.com;

    ssl_certificate /path/to/ssl/certificate.crt;
    ssl_certificate_key /path/to/ssl/private.key;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }
}

server {
    listen 443 ssl;
    server_name api.seusistema.com;

    ssl_certificate /path/to/ssl/certificate.crt;
    ssl_certificate_key /path/to/ssl/private.key;

    location / {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }
}
EOL

# 6. Configurar PM2 para gerenciamento de processos
echo "Configurando PM2..."
npm install -g pm2
pm2 start whatsapp_server.js --name "whatsapp-server"
pm2 start main.py --name "python-backend"
pm2 start frontend/package.json --name "frontend"

# 7. Configurar backup automático
echo "Configurando backup automático..."
mkdir -p backup
cat > backup.sh << EOL
#!/bin/bash
timestamp=\$(date +%Y%m%d_%H%M%S)
mongodump --out backup/\$timestamp
EOL
chmod +x backup.sh

# 8. Configurar monitoramento
echo "Configurando monitoramento..."
npm install -g pm2-logrotate
pm2 install pm2-logrotate
pm2 set pm2-logrotate:max_size 10M
pm2 set pm2-logrotate:retain 7

# 9. Testar integração
echo "Testando integração..."
node test_whatsapp_firebase.js
python -m pytest tests/

echo "Configuração concluída!" 