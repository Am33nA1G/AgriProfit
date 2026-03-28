# SSL Certificates

This directory is mounted into the nginx container at `/etc/nginx/ssl/`.
It is intentionally empty in git — **never commit real certs here**.

## Option A — AWS ALB + ACM (recommended for AWS)

If you put an Application Load Balancer in front of this stack:
- Terminate TLS at the ALB using an ACM certificate (free, auto-renews)
- Remove the `ssl` directives from `nginx/conf.d/default.conf`
- Change both `listen 443 ssl;` blocks to `listen 80;`
- The ALB forwards plain HTTP to nginx on port 80

This is simpler and more reliable than managing certs yourself.

## Option B — Let's Encrypt / certbot (bare EC2)

On the EC2 instance (before starting docker-compose):

```bash
# Install certbot
sudo apt install certbot

# Issue certificate (stop nginx first so port 80 is free)
sudo certbot certonly --standalone \
  -d yourdomain.com \
  -d www.yourdomain.com \
  -d api.yourdomain.com

# Certs land in /etc/letsencrypt/live/yourdomain.com/
# Copy or symlink into ./nginx/ssl/yourdomain.com/
sudo mkdir -p ./nginx/ssl/yourdomain.com
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ./nginx/ssl/yourdomain.com/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem   ./nginx/ssl/yourdomain.com/
```

Set up auto-renewal (runs twice a day, only renews when <30 days remain):
```bash
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

After renewal, reload nginx:
```bash
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

## Expected directory layout

```
nginx/ssl/
└── yourdomain.com/
    ├── fullchain.pem   ← cert + intermediates
    └── privkey.pem     ← private key (chmod 600)
```
