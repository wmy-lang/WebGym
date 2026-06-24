<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  listClasses, createClass, updateClass, deactivateClass,
  type ClassDefinition, type ClassCreatePayload,
} from '@/api/classes'
import { listCoaches, type Coach } from '@/api/coaches'
import { translateError, extractErrorCode } from '@/utils/errors'

const loading = ref(false)
const rows = ref<ClassDefinition[]>([])
const total = ref(0)
const query = reactive({ page: 1, per_page: 20, q: '', include_inactive: false })

async function load() {
  loading.value = true
  try {
    const { items, meta } = await listClasses(query)
    rows.value = items
    total.value = meta.total
  } catch (err) { ElMessage.error(translateError(extractErrorCode(err))) }
  finally { loading.value = false }
}
onMounted(load)
function onSearch() { query.page = 1; load() }

// ---------- 教练下拉（创建时用） ----------
const coachOptions = ref<Coach[]>([])
async function loadCoaches() {
  const { items } = await listCoaches({ per_page: 100 })
  coachOptions.value = items
}

// ---------- 表单 ----------
const formOpen = ref(false)
const editing = ref<ClassDefinition | null>(null)
const form = reactive<ClassCreatePayload & { is_active?: boolean }>({
  name: '', description: '', coach_id: null, capacity: 10, duration_minutes: 60,
})
const formRef = ref<FormInstance>()
const rules: FormRules = {
  name: [{ required: true, message: '请输入课程名', trigger: 'blur' }],
  capacity: [{ required: true, message: '请输入容量', trigger: 'blur' }],
  duration_minutes: [{ required: true, message: '请输入时长', trigger: 'blur' }],
}

async function openCreate() {
  editing.value = null
  Object.assign(form, { name: '', description: '', coach_id: null, capacity: 10, duration_minutes: 60, is_active: true })
  await loadCoaches()
  formOpen.value = true
}
async function openEdit(row: ClassDefinition) {
  editing.value = row
  Object.assign(form, {
    name: row.name, description: row.description || '',
    coach_id: row.coach_id, capacity: row.capacity, duration_minutes: row.duration_minutes,
    is_active: row.is_active,
  })
  await loadCoaches()
  formOpen.value = true
}

async function submit() {
  if (!formRef.value) return
  const ok = await formRef.value.validate().catch(() => false)
  if (!ok) return
  try {
    const payload = {
      name: form.name.trim(),
      description: form.description || null,
      coach_id: form.coach_id || null,
      capacity: form.capacity,
      duration_minutes: form.duration_minutes,
    }
    if (editing.value) {
      await updateClass(editing.value.id, { ...payload, is_active: form.is_active })
    } else {
      await createClass(payload)
    }
    ElMessage.success('已保存')
    formOpen.value = false
    load()
  } catch (err) { ElMessage.error(translateError(extractErrorCode(err))) }
}

async function onDeactivate(row: ClassDefinition) {
  try { await ElMessageBox.confirm(`停用课程"${row.name}"？`, '提示', { type: 'warning' }) } catch { return }
  try { await deactivateClass(row.id); ElMessage.success('已停用'); load() }
  catch (err) { ElMessage.error(translateError(extractErrorCode(err))) }
}
async function onReactivate(row: ClassDefinition) {
  try { await updateClass(row.id, { is_active: true }); ElMessage.success('已启用'); load() }
  catch (err) { ElMessage.error(translateError(extractErrorCode(err))) }
}
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="toolbar">
        <div class="filters">
          <el-input v-model="query.q" placeholder="课程名搜索" clearable style="width: 200px" @keyup.enter="onSearch" />
          <el-checkbox v-model="query.include_inactive" @change="onSearch">显示已停用</el-checkbox>
          <el-button type="primary" @click="onSearch">搜索</el-button>
        </div>
        <el-button type="success" @click="openCreate">新建课程</el-button>
      </div>
    </template>

    <el-table v-loading="loading" :data="rows" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="name" label="课程名" width="160" />
      <el-table-column prop="coach_name" label="主教练" width="120" />
      <el-table-column prop="capacity" label="容量" width="90" />
      <el-table-column label="时长" width="100">
        <template #default="{ row }">{{ row.duration_minutes }} 分钟</template>
      </el-table-column>
      <el-table-column prop="description" label="简介" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.is_active" type="success">启用</el-tag>
          <el-tag v-else type="info">停用</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" fixed="right" width="160">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="row.is_active" link type="danger" @click="onDeactivate(row)">停用</el-button>
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

  <el-dialog v-model="formOpen" :title="editing ? '编辑课程' : '新建课程'" width="500px">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="92px">
      <el-form-item label="课程名" prop="name"><el-input v-model="form.name" /></el-form-item>
      <el-form-item label="主教练">
        <el-select v-model="form.coach_id" placeholder="可选" clearable style="width: 100%">
          <el-option v-for="c in coachOptions" :key="c.id" :label="c.name" :value="c.id" :disabled="!c.is_active" />
        </el-select>
      </el-form-item>
      <el-form-item label="容量" prop="capacity">
        <el-input-number v-model="form.capacity" :min="1" :max="500" controls-position="right" />
      </el-form-item>
      <el-form-item label="时长" prop="duration_minutes">
        <el-input-number v-model="form.duration_minutes" :min="10" :max="480" :step="10" controls-position="right" />
        <span style="margin-left: 8px; color: #909399">分钟</span>
      </el-form-item>
      <el-form-item label="简介"><el-input v-model="form.description" type="textarea" :rows="3" /></el-form-item>
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
