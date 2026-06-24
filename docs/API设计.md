# API 设计

> 论文第 4 章原料。对应 `docs/设计方案.md` §2、§6。主要引用：[1][2][10]。

## 1. 总览：RESTful 资源约定

- 前缀统一 `/api/`
- 鉴权：登录后 session cookie；写操作必须带 `X-CSRFToken` 头（`/api/auth/login` 例外）
- 资源命名：复数名词；嵌套保留浅层（`/members/{id}`、`/coaches/{id}`、`/card-types/{id}`）
- 列表分页：`?page=1&per_page=20`，最大 `per_page=100`；返回 `{items, meta:{page, per_page, total, pages}}`
- 写操作语义：`POST` 创建、`PATCH` 局部更新、`DELETE` 软删除（`is_active=False`）
- 错误体：`{"error": "<code>"[, "details": {...}]}`，HTTP 状态码 + 错误码双轨

## 2. 认证接口

| Method | Path | 权限 | 说明 |
|---|---|---|---|
| GET | `/api/auth/csrf-token` | 公开 | 下发 CSRF token（SPA 启动时调一次） |
| POST | `/api/auth/login` | 公开 | `{username, password}` → 设置 session + 返回 `user` |
| POST | `/api/auth/logout` | 已登录 | 清 session |
| GET | `/api/auth/me` | 已登录 | 返回当前用户 |

错误码：`invalid_credentials`（400 字段缺失 / 401 验证失败）、`account_disabled`（403）、`unauthorized`（401）。

## 3. 会员接口（/api/members/*）

| Method | Path | 权限 | 说明 |
|---|---|---|---|
| GET | `/api/members` | staff | `?q=` 模糊搜（username/real_name/phone）、`?include_inactive=1` 显示禁用 |
| POST | `/api/members` | staff | 创建会员账号（User + MemberProfile 同事务） |
| GET | `/api/members/{id}` | staff | 详情 |
| PATCH | `/api/members/{id}` | staff | 改资料 / `is_active` |
| DELETE | `/api/members/{id}` | staff | 软删除（`is_active=False`） |

**创建入参**：`username` (3-64), `password` (≥6), `real_name`, `phone`，可选 `gender/birthday/id_card/emergency_contact/note`。`id_card` 入库 Fernet 加密。

**错误码**：`username_taken` (409)、`phone_taken` (409)、`validation_error` (400)、`not_found` (404)。

## 4. 卡接口（/api/cards/*）

| Method | Path | 权限 | 说明 |
|---|---|---|---|
| GET | `/api/cards` | 已登录 | staff 可全部；member 只看自己 |
| GET | `/api/cards/{id}` | 已登录 | 同上；member 越权 → 403 |
| POST | `/api/cards` | staff | 办卡 `{member_id, card_type_id, start_date?}` |
| POST | `/api/cards/{id}/renew` | staff | 续费：期限+duration / 次数+visits |
| POST | `/api/cards/{id}/freeze` | staff | active → frozen |
| POST | `/api/cards/{id}/unfreeze` | staff | frozen → active（已过期则 → expired） |
| POST | `/api/cards/{id}/cancel` | staff | 任意非 cancelled → cancelled（终态） |
| POST | `/api/cards/sweep-expired` | staff | 批量把已过期卡置 expired |

**列表过滤**：`?member_id=`（staff 用）/ `?status=active|frozen|expired|cancelled`

**业务错误**（HTTP 400/404）：`member_not_found`、`member_disabled`、`card_type_not_found`、`card_not_found`、`card_frozen`、`card_cancelled`、`card_not_active`、`card_not_frozen`。

状态机详见 `docs/数据库设计.md`。


## 5. 教练接口（/api/coaches/*）

| Method | Path | 权限 | 说明 |
|---|---|---|---|
| GET | `/api/coaches` | staff | `?q=` 按 name 模糊；`?include_inactive=1` |
| POST | `/api/coaches` | staff | `{name, gender?, phone?, specialty?, bio?, hired_at?}` |
| GET | `/api/coaches/{id}` | staff | 详情 |
| PATCH | `/api/coaches/{id}` | staff | 改资料 / `is_active` |
| DELETE | `/api/coaches/{id}` | staff | 软删除 |

## 6. 卡类型接口（/api/card-types/*）

| Method | Path | 权限 | 说明 |
|---|---|---|---|
| GET | `/api/card-types` | staff | 读 |
| POST | `/api/card-types` | **admin** | `{name, duration_days?, total_visits?, price}`；两个 dimension 至少填一个 |
| GET | `/api/card-types/{id}` | staff | 详情 |
| PATCH | `/api/card-types/{id}` | **admin** | 改价 / 名 / `is_active` |
| DELETE | `/api/card-types/{id}` | **admin** | 软删除 |

错误码：`name_taken` (409)、`validation_error` (400)、`not_found` (404)。

## 7. 课程与排课接口（/api/classes/* + /api/sessions/*）

### 7.1 课程定义 `/api/classes/*`

| Method | Path | 权限 | 说明 |
|---|---|---|---|
| GET | `/api/classes` | 已登录 | member 仅看 active；staff 可 `?include_inactive=1` |
| POST | `/api/classes` | staff | `{name, description?, coach_id?, capacity, duration_minutes}` |
| GET | `/api/classes/{id}` | 已登录 | member 看 inactive → 404 |
| PATCH | `/api/classes/{id}` | staff | 局部更新 |
| DELETE | `/api/classes/{id}` | staff | 软删除 |

