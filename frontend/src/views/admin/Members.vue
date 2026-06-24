<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  listMembers,
  createMember,
  updateMember,
  deactivateMember,
  type Member,
  type MemberCreatePayload,
  type MemberUpdatePayload,
  type Gender,
} from '@/api/members'
import { translateError, extractErrorCode } from '@/utils/errors'
import { formatDateTime, formatDate } from '@/utils/format'

const loading = ref(false)
const rows = ref<Member[]>([])
const total = ref(0)
const query = reactive({ page: 1, per_page: 20, q: '', include_inactive: false })

async function load() {
  loading.value = true
  try {
    const { items, meta } = await listMembers(query)
    rows.value = items
    total.value = meta.total
  } catch (err) {
    ElMessage.error(translateError(extractErrorCode(err)))
  } finally {
    loading.value = false
  }
}

onMounted(load)

function onSearch() {
  query.page = 1
  load()
}

// ---------- 创建 ----------
const createOpen = ref(false)
const createForm = reactive<MemberCreatePayload & { gender: Gender | null; birthday: string | null }>({
  username: '',
  password: '',
  real_name: '',
  phone: '',
  gender: null,
  birthday: null,
  id_card: '',
  emergency_contact: '',
  note: '',
})
const createRef = ref<FormInstance>()
const createRules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }, { min: 3, max: 64, message: '3-64 个字符', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }, { min: 6, max: 128, message: '6-128 个字符', trigger: 'blur' }],
  real_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  phone: [{ required: true, message: '请输入手机号', trigger: 'blur' }],
}

function openCreate() {
  Object.assign(createForm, {
    username: '', password: '', real_name: '', phone: '',
    gender: null, birthday: null, id_card: '', emergency_contact: '', note: '',
  })
  createOpen.value = true
}

async function submitCreate() {
  if (!createRef.value) return
  const ok = await createRef.value.validate().catch(() => false)
  if (!ok) return
  try {
    const payload: MemberCreatePayload = {
      username: createForm.username.trim(),
      password: createForm.password,
      real_name: createForm.real_name.trim(),
      phone: createForm.phone.trim(),
      gender: createForm.gender || null,
      birthday: createForm.birthday || null,
      id_card: createForm.id_card || null,
      emergency_contact: createForm.emergency_contact || null,
      note: createForm.note || null,
    }
    await createMember(payload)
    ElMessage.success('创建成功')
    createOpen.value = false
    load()
  } catch (err) {
    ElMessage.error(translateError(extractErrorCode(err)))
  }
}

// ---------- 编辑 ----------
const editOpen = ref(false)
const editing = ref<Member | null>(null)
const editForm = reactive<MemberUpdatePayload>({})

function openEdit(row: Member) {
  editing.value = row
  Object.assign(editForm, {
    real_name: row.real_name || '',
    phone: row.phone || '',
    gender: row.gender,
    birthday: row.birthday,
    emergency_contact: row.emergency_contact || '',
    note: row.note || '',
    is_active: row.is_active,
  })
  editOpen.value = true
}

async function submitEdit() {
  if (!editing.value) return
  try {
    await updateMember(editing.value.id, editForm)
    ElMessage.success('保存成功')
    editOpen.value = false
    load()
  } catch (err) {
    ElMessage.error(translateError(extractErrorCode(err)))
  }
}

// ---------- 禁用 ----------
async function onDeactivate(row: Member) {
  try {
    await ElMessageBox.confirm(`确定要禁用会员"${row.real_name || row.username}"吗？`, '提示', {
      type: 'warning',
    })
  } catch { return }
  try {
    await deactivateMember(row.id)
    ElMessage.success('已禁用')
    load()
  } catch (err) {
    ElMessage.error(translateError(extractErrorCode(err)))
  }
}

async function onReactivate(row: Member) {
  try {
    await updateMember(row.id, { is_active: true })
    ElMessage.success('已启用')
    load()
  } catch (err) {
    ElMessage.error(translateError(extractErrorCode(err)))
  }
}

