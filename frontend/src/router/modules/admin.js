export default [
  {
    path: '/admin',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
    children: [
      { path: '', name: 'AdminOverview', component: () => import('@/views/AdminPage.vue') },
      { path: 'users', name: 'AdminUsers', component: () => import('@/views/admin/Users.vue') },
      { path: 'tasks', name: 'AdminTasks', component: () => import('@/views/admin/Tasks.vue') },
      { path: 'system', name: 'AdminSystemStatus', component: () => import('@/views/admin/SystemStatus.vue') },
    ]
  }
]
