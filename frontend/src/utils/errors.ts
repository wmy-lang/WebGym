/**
 * 把后端业务错误码翻译成中文提示。
 * 后端约定：错误体形如 ``{error: "<code>", details?: {...}}``。
 */

const ERROR_MESSAGES: Record<string, string> = {
  // 通用
  validation_error: '输入有误，请检查表单',
  not_found: '记录不存在',
  forbidden: '没有权限',
  conflict: '数据冲突',
  unauthorized: '请先登录',
  method_not_allowed: '请求方式不正确',

  // 认证
  invalid_credentials: '用户名或密码错误',
  account_disabled: '账号已被禁用',

  // 会员
  username_taken: '用户名已被占用',
  phone_taken: '手机号已被占用',

  // 卡类型
  name_taken: '名称已存在',

  // 会员卡
  member_not_found: '会员不存在',
  member_disabled: '会员账号已禁用',
  card_type_not_found: '卡类型不存在',
  card_not_found: '会员卡不存在',
  card_frozen: '该卡已冻结',
  card_cancelled: '该卡已注销',
  card_not_active: '该卡当前不可用',
  card_not_frozen: '该卡当前未处于冻结状态',
  card_visits_exhausted: '次卡剩余次数为 0',

  // 课程 / 排课
  class_not_found: '课程不存在',
  coach_not_found: '教练不存在',
  invalid_datetime: '日期格式不正确',
  invalid_status: '状态参数不合法',
  session_not_scheduled: '排课已不可修改',

  // 预约
  session_not_found: '排课不存在',
  session_not_open: '排课不可预约',
  session_already_started: '排课已开始，无法预约',
  no_usable_card: '没有可用会员卡',
  already_booked: '已存在有效预约',
  session_full: '排课已满员',
  booking_not_found: '预约不存在',
  booking_locked: '预约已不能修改',
  cancel_cutoff_passed: '距开课不足 2 小时，无法自助取消',
  booking_not_active: '预约当前不可签到',
  already_checked_in: '已签到，请勿重复操作',
}

export function translateError(code: string | undefined | null): string {
  if (!code) return '操作失败'
  return ERROR_MESSAGES[code] ?? code
}

export function extractErrorCode(err: any): string | null {
  return err?.response?.data?.error ?? null
}
