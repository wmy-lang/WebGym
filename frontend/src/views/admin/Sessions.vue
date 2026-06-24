<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  listSessions, createSession, cancelSession, finishSession,
  type ClassSession, type SessionStatus, type SessionCreatePayload,
} from '@/api/sessions'
import { listClasses, type ClassDefinition } from '@/api/classes'
import { listCoaches, type Coach } from '@/api/coaches'
import { translateError, extractErrorCode } from '@/utils/errors'
import { formatDateTime, toIsoNaive } from '@/utils/format'

const loading = ref(false)
const rows = ref<ClassSession[]>([])
const total = ref(0)
const query = reactive<{
  page: number; per_page: number;
  from?: string; to?: string;
  class_def_id?: number; coach_id?: number; status?: SessionStatus;
}>({ page: 1, per_page: 20 })
const dateRange = ref<[string, string] | null>(null)

const statusOptions: { label: string; value: SessionStatus }[] = [
  { label: '待开课', value: 'scheduled' },
  { label: '已取消', value: 'cancelled' },
  { label: '已结束', value: 'finished' },
]

async function load() {
  loading.value = true
  if (dateRange.value && dateRange.value.length === 2) {
    query.from = toIsoNaive(dateRange.value[0])
    query.to = toIsoNaive(dateRange.value[1])
  } else {
    query.from = undefined
    query.to = undefined
  }
  try {
    const { items, meta } = await listSessions(query)
    rows.value = items
    total.value = meta.total
  } catch (err) { ElMessage.error(translateError(extractErrorCode(err))) }
  finally { loading.value = false }
}
onMounted(async () => { await loadOptions(); load() })

const classOptions = ref<ClassDefinition[]>([])
const coachOptions = ref<Coach[]>([])
async function loadOptions() {
  const [cls, coa] = await Promise.all([listClasses({ per_page: 100 }), listCoaches({ per_page: 100 })])
  classOptions.value = cls.items.filter((c) => c.is_active)
  coachOptions.value = coa.items.filter((c) => c.is_active)
}

function onSearch() { query.page = 1; load() }

// ---------- 新建排课 ----------
const formOpen = ref(false)
const form = reactive<SessionCreatePayload & { start_at: string }>({
  class_def_id: 0, start_at: '', end_at: null, coach_id: null, capacity: null, location: null,
})
const formRef = ref<FormInstance>()
const rules: FormRules = {
  class_def_id: [{ required: true, message: '请选择课程', trigger: 'change' }],
  start_at: [{ required: true, message: '请选择开课时间', trigger: 'change' }],
}

function openCreate() {
  Object.assign(form, { class_def_id: 0, start_at: '', end_at: null, coach_id: null, capacity: null, location: null })
  formOpen.value = true
}

async function submit() {
  if (!formRef.value) return
  const ok = await formRef.value.validate().catch(() => false)
  if (!ok) return
  try {
    await createSession({
      class_def_id: form.class_def_id,
      start_at: toIsoNaive(form.start_at) as string,
      end_at: form.end_at ? toIsoNaive(form.end_at) : null,
      coach_id: form.coach_id || null,
      capacity: form.capacity || null,
      location: form.location || null,
    })
    ElMessage.success('已排课')
    formOpen.value = false
    load()
  } catch (err) { ElMessage.error(translateError(extractErrorCode(err))) }
}

async function onCancel(row: ClassSession) {
  try {
    await ElMessageBox.confirm('取消该排课？已预约的会员将自动取消', '提示', { type: 'warning' })
  } catch { return }
  try { await cancelSession(row.id); ElMessage.success('已取消'); load() }
  catch (err) { ElMessage.error(translateError(extractErrorCode(err))) }
}
async function onFinish(row: ClassSession) {
  try {
    await ElMessageBox.confirm('标记为已结束？未签到的会员将记为缺席', '提示', { type: 'info' })
  } catch { return }
  try { await finishSession(row.id); ElMessage.success('已结束'); load() }
  catch (err) { ElMessage.error(translateError(extractErrorCode(err))) }
}

function statusTag(s: SessionStatus): { type: 'success' | 'info' | 'danger'; text: string } {
  if (s === 'scheduled') return { type: 'success', text: '待开课' }
  if (s === 'cancelled') return { type: 'danger', text: '已取消' }
  return { type: 'info', text: '已结束' }
}
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="toolbar">
        <div class="filters">
          <el-date-picker
            v-model="dateRange" type="datetimerange" range-separator="至"
            start-placeholder="开始" end-placeholder="结束"
            value-format="YYYY-MM-DD HH:mm:ss" style="width: 360px"
          />
          <el-select v-model="query.class_def_id" placeholder="课程" clearable style="width: 160px">
            <el-option v-for="c in classOptions" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
          <el-select v-model="query.coach_id" placeholder="教练" clearable style="width: 140px">
            <el-option v-for="c in coachOptions" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
          <el-select v-model="query.status" placeholder="状态" clearable style="width: 120px">
            <el-option v-for="o in statusOptions" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
          <el-button type="primary" @click="onSearch">搜索</el-button>
        </div>
        <el-button type="success" @click="openCreate">新建排课</el-button>
      </div>
    </template>

    <el-table v-loading="loading" :data="rows" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="class_name" label="课程" width="140" />
      <el-table-column prop="coach_name" label="教练" width="100" />
      <el-table-column label="开课时间" width="160">
        <template #default="{ row }">{{ formatDateTime(row.start_at) }}</template>
      </el-table-column>
      <el-table-column label="结束时间" width="160">
        <template #default="{ row }">{{ formatDateTime(row.end_at) }}</template>
      </el-table-column>
      <el-table-column label="人数" width="120">
        <template #default="{ row }">
          <el-tag :type="row.booked_count >= row.capacity ? 'danger' : 'primary'" effect="plain">
            {{ row.booked_count }} / {{ row.capacity }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="location" label="地点" width="120" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTag(row.status).type">{{ statusTag(row.status).text }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" fixed="right" width="180">
        <template #default="{ row }">
          <template v-if="row.status === 'scheduled'">
            <el-button link type="info" @click="onFinish(row)">结束</el-button>
            <el-button link type="danger" @click="onCancel(row)">取消排课</el-button>
          </template>
          <span v-else style="color: #c0c4cc">—</span>
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

  <el-dialog v-model="formOpen" title="新建排课" width="500px">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="92px">
      <el-form-item label="课程" prop="class_def_id">
        <el-select v-model="form.class_def_id" placeholder="选择课程" style="width: 100%">
          <el-option v-for="c in classOptions" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="开课时间" prop="start_at">
        <el-date-picker
          v-model="form.start_at" type="datetime" value-format="YYYY-MM-DD HH:mm:ss"
          placeholder="选择开课时间" style="width: 100%"
        />
      </el-form-item>
      <el-form-item label="结束时间">
        <el-date-picker
          v-model="form.end_at" type="datetime" value-format="YYYY-MM-DD HH:mm:ss"
          placeholder="留空则按课程时长自动计算" style="width: 100%"
        />
      </el-form-item>
      <el-form-item label="代课教练">
        <el-select v-model="form.coach_id" placeholder="留空使用课程默认教练" clearable style="width: 100%">
          <el-option v-for="c in coachOptions" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="容量">
        <el-input-number v-model="form.capacity" :min="1" :max="500" controls-position="right" />
        <span style="margin-left: 8px; color: #909399">留空使用课程默认值</span>
      </el-form-item>
      <el-form-item label="地点"><el-input v-model="form.location" placeholder="如：A 教室" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="formOpen = false">取消</el-button>
      <el-button type="primary" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; }
.filters { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.pager { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
