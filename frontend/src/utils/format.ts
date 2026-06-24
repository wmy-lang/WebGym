/**
 * 日期格式化工具。后端 ``DateTime`` 字段以 ISO 字符串返回（naive UTC），
 * 这里统一按"当作本地时间"展示——避免在论文里再讨论时区飘移。
 */

export function formatDateTime(value?: string | null): string {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export function formatDate(value?: string | null): string {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/** Element Plus DatePicker 的 ``YYYY-MM-DDTHH:mm:ss`` → 后端要的 ISO；保留秒位。 */
export function toIsoNaive(value?: string | Date | null): string | undefined {
  if (!value) return undefined
  const d = typeof value === 'string' ? new Date(value) : value
  if (Number.isNaN(d.getTime())) return undefined
  const pad = (n: number) => String(n).padStart(2, '0')
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  )
}
