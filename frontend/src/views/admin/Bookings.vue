<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  listBookings, createBooking, cancelBooking,
  type Booking, type BookingStatus,
} from '@/api/bookings'
import { checkIn } from '@/api/attendance'
import { listMembers, type Member } from '@/api/members'
import { listSessions, type ClassSession } from '@/api/sessions'
import { translateError, extractErrorCode } from '@/utils/errors'
import { formatDateTime, toIsoNaive } from '@/utils/format'

const loading = ref(false)
const rows = ref<Booking[]>([])
const total = ref(0)
const query = reactive<{
  page: number; per_page: number;
  member_id?: number; session_id?: number; status?: BookingStatus;
}>({ page: 1, per_page: 20 })

const statusOptions: { label: string; value: BookingStatus }[] = [
  { label: '已预约', value: 'booked' },
  { label: '已签到', value: 'attended' },
  { label: '已取消', value: 'cancelled' },
  { label: '缺席', value: 'no_show' },
]

async function load() {
  loading.value = true
  try {
    const { items, meta } = await listBookings(query)
    rows.value = items
    total.value = meta.total
  } catch (err) { ElMessage.error(translateError(extractErrorCode(err))) }
  finally { loading.value = false }
}
onMounted(load)
function onSearch() { query.page = 1; load() }

// ---------- 会员远程搜索 ----------
const memberOptions = ref<Member[]>([])
const memberLoading = ref(false)
async function searchMembers(keyword: string) {
  memberLoading.value = true
  try {
    const { items } = await listMembers({ q: keyword, per_page: 20 })
    memberOptions.value = items
  } finally { memberLoading.value = false }
}

// ---------- 排课下拉（用未来 scheduled） ----------
const sessionOptions = ref<ClassSession[]>([])
async function loadFutureSessions() {
  const now = new Date()
  const fromIso = toIsoNaive(now) as string
  const { items } = await listSessions({ from: fromIso, status: 'scheduled', per_page: 50 })
  sessionOptions.value = items
}

// ---------- 代下单 ----------
const bookOpen = ref(false)
const bookForm = reactive<{ member_id: number | null; session_id: number | null }>({
  member_id: null, session_id: null,
})
const bookRef = ref<FormInstance>()
const bookRules: FormRules = {
  member_id: [{ required: true, message: '请选择会员', trigger: 'change' }],
  session_id: [{ required: true, message: '请选择排课', trigger: 'change' }],
}

async function openBook() {
  Object.assign(bookForm, { member_id: null, session_id: null })
  await loadFutureSessions()
  bookOpen.value = true
}

async function submitBook() {
  if (!bookRef.value) return
  const ok = await bookRef.value.validate().catch(() => false)
  if (!ok) return
  try {
    await createBooking({
      member_id: bookForm.member_id as number,
      session_id: bookForm.session_id as number,
    })
    ElMessage.success('已下单')
    bookOpen.value = false
    load()
  } catch (err) { ElMessage.error(translateError(extractErrorCode(err))) }
}

// ---------- 取消 ----------
async function onCancel(row: Booking) {
  try {
    await ElMessageBox.confirm(`取消"${row.member_name}"的"${row.class_name}"预约？`, '提示', { type: 'warning' })
  } catch { return }
  try { await cancelBooking(row.id); ElMessage.success('已取消'); load() }
  catch (err) { ElMessage.error(translateError(extractErrorCode(err))) }
}

// ---------- 代签到 ----------
async function onCheckIn(row: Booking) {
  try { await checkIn(row.id); ElMessage.success('签到成功'); load() }
  catch (err) { ElMessage.error(translateError(extractErrorCode(err))) }
}

function statusTag(s: BookingStatus): { type: 'success' | 'primary' | 'info' | 'warning'; text: string } {
  if (s === 'booked') return { type: 'primary', text: '已预约' }
  if (s === 'attended') return { type: 'success', text: '已签到' }
  if (s === 'cancelled') return { type: 'info', text: '已取消' }
  return { type: 'warning', text: '缺席' }
}
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="toolbar">
        <div class="filters">
          <el-select
            v-model="query.member_id" placeholder="按会员筛选" clearable filterable remote
            :remote-method="searchMembers" :loading="memberLoading" style="width: 220px"
            @change="onSearch"
          >
            <el-option v-for="m in memberOptions" :key="m.id" :label="`${m.real_name || m.username}`" :value="m.id" />
          </el-select>
          <el-select v-model="query.status" placeholder="状态" clearable style="width: 140px" @change="onSearch">
            <el-option v-for="o in statusOptions" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
          <el-button type="primary" @click="onSearch">搜索</el-button>
        </div>
        <el-button type="success" @click="openBook">代下单</el-button>
      </div>
    </template>

    <el-table v-loading="loading" :data="rows" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="member_name" label="会员" width="120" />
      <el-table-column prop="class_name" label="课程" width="140" />
      <el-table-column label="开课时间" width="160">
        <template #default="{ row }">{{ formatDateTime(row.start_at) }}</template>
      </el-table-column>
      <el-table-column prop="card_no" label="使用卡" width="160" />
      <el-table-column label="渠道" width="80">
        <template #default="{ row }">
          <el-tag size="small" :type="row.source === 'admin' ? 'warning' : 'info'" effect="plain">
            {{ row.source === 'admin' ? '代订' : '自助' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTag(row.status).type">{{ statusTag(row.status).text }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="预约时间" width="160">
        <template #default="{ row }">{{ formatDateTime(row.booked_at) }}</template>
      </el-table-column>
      <el-table-column label="签到时间" width="160">
        <template #default="{ row }">{{ formatDateTime(row.checked_in_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" fixed="right" width="180">
        <template #default="{ row }">
          <el-button v-if="row.status === 'booked'" link type="success" @click="onCheckIn(row)">代签到</el-button>
          <el-button v-if="row.status === 'booked'" link type="danger" @click="onCancel(row)">取消</el-button>
          <span v-if="row.status !== 'booked'" style="color: #c0c4cc">—</span>
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

  <el-dialog v-model="bookOpen" title="代会员下单" width="460px">
    <el-form ref="bookRef" :model="bookForm" :rules="bookRules" label-width="92px">
      <el-form-item label="会员" prop="member_id">
        <el-select
          v-model="bookForm.member_id" placeholder="搜索用户名 / 姓名 / 手机" filterable remote
          :remote-method="searchMembers" :loading="memberLoading" style="width: 100%"
        >
          <el-option v-for="m in memberOptions" :key="m.id" :label="`${m.real_name || m.username} (${m.phone || '—'})`" :value="m.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="排课" prop="session_id">
        <el-select v-model="bookForm.session_id" placeholder="选择课程" style="width: 100%">
          <el-option
            v-for="s in sessionOptions" :key="s.id" :value="s.id"
            :label="`${s.class_name} · ${formatDateTime(s.start_at)} · ${s.booked_count}/${s.capacity}`"
            :disabled="s.booked_count >= s.capacity"
          />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="bookOpen = false">取消</el-button>
      <el-button type="primary" @click="submitBook">下单</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; }
.filters { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.pager { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
