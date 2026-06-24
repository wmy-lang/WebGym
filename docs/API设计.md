# API 设计

> 论文第 4 章原料。对应 `docs/设计方案.md` §2、§6。主要引用：[1][2][10]。

## 1. 总览：RESTful 资源约定

## 2. 认证接口
### 2.1 GET /api/auth/csrf-token
### 2.2 POST /api/auth/login
### 2.3 POST /api/auth/logout
### 2.4 GET /api/auth/me

## 3. 会员接口（/api/members/*）

## 4. 卡接口（/api/cards/*）

## 5. 教练接口（/api/coaches/*）

## 6. 课程与排课接口（/api/classes/*）

## 7. 预约接口（/api/bookings/*）

## 8. 签到接口（/api/attendance/*）

## 9. 统计接口（/api/stats/*）

## 10. 导出接口（/api/exports/*）

## 11. 错误码约定

## 12. 与 Spring `@RestController` 路由风格对照（[1][2]）
