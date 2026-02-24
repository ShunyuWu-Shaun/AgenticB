# 安装与启动

## 环境要求
- Python `3.11+`
- 建议：Docker / Docker Compose（用于本地联调 Redis/MySQL）

## 方式一：本地 Python 运行
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn easyshift_maas.api.app:app --reload --port 8000
```

服务启动后：
- OpenAPI: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`

## 方式二：Docker Compose 联调
```bash
docker compose up --build
```

默认包含：
- `easyshift-api`
- `redis`
- `mysql`

默认开发密钥文件位置：`deploy/secrets/`。

## 可选：Nuitka 构建可执行文件
```bash
pip install '.[build]'
./scripts/build_nuitka.sh
```

输出：
- `dist/easyshift-maas`（CLI）
- `dist/easyshift-maas-api`（API 服务）

## 运行测试
```bash
pytest
python tools/sensitive_scan.py
```
