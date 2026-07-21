export function formatAppVersion(version: string) {
  const calendar = version.match(/^(\d+\.\d+\.\d+)-(\d+)\.(\d+)$/);
  return calendar ? `${calendar[1]}.${calendar[2]}-${calendar[3]}` : version;
}