### 7.2 排课 `/api/sessions/*`

| Method | Path | 权限 | 说明 |
|---|---|---|---|
| GET | `/api/sessions` | 已登录 | 过滤：`?from=ISO&to=ISO&class_def_id=&coach_id=&status=` |
| POST | `/api/sessions` | staff | `{class_def_id, start_at, end_at?, coach_id?, capacity?, location?}`；缺省字段从 class_def 继承 |
| GET | `/api/sessions/{id}` | 已登录 | 单条详情 |
| PATCH | `/api/sessions/{id}` | staff | 仅当 `status=scheduled` 时可改 |
| POST | `/api/sessions/{id}/cancel` | staff | 切 `cancelled`，连带把 `booked` 预约置 `cancelled` |
| POST | `/api/sessions/{id}/finish` | staff | 切 `finished`，未签到的 `booked` → `no_show` |

`ClassSession` 返回体新增 `booked_count`：当前有效预约数（非 cancelled），便于前端判满员。

错误码：`class_not_found`、`coach_not_found`、`invalid_datetime`、`invalid_status`、`session_not_scheduled`、`validation_error`。


## 8. 预约接口（/api/bookings/*）

| Method | Path | 权限 | 说明 |
|---|---|---|---|
| GET | `/api/bookings` | 已登录 | member 仅看自己；staff 可 `?member_id=&session_id=&status=` |
| POST | `/api/bookings` | 已登录 | member：`{session_id}`；staff 必填 `{session_id, member_id}` |
| GET | `/api/bookings/{id}` | 已登录 | member 越权 → 403 |
| POST | `/api/bookings/{id}/cancel` | 已登录 | member 仅取消自己；距开课 ≤ 2h 不能自助取消（staff 可绕过） |

**预约规则（service 层强制）**：

- 会员必须 active 且 `is_active=True`
- session 必须 `status=scheduled` 且 `start_at > now`
- 挑卡顺序：期限卡 end_date 升序 → id 升序；次卡仅在没有期限卡可用时使用
- 同会员同 session 不能同时存在非 cancelled 预约（partial unique 索引 + 预查询双重兜底）
- 不超过 `session.capacity`
- 预约阶段**不**扣次卡，签到时才扣

**业务错误**：`member_not_found` (404)、`member_disabled` (403)、`session_not_found` (404)、`session_not_open` (400)、`session_already_started` (400)、`no_usable_card` (403)、`already_booked` (409)、`session_full` (409)、`booking_not_found` (404)、`forbidden` (403)、`booking_locked` (400)、`cancel_cutoff_passed` (400)。

**返回体（Read）**：`id, member_id, member_name, session_id, class_name, start_at, end_at, card_id, card_no, status, source, booked_at, cancelled_at, checked_in_at`。

## 9. 签到接口（/api/attendance/*）

| Method | Path | 权限 | 说明 |
|---|---|---|---|
| GET | `/api/attendance` | 已登录 | member 仅看自己；staff 可 `?member_id=&session_id=` |
| POST | `/api/attendance` | 已登录 | `{booking_id}`；member 仅可为自己签到 |

**签到规则**：

- 仅 `booking.status=booked` 可签到（已 cancelled / attended / no_show 均拒绝）
- session 必须 `status=scheduled`
- 次卡（`remaining_visits IS NOT NULL`）此时扣 1 次；`remaining_visits ≤ 0` → `card_visits_exhausted`
- 同一 booking 重复签到 → `already_checked_in` (409)

**业务错误**：`booking_not_found` (404)、`forbidden` (403)、`already_checked_in` (409)、`booking_not_active` (400)、`session_not_open` (400)、`card_visits_exhausted` (400)。

**返回体（Read）**：`id, booking_id, member_id, member_name, session_id, class_name, checked_in_at, checked_in_by`。

## 10. 统计接口（/api/stats/*）

> W11 落地。

## 11. 导出接口（/api/exports/*）

> W11 落地。

## 12. 错误码约定

| HTTP | error code | 含义 |
|---|---|---|
| 400 | `validation_error` | Marshmallow 校验失败，附 `details` |
| 400 | `invalid_credentials` | 登录字段缺失 |
| 401 | `unauthorized` | 未登录 |
| 401 | `invalid_credentials` | 登录失败（用户不存在或密码错） |
| 403 | `forbidden` | 已登录但角色不符 |
| 403 | `account_disabled` | 账号被禁用 |
| 404 | `not_found` | 资源不存在 |
| 405 | `method_not_allowed` | 路由方法错 |
| 409 | `username_taken` / `phone_taken` / `name_taken` | 唯一约束冲突 |

## 13. 与 Spring `@RestController` 路由风格对照（[1][2]）

| 本项目（Flask） | Spring Boot 对应 |
|---|---|
| `@bp.get("/members")` | `@GetMapping("/members")` |
| `@bp.post("/members")` | `@PostMapping` + `@RequestBody` |
| `@staff_required` | `@PreAuthorize("hasAnyRole('ADMIN','STAFF')")` |
| Marshmallow `Schema().load()` | `@Valid` + Bean Validation |
| `jsonify(error=..., details=...)` | `ResponseEntity<ErrorResponse>` + `@ControllerAdvice` |
