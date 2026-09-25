# NFT Tracker — MRKT + Getgems

## Variables
```
BOT_TOKEN=
ADMIN_IDS=
WHITELIST_IDS=
MRKT_TOKEN=
GETGEMS_TOKEN=
POLL_INTERVAL=20
```

## Getgems token
API: `https://api.getgems.io/public-api/v1/nfts/offchain/on-sale/gifts`

Нужен Bearer-токен (живёт ~2 дня). Получение:
1. TON Proof → POST https://api.getgems.io/public-api/auth/ton-proof
2. Или запросить Gift API доступ у @nfton_bot

## MRKT token
web.telegram.org → @mrkt Mini App → F12 → Network → auth → token
