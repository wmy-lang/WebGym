<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  listCardTypes,
  createCardType,
  updateCardType,
  deactivateCardType,
  type CardType,
  type CardTypeCreatePayload,
} from '@/api/cardTypes'
import { translateError, extractErrorCode } from '@/utils/errors'

const loading = ref(false)
const rows = ref<CardType[]>([])
const total = ref(0)
const query = reactive({ page: 1, per_page: 20 })

async function load() {
  loading.value = true
  try {
    const { items, meta } = await listCardTypes(query)
    rows.value = items
    total.value = meta.total
  } catch (err) {
    ElMessage.error(translateError(extractErrorCode(err)))
  } finally { loading.value = false }
}
onMounted(load)

const formOpen = ref(false)
const editing = ref<CardType | null>(null)
const form = reactive<CardTypeCreatePayload & { is_active?: boolean }>({
  name: '', duration_days: null, total_visits: null, price: '0.00',
})
const formRef = ref<FormInstance>()
const rules: FormRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  price: [{ required: true, message: '请输入价格', trigger: 'blur' }],
}

function openCreate() {
  editing.value = null
  Object.assign(form, { name: '', duration_days: null, total_visits: null, price: '0.00', is_active: true })
  formOpen.value = true
}
function openEdit(row: CardType) {
  editing.value = row
  Object.assign(form, {
    name: row.name,
    duration_days: row.duration_days,
    total_visits: row.total_visits,
    price: row.price,
    is_active: row.is_active,
  })
  formOpen.value = true
}

async function submit() {
  if (!formRef.value) return
  const ok = await formRef.value.validate().catch(() => false)
  if (!ok) return
  if (!form.duration_days && !form.total_visits) {
    ElMessage.error('期限天数与次数至少填一项')
    return
  }
  try {
    if (editing.value) {
      await updateCardType(editing.value.id, {
        name: form.name,
        duration_days: form.duration_days,
        total_visits: form.total_visits,
        price: form.price,
        is_active: form.is_active,
      })
    } else {
      await createCardType({
        name: form.name,
        duration_days: form.duration_days || null,
        total_visits: form.total_visits || null,
        price: form.price,
      })
    }
    ElMessage.success('已保存')
    formOpen.value = false
    load()
  } catch (err) { ElMessage.error(translateError(extractErrorCode(err))) }
}

async function onDeactivate(row: CardType) {
  try { await ElMessageBox.confirm(`停用卡类型"${row.name}"？`, '提示', { type: 'warning' }) } catch { return }
  try {
    await deactivateCardType(row.id)
    ElMessage.success('已停用')
    load()
  } catch (err) { ElMessage.error(translateError(extractErrorCode(err))) }
}
async function onReactivate(row: CardType) {
  try {
    await updateCardType(row.id, { is_active: true })
    ElMessage.success('已启用')
    load()
  } catch (err) { ElMessage.error(translateError(extractErrorCode(err))) }
}
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="toolbar">
        <span class="title">卡类型字典</span>
        <el-button type="success" @click="openCreate">新建卡类型</el-button>
      </div>
    </template>

    <el-table v-loading="loading" :data="rows" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="name" label="名称" width="160" />
      <el-table-column label="维度">
        <template #default="{ row }">
          <el-tag v-if="row.duration_days" type="primary" effect="plain">期限：{{ row.duration_days }} 天</el-tag>
          <el-tag v-if="row.total_visits" type="warning" effect="plain" style="margin-left: 6px">
            次数：{{ row.total_visits }} 次
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="price" label="价格(元)" width="120" />
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
        background layout="total, prev, pager, next" :total="total"
        v-model:current-page="query.page" v-model:page-size="query.per_page"
        @current-change="load"
      />
    </div>
  </el-card>

  <el-dialog v-model="formOpen" :title="editing ? '编辑卡类型' : '新建卡类型'" width="460px">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="92px">
      <el-form-item label="名称" prop="name"><el-input v-model="form.name" placeholder="如：年卡 / 10 次卡" /></el-form-item>
      <el-form-item label="期限天数">
        <el-input-number v-model="form.duration_days" :min="1" :max="3650" controls-position="right" style="width: 100%" />
        <div class="hint">期限卡填这里（与"次数"二选一或都填）</div>
      </el-form-item>
      <el-form-item label="次数">
        <el-input-number v-model="form.total_visits" :min="1" :max="1000" controls-position="right" style="width: 100%" />
        <div class="hint">次卡填这里</div>
      </el-form-item>
      <el-form-item label="价格" prop="price">
        <el-input v-model="form.price" placeholder="如 1888.00" />
      </el-form-item>
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
.title { font-size: 16px; font-weight: 500; }
.hint { color: #909399; font-size: 12px; margin-top: 4px; }
.pager { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
