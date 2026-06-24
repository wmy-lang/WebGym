# WebGym Backend

Flask 3 + SQLAlchemy + SQLite。详见 `../docs/设计方案.md`。

## 本地启动

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate    # Windows Git Bash；CMD/PowerShell 用 .venv\Scripts\activate
pip install -e ".[dev]"
flask --app wsgi run --debug     # http://127.0.0.1:5000
```

健康检查：

```bash
curl http://127.0.0.1:5000/api/ping
```

## 测试

```bash
pytest                           # 单测
pytest --cov=app                 # 带覆盖率
```

## 配置切换

```bash
FLASK_CONFIG=test flask --app wsgi run    # 用 TestConfig（内存库、关 CSRF）
```
