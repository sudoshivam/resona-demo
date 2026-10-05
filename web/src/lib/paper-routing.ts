export function normalizePaperRouteId(id: string): string {
  const match = id.match(/^https?:\/\/openalex\.org\/(W\d+)$/i);
  return match ? match[1].toUpperCase() : id;
}

export function paperDetailHref(id: string): string {
  return `/paper/${encodeURIComponent(normalizePaperRouteId(id))}`;
}
