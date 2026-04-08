<template>
  <div class="users-page">
    <div class="page-header">
      <div class="header-content">
        <h1>{{ t('admin.users') }}</h1>
        <p class="description">{{ t('admin.usersDesc') }}</p>
      </div>
      <div class="header-actions">
        <button class="btn-secondary" @click="loadUsers" :disabled="loading">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M23 4v6h-6M1 20v-6h6"/>
            <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
          </svg>
          {{ t('common.refresh') }}
        </button>
        <button class="btn-primary" @click="showCreateDialog = true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          {{ t('admin.createUser') }}
        </button>
      </div>
    </div>

    <div class="filters" v-if="users.length > 0">
      <div class="filter-group">
        <div class="search-input-wrapper">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="search-icon">
            <circle cx="11" cy="11" r="8"/>
            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input
            type="text"
            v-model="searchQuery"
            :placeholder="t('admin.searchPlaceholder')"
            class="search-input"
          />
        </div>
      </div>
      <div class="filter-group">
        <select v-model="filterRole">
          <option value="">{{ t('admin.allRoles') }}</option>
          <option value="admin">{{ t('common.admin') }}</option>
          <option value="user">{{ t('common.user') }}</option>
        </select>
      </div>
      <div class="filter-group">
        <select v-model="filterStatus">
          <option value="">{{ t('admin.allStatuses_filter') }}</option>
          <option value="active">{{ t('admin.activeStatus') }}</option>
          <option value="disabled">{{ t('admin.disabledStatus') }}</option>
        </select>
      </div>
      <button v-if="searchQuery || filterRole || filterStatus" class="btn-filter-reset" @click="resetFilters">
        {{ t('admin.resetFilters') }}
      </button>
    </div>

    <div v-if="loading && users.length === 0" class="loading-state">
      <div class="spinner"></div>
      <p>{{ t('common.loading') }}</p>
    </div>

    <div v-else-if="error && !users.length" class="error-state">
      <p>{{ error }}</p>
      <button class="btn-secondary" @click="loadUsers">{{ t('common.retry') }}</button>
    </div>

    <div v-if="error && users.length" class="error-banner">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
        <circle cx="12" cy="12" r="10"/>
        <line x1="15" y1="9" x2="9" y2="15"/>
        <line x1="9" y1="9" x2="15" y2="15"/>
      </svg>
      <span>{{ error }}</span>
      <button class="banner-dismiss" @click="error = ''">&times;</button>
    </div>

    <div v-if="users.length === 0 && !loading && !error" class="empty-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
        <circle cx="9" cy="7" r="4"/>
      </svg>
      <p>{{ t('admin.noUsers') }}</p>
    </div>

    <div v-else-if="filteredUsers.length === 0 && users.length > 0" class="empty-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="11" cy="11" r="8"/>
        <line x1="21" y1="21" x2="16.65" y2="16.65"/>
      </svg>
      <p>{{ t('admin.noFilteredUsers') }}</p>
    </div>

    <div v-else-if="users.length > 0" class="users-table-container">
      <table class="users-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>{{ t('admin.username') }}</th>
            <th>{{ t('admin.displayName') }}</th>
            <th>{{ t('admin.userSource') }}</th>
            <th>{{ t('admin.role') }}</th>
            <th>{{ t('admin.approvalStatus') }}</th>
            <th>{{ t('admin.quotaSummary') }}</th>
            <th>{{ t('admin.status') }}</th>
            <th>{{ t('admin.createdAt') }}</th>
            <th class="cell-actions-header">{{ t('admin.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in filteredUsers" :key="user.id">
            <td class="cell-id">{{ user.id }}</td>
            <td class="cell-username">{{ user.username }}</td>
            <td>{{ user.displayName }}</td>
            <td>
              <div>{{ user.school || '-' }}</div>
              <div class="cell-subtext">{{ user.organization || '-' }}</div>
            </td>
            <td>
              <span :class="['badge', `badge-${user.role}`]">{{ user.role }}</span>
            </td>
            <td>
              <span :class="['badge', user.isApproved ? 'badge-active' : 'badge-pending']">
                {{ user.isApproved ? t('admin.approved') : t('admin.pendingApproval') }}
              </span>
            </td>
            <td>
              <div>{{ formatQuota(user) }}</div>
              <div class="cell-subtext">{{ t('admin.maxThreadsShort') }} {{ user.effectiveMaxThreads }}</div>
            </td>
            <td>
              <span :class="['badge', user.isActive ? 'badge-active' : 'badge-inactive']">
                {{ user.isActive ? t('common.active') : t('admin.disabled') }}
              </span>
            </td>
            <td class="cell-date">{{ formatDate(user.createdAt) }}</td>
            <td class="cell-actions">
              <div class="cell-actions-inner">
                <button
                  class="btn-action btn-edit"
                  @click="editUser(user)"
                  :title="t('admin.editUser')"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                    <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
                    <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
                  </svg>
                </button>
                <button
                  class="btn-action btn-reset"
                  @click="openResetDialog(user)"
                  :title="t('admin.resetPassword')"
                  :disabled="isCurrentUser(user)"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                    <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 11-7.778 7.778 5.5 5.5 0 017.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>
                  </svg>
                </button>
                <button
                  v-if="user.isActive"
                  class="btn-action btn-disable"
                  @click="disableUser(user)"
                  :disabled="actionLoading === user.id"
                >
                  {{ t('admin.disable') }}
                </button>
                <button
                  v-else
                  class="btn-action btn-enable"
                  @click="enableUser(user)"
                  :disabled="actionLoading === user.id"
                >
                  {{ t('admin.enable') }}
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showCreateDialog" class="dialog-overlay" @click.self="showCreateDialog = false">
      <div class="dialog">
        <div class="dialog-header">
          <h3>{{ t('admin.createUser') }}</h3>
          <button class="btn-close" @click="showCreateDialog = false">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        <div class="dialog-body">
          <div class="form-group">
            <label>{{ t('admin.username') }} *</label>
            <input
              type="text"
              v-model="createForm.username"
              :placeholder="t('admin.usernamePlaceholder')"
            />
          </div>
          <div class="form-group">
            <label>{{ t('admin.password') }} *</label>
            <input
              type="password"
              v-model="createForm.password"
              :placeholder="t('admin.passwordPlaceholder')"
            />
          </div>
          <div class="form-group">
            <label>{{ t('admin.displayName') }}</label>
            <input
              type="text"
              v-model="createForm.displayName"
              :placeholder="t('admin.displayNamePlaceholder')"
            />
          </div>
          <div class="form-group">
            <label>{{ t('admin.school') }}</label>
            <input type="text" v-model="createForm.school" :placeholder="t('admin.schoolPlaceholder')" />
          </div>
          <div class="form-group">
            <label>{{ t('admin.organization') }}</label>
            <input type="text" v-model="createForm.organization" :placeholder="t('admin.organizationPlaceholder')" />
          </div>
          <div class="form-group">
            <label>{{ t('admin.role') }}</label>
            <select v-model="createForm.role">
              <option value="user">{{ t('common.user') }}</option>
              <option value="admin">{{ t('common.admin') }}</option>
            </select>
          </div>
          <div class="form-group form-group-toggle">
            <label>{{ t('admin.approvalStatus') }}</label>
            <FormToggle
              v-model="createForm.isApproved"
              tone="primary"
              :on-text="t('admin.approved')"
              :off-text="t('admin.pendingApproval')"
            />
            <span class="form-hint">{{ t('admin.approvalStatusHint') }}</span>
          </div>
          <div class="form-group">
            <label>{{ t('admin.runLimitOverride') }}</label>
            <input type="number" min="0" v-model.number="createForm.runLimitOverride" :placeholder="t('admin.zeroMeansUnlimited')" />
            <span class="form-hint">{{ t('admin.runLimitOverrideHint') }}</span>
          </div>
          <div class="form-group">
            <label>{{ t('admin.maxThreadsOverride') }}</label>
            <input type="number" min="1" v-model.number="createForm.maxThreadsOverride" :placeholder="t('admin.leaveEmptyForDefault')" />
            <span class="form-hint">{{ t('admin.maxThreadsOverrideHint') }}</span>
          </div>
          <div v-if="createError" class="form-error">{{ createError }}</div>
        </div>
        <div class="dialog-footer">
          <button class="btn-secondary" @click="showCreateDialog = false">
            {{ t('admin.cancel_action') }}
          </button>
          <button class="btn-primary" @click="createUser" :disabled="createLoading">
            {{ createLoading ? t('common.loading') : t('common.confirm') }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showEditDialog" class="dialog-overlay" @click.self="showEditDialog = false">
      <div class="dialog">
        <div class="dialog-header">
          <h3>{{ t('admin.editUser') }}</h3>
          <button class="btn-close" @click="showEditDialog = false">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        <div class="dialog-body">
          <div class="form-group">
            <label>{{ t('admin.displayName') }}</label>
            <input type="text" v-model="editForm.displayName" />
          </div>
          <div class="form-group">
            <label>{{ t('admin.school') }}</label>
            <input type="text" v-model="editForm.school" />
          </div>
          <div class="form-group">
            <label>{{ t('admin.organization') }}</label>
            <input type="text" v-model="editForm.organization" />
          </div>
          <div class="form-group">
            <label>{{ t('admin.role') }}</label>
            <select v-model="editForm.role" :disabled="editIsSelf">
              <option value="user">{{ t('common.user') }}</option>
              <option value="admin">{{ t('common.admin') }}</option>
            </select>
            <span v-if="editIsSelf" class="form-hint">{{ t('admin.cannotChangeOwnRole') }}</span>
          </div>
          <div class="form-group form-group-toggle">
            <label>{{ t('admin.status') }}</label>
            <FormToggle
              v-model="editForm.isActive"
              tone="success"
              :disabled="editIsSelf"
              :on-text="t('admin.activeStatus')"
              :off-text="t('admin.disabledStatus')"
            />
            <span class="form-hint">{{ t('admin.statusHint') }}</span>
            <span v-if="editIsSelf" class="form-hint">{{ t('admin.cannotDisableSelf') }}</span>
          </div>
          <div class="form-group form-group-toggle">
            <label>{{ t('admin.approvalStatus') }}</label>
            <FormToggle
              v-model="editForm.isApproved"
              tone="primary"
              :on-text="t('admin.approved')"
              :off-text="t('admin.pendingApproval')"
            />
            <span class="form-hint">{{ t('admin.approvalStatusHint') }}</span>
          </div>
          <div class="form-group">
            <label>{{ t('admin.runLimitOverride') }}</label>
            <input type="number" min="0" v-model.number="editForm.runLimitOverride" :placeholder="t('admin.zeroMeansUnlimited')" />
            <span class="form-hint">{{ t('admin.runLimitOverrideHint') }}</span>
            <span class="form-hint">{{ t('admin.userRunCountHint', { count: editForm.runCount || 0 }) }}</span>
          </div>
          <div class="form-group">
            <label>{{ t('admin.maxThreadsOverride') }}</label>
            <input type="number" min="1" v-model.number="editForm.maxThreadsOverride" :placeholder="t('admin.leaveEmptyForDefault')" />
            <span class="form-hint">{{ t('admin.maxThreadsOverrideHint') }}</span>
          </div>
          <div v-if="editError" class="form-error">{{ editError }}</div>
        </div>
        <div class="dialog-footer">
          <button class="btn-secondary" @click="showEditDialog = false">
            {{ t('admin.cancel_action') }}
          </button>
          <button class="btn-primary" @click="saveEditUser" :disabled="editLoading">
            {{ editLoading ? t('common.loading') : t('admin.save') }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showResetDialog" class="dialog-overlay" @click.self="showResetDialog = false">
      <div class="dialog">
        <div class="dialog-header">
          <h3>{{ t('admin.resetPassword') }}</h3>
          <button class="btn-close" @click="showResetDialog = false">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        <div class="dialog-body">
          <p class="reset-target-info">{{ resetTarget?.displayName || resetTarget?.username }} ({{ resetTarget?.role }})</p>
          <div class="form-group">
            <label>{{ t('admin.newPassword') }}</label>
            <input type="password" v-model="newPassword" :placeholder="t('admin.newPassword')" />
          </div>
          <div class="form-group">
            <label>{{ t('admin.confirmPassword') }}</label>
            <input type="password" v-model="confirmPassword" :placeholder="t('admin.confirmPassword')" />
          </div>
          <div class="form-warning">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
              <line x1="12" y1="9" x2="12" y2="13"/>
              <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            {{ t('admin.resetPasswordWarning') }}
          </div>
          <div v-if="resetError" class="form-error">{{ resetError }}</div>
        </div>
        <div class="dialog-footer">
          <button class="btn-secondary" @click="showResetDialog = false">
            {{ t('admin.cancel_action') }}
          </button>
          <button class="btn-primary" @click="resetPassword" :disabled="resetLoading">
            {{ resetLoading ? t('common.loading') : t('admin.confirmReset') }}
          </button>
        </div>
      </div>
    </div>

    <ConfirmDialog
      :visible="confirmState.visible"
      :title="confirmState.title"
      :message="confirmState.message"
      :confirmText="confirmState.confirmText"
      :cancelText="confirmState.cancelText"
      :type="confirmState.type"
      @confirm="handleConfirmConfirm"
      @cancel="handleConfirmCancel"
    />

    <ConfirmDialog
      :visible="alertDialog.visible"
      :title="alertDialog.title"
      :message="alertDialog.message"
      :confirmText="t('common.close')"
      :cancelText="''"
      type="info"
      @confirm="alertDialog.visible = false"
      @cancel="alertDialog.visible = false"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import adminService from '@/services/admin'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import FormToggle from '@/components/FormToggle.vue'

const { t } = useI18n()
const authStore = useAuthStore()

const confirmState = ref({
  visible: false,
  title: '',
  message: '',
  confirmText: '',
  cancelText: '',
  type: 'info',
  onConfirm: null,
})

const alertDialog = ref({
  visible: false,
  title: '',
  message: '',
})

const showConfirm = (opts) => {
  return new Promise((resolve) => {
    confirmState.value = {
      visible: true,
      title: opts.title || '',
      message: opts.message || '',
      confirmText: opts.confirmText || t('common.confirm'),
      cancelText: opts.cancelText || t('admin.cancel_action'),
      type: opts.type || 'info',
      onConfirm: () => { resolve(true) },
      onCancel: () => { resolve(false) },
    }
  })
}

const handleConfirmConfirm = () => {
  confirmState.value.visible = false
  confirmState.value.onConfirm?.()
}

const handleConfirmCancel = () => {
  confirmState.value.visible = false
  confirmState.value.onCancel?.()
}

const showAlert = (opts) => {
  alertDialog.value = {
    visible: true,
    title: opts.title || '',
    message: opts.message || '',
  }
}

const users = ref([])
const loading = ref(false)
const error = ref('')
const actionLoading = ref(null)
const showCreateDialog = ref(false)
const createLoading = ref(false)
const createError = ref('')

const searchQuery = ref('')
const filterRole = ref('')
const filterStatus = ref('')

const showEditDialog = ref(false)
const editForm = ref({
  id: null,
  displayName: '',
  school: '',
  organization: '',
  role: 'user',
  isActive: true,
  isApproved: false,
  runCount: 0,
  runLimitOverride: null,
  maxThreadsOverride: null,
})
const editLoading = ref(false)
const editError = ref('')
const editIsSelf = computed(() => {
  const currentId = authStore.getUser()?.id
  return currentId != null && editForm.value.id === currentId
})

const isCurrentUser = (user) => {
  const currentId = authStore.getUser()?.id
  return currentId != null && user.id === currentId
}

const showResetDialog = ref(false)
const resetTarget = ref(null)
const newPassword = ref('')
const confirmPassword = ref('')
const resetLoading = ref(false)
const resetError = ref('')

const createForm = reactive({
  username: '',
  password: '',
  displayName: '',
  school: '',
  organization: '',
  role: 'user',
  isApproved: false,
  runLimitOverride: null,
  maxThreadsOverride: null,
})

const filteredUsers = computed(() => {
  return users.value.filter(u => {
    const matchSearch = !searchQuery.value ||
      u.username.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      (u.displayName && u.displayName.toLowerCase().includes(searchQuery.value.toLowerCase()))
    const matchRole = !filterRole.value || u.role === filterRole.value
    const matchStatus = filterStatus.value === '' ||
      (filterStatus.value === 'active' && u.isActive) ||
      (filterStatus.value === 'disabled' && !u.isActive)
    return matchSearch && matchRole && matchStatus
  })
})

const resetFilters = () => {
  searchQuery.value = ''
  filterRole.value = ''
  filterStatus.value = ''
}

const loadUsers = async () => {
  loading.value = true
  error.value = ''
  try {
    users.value = await adminService.getAdminUsers()
  } catch (e) {
    error.value = e.message || t('admin.loadUsersError')
  } finally {
    loading.value = false
  }
}

const createUser = async () => {
  if (!createForm.username || !createForm.password) {
    createError.value = t('admin.fillRequired')
    return
  }
  createLoading.value = true
  createError.value = ''
  try {
    await adminService.createAdminUser({
      username: createForm.username,
      password: createForm.password,
      displayName: createForm.displayName || createForm.username,
      school: createForm.school,
      organization: createForm.organization,
      role: createForm.role,
      isApproved: createForm.isApproved,
      runLimitOverride: createForm.runLimitOverride,
      maxThreadsOverride: createForm.maxThreadsOverride,
    })
    showCreateDialog.value = false
    Object.assign(createForm, {
      username: '',
      password: '',
      displayName: '',
      school: '',
      organization: '',
      role: 'user',
      isApproved: false,
      runLimitOverride: null,
      maxThreadsOverride: null,
    })
    await loadUsers()
  } catch (e) {
    createError.value = e.message || t('admin.createUserError')
  } finally {
    createLoading.value = false
  }
}

const disableUser = async (user) => {
  const confirmed = await showConfirm({
    title: t('admin.disable'),
    message: t('admin.confirmDisable', { name: user.username }),
    type: 'danger',
  })
  if (!confirmed) return
  actionLoading.value = user.id
  try {
    await adminService.disableAdminUser(user.id)
    await loadUsers()
  } catch (e) {
    error.value = e.message || t('admin.disableUserError')
  } finally {
    actionLoading.value = null
  }
}

const enableUser = async (user) => {
  const confirmed = await showConfirm({
    title: t('admin.enable'),
    message: t('admin.confirmEnable', { name: user.username }),
  })
  if (!confirmed) return
  actionLoading.value = user.id
  try {
    await adminService.enableAdminUser(user.id)
    await loadUsers()
  } catch (e) {
    error.value = e.message || t('admin.enableUserError')
  } finally {
    actionLoading.value = null
  }
}

const editUser = (user) => {
  editForm.value = {
    id: user.id,
    displayName: user.displayName || '',
    school: user.school || '',
    organization: user.organization || '',
    role: user.role,
    isActive: user.isActive,
    isApproved: user.isApproved,
    runCount: user.runCount || 0,
    runLimitOverride: user.runLimitOverride,
    maxThreadsOverride: user.maxThreadsOverride,
  }
  editError.value = ''
  showEditDialog.value = true
}

const saveEditUser = async () => {
  editLoading.value = true
  editError.value = ''
  try {
    await adminService.updateAdminUser(editForm.value.id, {
      role: editForm.value.role,
      displayName: editForm.value.displayName,
      school: editForm.value.school,
      organization: editForm.value.organization,
      isActive: editForm.value.isActive,
      isApproved: editForm.value.isApproved,
      runLimitOverride: editForm.value.runLimitOverride,
      maxThreadsOverride: editForm.value.maxThreadsOverride,
    })
    showEditDialog.value = false
    await loadUsers()
  } catch (e) {
    editError.value = e.message || t('admin.updateUserError')
  } finally {
    editLoading.value = false
  }
}

const openResetDialog = (user) => {
  resetTarget.value = user
  newPassword.value = ''
  confirmPassword.value = ''
  resetError.value = ''
  showResetDialog.value = true
}

const resetPassword = async () => {
  if (!newPassword.value) {
    resetError.value = t('admin.passwordTooShort')
    return
  }
  if (newPassword.value.length < 6) {
    resetError.value = t('admin.passwordTooShort')
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    resetError.value = t('admin.passwordMismatch')
    return
  }
  resetLoading.value = true
  resetError.value = ''
  try {
    await adminService.resetUserPassword(resetTarget.value.id, newPassword.value)
    showResetDialog.value = false
    showAlert({ title: t('admin.resetPassword'), message: t('admin.resetPasswordSuccess') })
  } catch (e) {
    resetError.value = e.message || t('admin.resetPasswordError')
  } finally {
    resetLoading.value = false
  }
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const formatQuota = (user) => {
  if (!user) return '-'
  if (!user.effectiveRunLimit) {
    return `${t('admin.unlimitedRuns')} | ${t('admin.usedRuns', { count: user.runCount || 0 })}`
  }
  return `${user.runCount || 0}/${user.effectiveRunLimit}`
}

onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
.users-page {
  max-width: 1480px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
  gap: 24px;
}

.header-content h1 {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.header-content .description {
  color: var(--text-secondary);
  font-size: 0.9375rem;
}

.header-actions {
  display: flex;
  gap: 12px;
  flex-shrink: 0;
}

.btn-primary, .btn-secondary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: var(--radius-md);
  font-size: 0.9375rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
  border: none;
}

.btn-primary {
  background: var(--primary);
  color: white;
}

.btn-primary:hover {
  background: var(--primary-hover);
}

.btn-secondary {
  background: var(--bg-surface);
  color: var(--text-secondary);
  border: 1px solid var(--border);
}

.btn-secondary:hover {
  background: var(--bg-surface-alt);
  color: var(--text-primary);
}

.btn-secondary:disabled, .btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary svg, .btn-secondary svg {
  width: 18px;
  height: 18px;
}

.filters {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  padding: 16px 20px;
  background: var(--bg-surface);
  border-radius: var(--radius-lg);
  align-items: center;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.filter-group select {
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  background: var(--bg-primary);
  color: var(--text-primary);
  min-width: 140px;
}

.filter-group select:focus {
  outline: none;
  border-color: var(--primary);
}

.search-input-wrapper {
  position: relative;
}

.search-icon {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  width: 16px;
  height: 16px;
  color: var(--text-muted);
  pointer-events: none;
}

.search-input {
  padding: 8px 12px 8px 34px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  background: var(--bg-primary);
  color: var(--text-primary);
  width: 260px;
}

.search-input:focus {
  outline: none;
  border-color: var(--primary);
}

.btn-filter-reset {
  padding: 8px 14px;
  border-radius: var(--radius-md);
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
  border: 1px solid var(--border);
  background: transparent;
  color: var(--text-secondary);
}

.btn-filter-reset:hover {
  background: var(--bg-surface-alt);
  color: var(--text-primary);
}

.loading-state, .empty-state, .error-state {
  text-align: center;
  padding: 64px;
  background: var(--bg-surface);
  border-radius: var(--radius-xl);
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-state svg {
  width: 64px;
  height: 64px;
  color: var(--text-muted);
  margin-bottom: 16px;
}

.error-state {
  color: var(--error);
}

.error-state p {
  margin-bottom: 16px;
}

.error-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: var(--radius-md);
  color: var(--error);
  font-size: 0.875rem;
  margin-bottom: 20px;
}

.banner-dismiss {
  margin-left: auto;
  background: none;
  border: none;
  color: var(--error);
  font-size: 1.25rem;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
}

.btn-secondary {
  background: var(--bg-surface);
  color: var(--text-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  font-size: 0.9375rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.users-table-container {
  background: var(--bg-surface);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-card);
}

.users-table {
  width: 100%;
  border-collapse: collapse;
}

.users-table th {
  text-align: left;
  padding: 16px 20px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  background: var(--bg-surface-alt);
  border-bottom: 1px solid var(--border);
}

.users-table td {
  padding: 16px 20px;
  font-size: 0.9375rem;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border);
  vertical-align: middle;
}

.cell-actions-header {
  text-align: left;
}

.users-table tr:last-child td {
  border-bottom: none;
}

.users-table tr:hover td {
  background: var(--bg-surface-alt);
}

.cell-id {
  font-family: 'Fira Code', monospace;
  color: var(--text-muted);
}

.cell-date {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.cell-subtext {
  margin-top: 4px;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  font-size: 0.75rem;
  font-weight: 600;
}

.badge-admin {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
}

.badge-user {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
}

.badge-active {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
}

.badge-inactive {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.badge-pending {
  background: rgba(234, 179, 8, 0.15);
  color: #d97706;
}

.cell-actions {
  white-space: nowrap;
}

.cell-actions-inner {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 36px;
  flex-wrap: wrap;
}

.btn-action {
  padding: 6px 14px;
  border-radius: var(--radius-sm);
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
  border: 1px solid transparent;
}

.btn-disable {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.2);
}

.btn-disable:hover {
  background: rgba(239, 68, 68, 0.2);
}

.btn-enable {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
  border-color: rgba(16, 185, 129, 0.2);
}

.btn-enable:hover {
  background: rgba(16, 185, 129, 0.2);
}

.btn-edit {
  background: rgba(107, 114, 128, 0.1);
  color: var(--text-secondary);
  border-color: rgba(107, 114, 128, 0.2);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 10px;
}

.btn-edit:hover {
  background: rgba(107, 114, 128, 0.2);
  color: var(--text-primary);
}

.btn-reset {
  background: rgba(234, 179, 8, 0.1);
  color: #eab308;
  border-color: rgba(234, 179, 8, 0.2);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 10px;
}

.btn-reset:hover {
  background: rgba(234, 179, 8, 0.2);
}

.btn-action:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.dialog {
  background: var(--bg-surface);
  border-radius: var(--radius-xl);
  width: 100%;
  max-width: 560px;
  box-shadow: var(--shadow-lg);
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border);
}

.dialog-header h3 {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
}

.btn-close {
  background: none;
  border: none;
  padding: 4px;
  cursor: pointer;
  color: var(--text-muted);
  border-radius: var(--radius-sm);
}

.btn-close:hover {
  background: var(--bg-surface-alt);
  color: var(--text-primary);
}

.btn-close svg {
  width: 20px;
  height: 20px;
}

.dialog-body {
  padding: 24px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.form-group input, .form-group select {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  font-size: 0.9375rem;
  background: var(--bg-primary);
  color: var(--text-primary);
  transition: border-color var(--transition-fast);
}

.form-group input:focus, .form-group select:focus {
  outline: none;
  border-color: var(--primary);
}

.form-group input:disabled, .form-group select:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.form-hint {
  display: block;
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-top: 4px;
}

.form-group-toggle {
  display: flex;
  flex-direction: column;
  gap: 10px;
}


.form-warning {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: rgba(234, 179, 8, 0.1);
  border-radius: var(--radius-md);
  color: #eab308;
  font-size: 0.8125rem;
  margin-bottom: 16px;
}

.form-warning svg {
  flex-shrink: 0;
}

.reset-target-info {
  font-size: 0.9375rem;
  color: var(--text-primary);
  font-weight: 500;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border);
}

.form-error {
  color: var(--error);
  font-size: 0.875rem;
  margin-top: 12px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--border);
  background: var(--bg-surface-alt);
  border-radius: 0 0 var(--radius-xl) var(--radius-xl);
}
</style>
