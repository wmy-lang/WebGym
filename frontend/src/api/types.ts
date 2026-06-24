/**
 * 通用 API 类型。和后端 ``utils/pagination.py`` 的 ``{items, meta}`` 对齐。
 */

export interface PageMeta {
  page: number
  per_page: number
  total: number
  pages: number
}

export interface Paginated<T> {
  items: T[]
  meta: PageMeta
}

export interface PageQuery {
  page?: number
  per_page?: number
}
