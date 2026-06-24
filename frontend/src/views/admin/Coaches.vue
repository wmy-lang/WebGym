<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  listCoaches,
  createCoach,
  updateCoach,
  deactivateCoach,
  type Coach,
  type CoachCreatePayload,
} from '@/api/coaches'
import type { Gender } from '@/api/members'
import { translateError, extractErrorCode } from '@/utils/errors'
import { formatDate } from '@/utils/format'

const loading = ref(false)
const rows = ref<Coach[]>([])
const total = ref(0)
const query = reactive({ page: 1, per_page: 20, q: '', include_inactive: false })

async function load() {
  loading.value = true
  try {
    const { items, meta } = await listCoaches(query)
    rows.value = items
    total.value = meta.total
  } catch (err) {
    ElMessage.error(translateError(extractErrorCode(err)))
  } finally {
    loading.value = false
  }
}
onMounted(load)
function onSearch() { query.page = 1; load() }

const formOpen = ref(false)
const editing = ref<Coach | null>(null)
const form = reactive<CoachCreatePayload & { gender: Gender | null; is_active?: boolean }>({
  name: '', gender: null, phone: '', specialty: '', bio: '', hired_at: null,
})
const formRef = ref<FormInstance>()
const rules: FormRules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
}

function openCreate() {
  editing.value = null
  Object.assign(form, { name: '', gender: null, phone: '', specialty: '', bio: '', hired_at: null, is_active: true })
  formOpen.value = true
}
function openEdit(row: Coach) {
  editing.value = row
  Object.assign(form, {
    name: row.name, gender: row.gender, phone: row.phone || '',
    specialty: row.specialty || '', bio: row.bio || '', hired_at: row.hired_at,
    is_active: row.is_active,
  })
  formOpen.value = true
}

async function submit() {
  if (!formRef.value) return
  const ok = await formRef.value.validate().catch(() => false)
  if (!ok) return
  const payload = {
    name: form.name.trim(),
    gender: form.gender || null,
    phone: form.phone || null,
    specialty: form.specialty || null,
    bio: form.bio || null,
    hired_at: form.hired_at || null,
  }
  try {
    if (editing.value) {
      await updateCoach(editing.value.id, { ...payload, is_active: form.is_active })
    } else {
      await createCoach(payload)
    }
    ElMessage.success('已保存')
    formOpen.value = false
    load()
  } catch (err) {
    ElMessage.error(translateError(extractErrorCode(err)))
  }
}

async function onDeactivate(row: Coach) {
  try { await ElMessageBox.confirm(`禁用教练"${row.name}"？`, '提示', { type: 'warning' }) } catch { return }
  try {
    await deactivateCoach(row.id)
    ElMessage.success('已禁用')
    load()
  } catch (err) { ElMessage.error(translateError(extractErrorCode(err))) }
}

async function onReactivate(row: Coach) {
  try {
    await updateCoach(row.id, { is_active: true })
    ElMessage.success('已启用')
    load()
  } catch (err) { ElMessage.error(translateError(extractErrorCode(err))) }
}

function genderLabel(g: Gender | null) {
  if (g === 'male') return '男'
  if (g === 'female') return '女'
  if (g === 'other') return '其他'
  return '—'
}
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="toolbar">
        <div class="filters">
          <el-input v-model="query.q" placeholder="教练姓名" clearable style="width: 200px" @keyup.enter="onSearch" />
          <el-checkbox v-model="query.include_inactive" @change="onSearch">显示已离职</el-checkbox>
          <el-button type="primary" @click="onSearch">搜索</el-button>
        </div>
        <el-button type="success" @click="openCreate">新建教练</el-button>
      </div>
    </template>

    <el-table v-loading="loading" :data="rows" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="name" label="姓名" width="120" />
      <el-table-column label="性别" width="80">
        <template #default="{ row }">{{ genderLabel(row.gender) }}</template>
      </el-table-column>
      <el-table-column prop="phone" label="手机号" width="140" />
      <el-table-column prop="specialty" label="专长" />
      <el-table-column label="入职日期" width="120">
        <template #default="{ row }">{{ formatDate(row.hired_at) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.is_active" type="success">在职</el-tag>
          <el-tag v-else type="info">离职</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" fixed="right" width="160">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="row.is_active" link type="danger" @click="onDeactivate(row)">禁用</el-button>
          <el-button v-else link type="success" @click="onReactivate(row)">启用</el-button>
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

  <el-dialog v-model="formOpen" :title="editing ? '编辑教练' : '新建教练'" width="500px">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="92px">
      <el-form-item label="姓名" prop="name"><el-input v-model="form.name" /></el-form-item>
      <el-form-item label="性别">
        <el-select v-model="form.gender" placeholder="—" clearable style="width: 100%">
          <el-option label="男" value="male" /><el-option label="女" value="female" /><el-option label="其他" value="other" />
        </el-select>
      </el-form-item>
      <el-form-item label="手机号"><el-input v-model="form.phone" /></el-form-item>
      <el-form-item label="专长"><el-input v-model="form.specialty" placeholder="如：瑜伽,普拉提" /></el-form-item>
      <el-form-item label="入职日期">
        <el-date-picker v-model="form.hired_at" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
      </el-form-item>
      <el-form-item label="简介"><el-input v-model="form.bio" type="textarea" :rows="3" /></el-form-item>
      <el-form-item v-if="editing" label="状态"><el-switch v-model="form.is_active" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="formOpen = false">取消</el-button>
      <el-button type="primary" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; }
.filters { display: flex; gap: 12px; align-items: center; }
.pager { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
