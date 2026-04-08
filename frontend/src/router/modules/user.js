export default [
  {
    path: '/app',
    component: () => import('@/layouts/UserLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/app/home' },
      { path: 'home', name: 'UserHome', component: () => import('@/views/Home.vue'), meta: { moduleKey: 'home' } },
      { path: 'indexing', name: 'Indexing', component: () => import('@/views/IndexingPage.vue'), meta: { moduleKey: 'indexing' } },
      { path: 'results', name: 'Results', component: () => import('@/views/ResultsPage.vue'), meta: { moduleKey: 'results' } },
      { path: 'peak-extraction', name: 'PeakExtraction', component: () => import('@/views/PeakExtractionPage.vue'), meta: { moduleKey: 'peakExtraction' } },
    ]
  }
]
