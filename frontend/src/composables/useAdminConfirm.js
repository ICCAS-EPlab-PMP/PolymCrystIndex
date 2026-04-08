import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

export function useAdminConfirm() {
  const { t } = useI18n()

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

  return {
    confirmState,
    alertDialog,
    showConfirm,
    showAlert,
    handleConfirmConfirm,
    handleConfirmCancel,
    ConfirmDialog,
  }
}
