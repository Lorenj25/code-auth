/** The database stores UTC timestamps; older API versions omitted the timezone. */
export function utcTimestamp(value: string): string {
  const input = value.trim();
  // ISO timestamps without an offset came from naive UTC database columns.
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?$/.test(input)) {
    return `${input}Z`;
  }
  return input;
}

/** Uniform Philippine time display regardless of browser/device timezone. */
export function formatPhilippineTime(value: string): string {
  const date = new Date(utcTimestamp(value));
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleTimeString('en-PH', {
    timeZone: 'Asia/Manila', hour: '2-digit', minute: '2-digit', hour12: true,
  });
}

export function formatPhilippineDateTime(value: string): string {
  const date = new Date(utcTimestamp(value));
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString('en-PH', {
    timeZone: 'Asia/Manila', year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: true,
  });
}
