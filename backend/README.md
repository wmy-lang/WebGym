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

## 数据库迁移

```bash
flask --app wsgi db migrate -m "描述"   # 生成新迁移
flask --app wsgi db upgrade             # 应用
flask --app wsgi db downgrade -1        # 回滚一步
```

迁移文件位于 `migrations/versions/`，必须随代码提交。

## Seed / Reset

```bash
flask --app wsgi seed-demo              # 写演示数据（幂等）
flask --app wsgi reset-db               # 危险：清空并重建所有表
```

`seed-demo` 默认账号：`admin/admin123`、`staff01/staff123`、`alice/member123`（年卡）、`bob/member123`（10 次卡）。

## 测试

```bash
pytest                           # 单测
pytest --cov=app                 # 带覆盖率
```

## 配置切换

```bash
FLASK_CONFIG=test flask --app wsgi run    # 用 TestConfig（内存库、关 CSRF）
```