const genderLabel = computed(() => (g: Gender | null) => {
  if (g === 'male') return '男'
  if (g === 'female') return '女'
  if (g === 'other') return '其他'
  return '—'
})
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="toolbar">
        <div class="filters">
          <el-input
            v-model="query.q"
            placeholder="用户名 / 姓名 / 手机号"
            clearable
            style="width: 240px"
            @keyup.enter="onSearch"
          />
          <el-checkbox v-model="query.include_inactive" @change="onSearch">显示已禁用</el-checkbox>
          <el-button type="primary" @click="onSearch">搜索</el-button>
        </div>
        <el-button type="success" @click="openCreate">新建会员</el-button>
      </div>
    </template>

    <el-table v-loading="loading" :data="rows" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="username" label="用户名" width="140" />
      <el-table-column prop="real_name" label="姓名" width="120" />
      <el-table-column prop="phone" label="手机号" width="140" />
      <el-table-column label="性别" width="80">
        <template #default="{ row }">{{ genderLabel(row.gender) }}</template>
      </el-table-column>
      <el-table-column label="生日" width="120">
        <template #default="{ row }">{{ formatDate(row.birthday) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.is_active" type="success">启用</el-tag>
          <el-tag v-else type="info">禁用</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="160">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" fixed="right" width="180">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="row.is_active" link type="danger" @click="onDeactivate(row)">禁用</el-button>
          <el-button v-else link type="success" @click="onReactivate(row)">启用</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pager">
      <el-pagination
        background
        layout="total, prev, pager, next, sizes"
        :total="total"
        v-model:current-page="query.page"
        v-model:page-size="query.per_page"
        :page-sizes="[10, 20, 50, 100]"
        @current-change="load"
        @size-change="load"
      />
    </div>
  </el-card>

  <!-- 创建 -->
  <el-dialog v-model="createOpen" title="新建会员" width="540px">
    <el-form ref="createRef" :model="createForm" :rules="createRules" label-width="92px">
      <el-form-item label="用户名" prop="username"><el-input v-model="createForm.username" /></el-form-item>
      <el-form-item label="密码" prop="password"><el-input v-model="createForm.password" type="password" show-password /></el-form-item>
      <el-form-item label="姓名" prop="real_name"><el-input v-model="createForm.real_name" /></el-form-item>
      <el-form-item label="手机号" prop="phone"><el-input v-model="createForm.phone" /></el-form-item>
      <el-form-item label="性别">
        <el-select v-model="createForm.gender" placeholder="—" clearable style="width: 100%">
          <el-option label="男" value="male" />
          <el-option label="女" value="female" />
          <el-option label="其他" value="other" />
        </el-select>
      </el-form-item>
      <el-form-item label="生日">
        <el-date-picker v-model="createForm.birthday" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
      </el-form-item>
      <el-form-item label="身份证号">
        <el-input v-model="createForm.id_card" placeholder="可选，入库加密存储" />
      </el-form-item>
      <el-form-item label="紧急联系人">
        <el-input v-model="createForm.emergency_contact" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="createForm.note" type="textarea" :rows="2" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="createOpen = false">取消</el-button>
      <el-button type="primary" @click="submitCreate">保存</el-button>
    </template>
  </el-dialog>

  <!-- 编辑 -->
  <el-dialog v-model="editOpen" title="编辑会员" width="540px">
    <el-form :model="editForm" label-width="92px">
      <el-form-item label="姓名"><el-input v-model="editForm.real_name" /></el-form-item>
      <el-form-item label="手机号"><el-input v-model="editForm.phone" /></el-form-item>
      <el-form-item label="性别">
        <el-select v-model="editForm.gender" placeholder="—" clearable style="width: 100%">
          <el-option label="男" value="male" />
          <el-option label="女" value="female" />
          <el-option label="其他" value="other" />
        </el-select>
      </el-form-item>
      <el-form-item label="生日">
        <el-date-picker v-model="editForm.birthday" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
      </el-form-item>
      <el-form-item label="紧急联系人"><el-input v-model="editForm.emergency_contact" /></el-form-item>
      <el-form-item label="备注"><el-input v-model="editForm.note" type="textarea" :rows="2" /></el-form-item>
      <el-form-item label="状态"><el-switch v-model="editForm.is_active" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="editOpen = false">取消</el-button>
      <el-button type="primary" @click="submitEdit">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; }
.filters { display: flex; gap: 12px; align-items: center; }
.pager { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
