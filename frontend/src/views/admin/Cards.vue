<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  listCards,
  issueCard,
  renewCard,
  freezeCard,
  unfreezeCard,
  cancelCard,
  sweepExpiredCards,
  type Card,
  type CardStatus,
} from '@/api/cards'
import { listMembers, type Member } from '@/api/members'
import { listCardTypes, type CardType } from '@/api/cardTypes'
import { translateError, extractErrorCode } from '@/utils/errors'
import { formatDate, formatDateTime } from '@/utils/format'

const loading = ref(false)
const rows = ref<Card[]>([])
const total = ref(0)
const query = reactive<{ page: number; per_page: number; member_id?: number; status?: CardStatus }>({
  page: 1, per_page: 20, member_id: undefined, status: undefined,
})

const statusOptions: { label: string; value: CardStatus }[] = [
  { label: '使用中', value: 'active' },
  { label: '已冻结', value: 'frozen' },
  { label: '已过期', value: 'expired' },
  { label: '已注销', value: 'cancelled' },
]

async function load() {
  loading.value = true
  try {
    const { items, meta } = await listCards(query)
    rows.value = items
    total.value = meta.total
  } catch (err) {
    ElMessage.error(translateError(extractErrorCode(err)))
  } finally { loading.value = false }
}
onMounted(load)

// ---------- 远程会员搜索（用于过滤 + 办卡） ----------
const memberOptions = ref<Member[]>([])
const memberSearchLoading = ref(false)
async function searchMembers(keyword: string) {
  memberSearchLoading.value = true
  try {
    const { items } = await listMembers({ q: keyword, per_page: 20 })
    memberOptions.value = items
  } finally { memberSearchLoading.value = false }
}

// ---------- 办卡 ----------
const issueOpen = ref(false)
const issueForm = reactive<{ member_id: number | null; card_type_id: number | null; start_date: string | null }>({
  member_id: null, card_type_id: null, start_date: null,
})
const issueRef = ref<FormInstance>()
const issueRules: FormRules = {
  member_id: [{ required: true, message: '请选择会员', trigger: 'change' }],
  card_type_id: [{ required: true, message: '请选择卡类型', trigger: 'change' }],
}
const cardTypeOptions = ref<CardType[]>([])

async function openIssue() {
  Object.assign(issueForm, { member_id: null, card_type_id: null, start_date: null })
  // 拉所有卡类型（数量少，一次加载够）
  const { items } = await listCardTypes({ per_page: 100 })
  cardTypeOptions.value = items.filter((t) => t.is_active)
  issueOpen.value = true
}

async function submitIssue() {
  if (!issueRef.value) return
  const ok = await issueRef.value.validate().catch(() => false)
  if (!ok) return
  try {
    await issueCard({
      member_id: issueForm.member_id as number,
      card_type_id: issueForm.card_type_id as number,
      start_date: issueForm.start_date || null,
    })
    ElMessage.success('办卡成功')
    issueOpen.value = false
    load()
  } catch (err) { ElMessage.error(translateError(extractErrorCode(err))) }
}

// ---------- 卡操作 ----------
async function onRenew(row: Card) {
  try {
    const card = row.card_type_name ? `（${row.card_type_name}）` : ''
    await ElMessageBox.confirm(`续费卡 ${row.card_no}${card}？`, '提示', { type: 'info' })
  } catch { return }
  try {
    await renewCard(row.id)
    ElMessage.success('续费成功')
    load()
  } catch (err) { ElMessage.error(translateError(extractErrorCode(err))) }
}
async function onFreeze(row: Card) {
  try { await ElMessageBox.confirm(`冻结卡 ${row.card_no}？`, '提示', { type: 'warning' }) } catch { return }
  try { await freezeCard(row.id); ElMessage.success('已冻结'); load() }
  catch (err) { ElMessage.error(translateError(extractErrorCode(err))) }
}
async function onUnfreeze(row: Card) {
  try { await unfreezeCard(row.id); ElMessage.success('已解冻'); load() }
  catch (err) { ElMessage.error(translateError(extractErrorCode(err))) }
}
async function onCancel(row: Card) {
  try { await ElMessageBox.confirm(`注销卡 ${row.card_no}？此操作不可恢复`, '警告', { type: 'error' }) } catch { return }
  try { await cancelCard(row.id); ElMessage.success('已注销'); load() }
  catch (err) { ElMessage.error(translateError(extractErrorCode(err))) }
}
async function onSweep() {
  try { await ElMessageBox.confirm('扫描所有已过期卡并标记 expired？', '提示', { type: 'info' }) } catch { return }
  try {
    const { affected } = await sweepExpiredCards()
    ElMessage.success(`已处理 ${affected} 张卡`)
    load()
  } catch (err) { ElMessage.error(translateError(extractErrorCode(err))) }
}

