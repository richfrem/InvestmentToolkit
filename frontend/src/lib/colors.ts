export function getPillarColor(pillarCode: string): string {
  const colorMap: { [key: string]: string } = {
    'ASI_COMPUTE': '#2563EB', // blue-600
    'CASH': '#059669', // emerald-600
    'POWER_ENERGY': '#D97706', // amber-600
    'DATA_INFRA_SUPPLY_CHAIN': '#7C3AED', // violet-600
    'AI_TITANS_CLOUD': '#DC2626', // red-600
    'SOVEREIGN_FINANCE_DIGITAL_ASSETS': '#0891B2', // cyan-600
    'SECURITY_DATA_OS': '#65A30D', // lime-600
    'APPLIED_AI_ROBOTICS': '#475569', // slate-600
    'OTHER': '#9CA3AF', // gray-400
  };
  return colorMap[pillarCode] || colorMap['OTHER'];
}
