# 部署：Docker Compose

## 场景
适用于开发和联调。

## 启动
```bash
docker compose up --build
```

## 组件
- `reflexflow-api`
- `redis`
- `mysql`

## 密钥
Compose 使用 Docker secrets：
- `deploy/secrets/redis_conn.json`
- `deploy/secrets/mysql_conn.json`
- `deploy/secrets/mysql_password.txt`
- `deploy/secrets/mysql_root_password.txt`

> 这些默认值仅用于本地开发，生产环境必须替换。

## 验证
```bash
curl http://127.0.0.1:8000/health
```