function statusTag(s: CardStatus): { type: 'success' | 'warning' | 'info' | 'danger'; text: string } {
  if (s === 'active') return { type: 'success', text: '使用中' }
  if (s === 'frozen') return { type: 'warning', text: '已冻结' }
  if (s === 'expired') return { type: 'info', text: '已过期' }
  return { type: 'danger', text: '已注销' }
}
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="toolbar">
        <div class="filters">
          <el-select
            v-model="query.member_id" placeholder="按会员筛选" clearable filterable remote
            :remote-method="searchMembers" :loading="memberSearchLoading" style="width: 220px"
            @change="() => { query.page = 1; load() }"
          >
            <el-option v-for="m in memberOptions" :key="m.id" :label="`${m.real_name || m.username} (${m.phone || '—'})`" :value="m.id" />
          </el-select>
          <el-select v-model="query.status" placeholder="状态" clearable style="width: 140px" @change="() => { query.page = 1; load() }">
            <el-option v-for="o in statusOptions" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
          <el-button @click="onSweep">扫描过期</el-button>
        </div>
        <el-button type="success" @click="openIssue">办卡</el-button>
      </div>
    </template>

    <el-table v-loading="loading" :data="rows" stripe>
      <el-table-column prop="card_no" label="卡号" width="180" />
      <el-table-column prop="member_name" label="会员" width="120" />
      <el-table-column prop="card_type_name" label="卡类型" width="140" />
      <el-table-column label="开始日" width="120">
        <template #default="{ row }">{{ formatDate(row.start_date) }}</template>
      </el-table-column>
      <el-table-column label="截止日" width="120">
        <template #default="{ row }">{{ formatDate(row.end_date) }}</template>
      </el-table-column>
      <el-table-column label="剩余次数" width="100">
        <template #default="{ row }">{{ row.remaining_visits ?? '—' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTag(row.status).type">{{ statusTag(row.status).text }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="办卡时间" width="160">
        <template #default="{ row }">{{ formatDateTime(row.issued_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" fixed="right" width="240">
        <template #default="{ row }">
          <el-button link type="primary" @click="onRenew(row)" :disabled="row.status === 'cancelled'">续费</el-button>
          <el-button v-if="row.status === 'active'" link type="warning" @click="onFreeze(row)">冻结</el-button>
          <el-button v-if="row.status === 'frozen'" link type="success" @click="onUnfreeze(row)">解冻</el-button>
          <el-button v-if="row.status !== 'cancelled'" link type="danger" @click="onCancel(row)">注销</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pager">
      <el-pagination
        background layout="total, prev, pager, next, sizes" :total="total"
        v-model:current-page="query.page" v-model:page-size="query.per_page"
        :page-sizes="[10, 20, 50, 100]" @current-change="load" @size-change="load"
      />
    </div>
  </el-card>

  <el-dialog v-model="issueOpen" title="办卡" width="460px">
    <el-form ref="issueRef" :model="issueForm" :rules="issueRules" label-width="92px">
      <el-form-item label="会员" prop="member_id">
        <el-select
          v-model="issueForm.member_id" placeholder="搜索用户名 / 姓名 / 手机" filterable remote
          :remote-method="searchMembers" :loading="memberSearchLoading" style="width: 100%"
        >
          <el-option v-for="m in memberOptions" :key="m.id" :label="`${m.real_name || m.username} (${m.phone || '—'})`" :value="m.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="卡类型" prop="card_type_id">
        <el-select v-model="issueForm.card_type_id" placeholder="选择" style="width: 100%">
          <el-option v-for="t in cardTypeOptions" :key="t.id"
            :label="`${t.name} · ¥${t.price}` + (t.duration_days ? ` · ${t.duration_days}天` : '') + (t.total_visits ? ` · ${t.total_visits}次` : '')"
            :value="t.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="起始日">
        <el-date-picker v-model="issueForm.start_date" type="date" value-format="YYYY-MM-DD" placeholder="默认今天" style="width: 100%" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="issueOpen = false">取消</el-button>
      <el-button type="primary" @click="submitIssue">办卡</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; }
.filters { display: flex; gap: 12px; align-items: center; }
.pager { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
