# 安装与启动

## 环境要求
- Python `3.11+`
- 建议：Docker / Docker Compose（本地联调 Redis/MySQL）

## 本地运行
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,docs]'
uvicorn easyshift_maas.api.app:app --reload --port 8000
```

服务地址：
- OpenAPI: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`

## LLM 环境变量
```bash
export REFLEXFLOW_LLM_VENDOR=qwen
export REFLEXFLOW_LLM_API_KEY=your_api_key
export REFLEXFLOW_LLM_MODEL_PARSER=qwen-plus
export REFLEXFLOW_LLM_MODEL_GENERATOR=qwen-plus
export REFLEXFLOW_LLM_MODEL_CRITIC=qwen-plus
export REFLEXFLOW_LLM_TIMEOUT_SEC=30
```

支持供应商：`kimi`、`qwen`、`deepseek`、`openai`。

## Docker Compose
```bash
docker compose up --build
```

## Nuitka 构建
```bash
pip install '.[build]'
./scripts/build_nuitka.sh
```

输出：
- `dist/reflexflow-maas`（CLI）
- `dist/reflexflow-maas-api`（API）

## 测试与扫描
```bash
.venv/bin/pytest -q
.venv/bin/python tools/sensitive_scan.py
mkdocs build --strict
```
