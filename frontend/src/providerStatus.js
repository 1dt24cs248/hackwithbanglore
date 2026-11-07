export function hindsightBankLabel(health) {
  const bankId = health?.dependencies?.hindsight?.bank_id
  return typeof bankId === 'string' && bankId.trim()
    ? `${bankId.trim()} bank`
    : 'Hindsight bank unavailable'
}
