
# NURI – Piknik Online v2 (Flask-SocketIO)

10 kişiye kadar çevrim-içi, kategorili ve kg/adet/lt miktarlı piknik listesi.
Her değişiklik tüm kullanıcılara canlı olarak yansır.

## Hızlı Deploy (Render.com)
1) Bu repoyu bir GitHub reposuna yükle.
2) Render'da "New Web Service" → GitHub repo'yu seç.
3) `render.yaml` otomatik algılanır. (Plan: Free)
4) Açıldığında URL'yi arkadaşlarla paylaş.

## Yerelde çalıştırma
```bash
python -m venv .venv
# Windows PowerShell:
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass ; .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
export SECRET_KEY=dev && export MAX_USERS=10
gunicorn -k eventlet -w 1 app.server:app
# veya basit: python -m flask run  (SocketIO için gunicorn önerilir)
```

## API Kısa Özet
- `GET /api/items` — ürünler
- `POST /api/items {title,category,amount,unit,who}`
- `PATCH /api/items/<id>` — {title,category,amount,unit,who,status}
- `DELETE /api/items/<id>`
- `GET /api/categories`
- `GET /api/users`
- `POST /api/users {name}` — max 10 kişi
- WebSocket: `socket.io` üzerinden `state` / `presence` eventleri
