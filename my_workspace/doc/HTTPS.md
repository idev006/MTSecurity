# MTSecurity — HTTPS Setup Guide

> **สรุปสั้น:** ใช้ **Cloudflare Tunnel** — ง่ายที่สุด, ฟรี, ไม่ต้องจัดการ cert เอง  
> สำหรับ LAN-only ใช้ HTTP ได้เลย หรือใช้ mkcert ถ้าต้องการ HTTPS ใน LAN

---

## ทำไมต้องใช้ HTTPS?

| ข้อมูล | ความเสี่ยงถ้าใช้ HTTP |
|--------|----------------------|
| JWT Token (Authorization header) | ดักอ่านได้ใน LAN |
| Username / Password (POST /auth/login) | ดักอ่านได้ใน LAN |
| MJPEG video stream | ดักดูกล้องได้ |
| WebSocket events | ดักอ่าน alert ได้ |

---

## Scenario 1 — Office LAN (HTTP — ตอนนี้)

ถ้าเครือข่ายในสำนักงานเป็น **trusted network** (router ส่วนตัว, ไม่มีคนนอก):  
**HTTP ใช้งานได้เลย** — ไม่จำเป็นต้องตั้งค่าเพิ่ม

```
http://192.168.x.x   ← IP ของเครื่อง server
```

ใช้ `ipconfig` หา IP ของ server แล้วแจกให้ทีม

---

## Scenario 2 — Cloudflare Tunnel (แนะนำสำหรับอนาคต)

### ข้อดี
- ✅ HTTPS อัตโนมัติ — Cloudflare ออก cert ให้ฟรี
- ✅ ไม่ต้องมี Static IP หรือเปิด port บน router
- ✅ ป้องกัน DDoS โดย Cloudflare
- ✅ เพิ่ม Cloudflare Access เพื่อ login ก่อนเข้าระบบได้
- ✅ ฟรีสำหรับ basic use

### Architecture

```
[User ภายนอก]
    │ HTTPS (Cloudflare cert)
    ▼
[Cloudflare Edge] ──tunnel──► [cloudflared บน server] ──► [nginx:80 local]
                                                                │
                                                    ┌───────────┴───────────┐
                                                    ▼                       ▼
                                            [backend:8000]          [frontend:5173]
```

### วิธีติดตั้ง Cloudflare Tunnel

#### ขั้นตอนที่ 1 — ติดตั้ง cloudflared บน Windows Server

```powershell
# ดาวน์โหลด cloudflared
# https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/

# หรือใช้ winget
winget install Cloudflare.cloudflared
```

#### ขั้นตอนที่ 2 — Login Cloudflare

```powershell
cloudflared tunnel login
# เปิด browser → เลือก domain ใน Cloudflare account
```

#### ขั้นตอนที่ 3 — สร้าง Tunnel

```powershell
cloudflared tunnel create mtsecurity

# จะได้ Tunnel ID (UUID) เก็บไว้
# Credentials file จะถูกสร้างที่ C:\Users\<you>\.cloudflared\<UUID>.json
```

#### ขั้นตอนที่ 4 — ตั้งค่า config

สร้างไฟล์ `C:\Users\<you>\.cloudflared\config.yml`:

```yaml
tunnel: <TUNNEL-UUID>
credentials-file: C:\Users\<you>\.cloudflared\<TUNNEL-UUID>.json

ingress:
  - hostname: mtsecurity.yourdomain.com
    service: http://localhost:80
  - service: http_status:404
```

#### ขั้นตอนที่ 5 — ตั้งค่า DNS

```powershell
cloudflared tunnel route dns mtsecurity mtsecurity.yourdomain.com
# สร้าง CNAME record ใน Cloudflare DNS อัตโนมัติ
```

#### ขั้นตอนที่ 6 — รัน Tunnel

```powershell
# ทดสอบ
cloudflared tunnel run mtsecurity

# ติดตั้งเป็น Windows Service (auto-start)
cloudflared service install
```

#### ขั้นตอนที่ 7 — อัปเดต backend .env

```env
# backend/.env
CORS_ORIGINS=https://mtsecurity.yourdomain.com
BASE_URL=https://mtsecurity.yourdomain.com
```

แล้ว restart backend:
```powershell
# Ctrl+C ใน terminal แล้วรัน start-all.bat ใหม่
```

### Cloudflare Access (Optional — แนะนำ)

เพิ่ม layer ป้องกันก่อนเข้าระบบ:

1. ไปที่ Cloudflare Zero Trust Dashboard → Access → Applications
2. เพิ่ม application → Self-hosted
3. ตั้ง domain: `mtsecurity.yourdomain.com`
4. เพิ่ม policy: Allow → Email → `@yourcompany.com` (หรือ IP เฉพาะ)

---

## Scenario 3 — HTTPS บน LAN ด้วย mkcert (Optional)

ใช้เมื่อต้องการ HTTPS ใน LAN โดยไม่ใช้ Cloudflare

### ติดตั้ง mkcert

```powershell
# ติดตั้ง mkcert
winget install FiloSottile.mkcert

# ติดตั้ง root CA บนเครื่อง server (ทำครั้งเดียว)
mkcert -install
```

### สร้าง Certificate

```powershell
# สร้าง cert สำหรับ IP และ hostname
cd D:\dev\MTSecurity\my_workspace\nginx\ssl

mkcert -key-file key.pem -cert-file cert.pem localhost 127.0.0.1 192.168.1.x mtsecurity.local

# ไฟล์ที่ได้:
#   nginx/ssl/cert.pem
#   nginx/ssl/key.pem
```

> ⚠️ **Client ทุกเครื่องต้อง trust root CA** ด้วย:
> ```
> mkcert -CAROOT    ← หาที่อยู่ rootCA.pem
> # ส่ง rootCA.pem ให้ client แต่ละเครื่อง import
> ```

### เปิดใช้ SSL ใน docker-compose.infra.yml

แก้ไข `docker-compose.infra.yml` ส่วน nginx:

```yaml
nginx:
  image: nginx:1.27-alpine
  ports:
    - "80:80"
    - "443:443"    # เพิ่ม port 443
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    - ./nginx/conf.d/mtsecurity.ssl.conf:/etc/nginx/conf.d/mtsecurity.conf:ro   # เปลี่ยนเป็น ssl
    - ./nginx/ssl:/etc/nginx/ssl:ro                                              # mount cert
  extra_hosts:
    - "host.docker.internal:host-gateway"
```

```powershell
# Restart nginx
docker compose -f docker-compose.infra.yml up -d nginx
```

---

## สรุปการเลือก

| Scenario | เหมาะกับ | ความยาก |
|----------|---------|---------|
| HTTP only | LAN trusted network, dev | ✅ ไม่ต้องทำอะไร |
| Cloudflare Tunnel | External access, production | ⭐ ง่าย แนะนำ |
| mkcert LAN HTTPS | HTTPS ใน LAN ไม่ต้องการ internet | ⭐⭐ ปานกลาง |
| Let's Encrypt (Certbot) | Public domain, no Cloudflare | ⭐⭐⭐ ต้องการ Static IP |

**แนะนำ:** ตอนนี้ใช้ HTTP ใน LAN → เมื่อพร้อม deploy ภายนอกใช้ Cloudflare Tunnel
