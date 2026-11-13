export function queryString(filters, page) {
  const params = new URLSearchParams({ page: String(page), limit: '12' })
  for (const [key, value] of Object.entries(filters)) if (value) params.set(key, value)
  return params.toString()
}
