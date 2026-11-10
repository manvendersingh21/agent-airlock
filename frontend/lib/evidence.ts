export interface EvidenceSpan { start: number; end: number; label: string }
export interface EvidencePart { text: string; highlighted: boolean; label?: string }

/** Offsets are API-reported code points. Never search for or repair evidence spans. */
export function verifiedSpans(text: string, evidence: Record<string, unknown>[]): EvidenceSpan[] {
  const points = Array.from(text);
  return evidence.flatMap((item) => {
    const { start, end } = item;
    if (typeof start !== 'number' || typeof end !== 'number' || !Number.isInteger(start) || !Number.isInteger(end)
      || start < 0 || end <= start || end > points.length) return [];
    const quote = item.quote ?? item.value ?? item.line;
    // A detector can report inconsistent offsets. Keep those only in the raw evidence view.
    if (typeof quote === 'string' && points.slice(start, end).join('') !== quote) return [];
    return [{ start, end, label: typeof item.type === 'string' ? item.type : 'Clocked evidence' }];
  }).sort((a, b) => a.start - b.start);
}

export function evidenceParts(text: string, evidence: Record<string, unknown>[]): EvidencePart[] {
  const points = Array.from(text);
  const spans = verifiedSpans(text, evidence);
  const merged: EvidenceSpan[] = [];
  for (const span of spans) {
    const previous = merged[merged.length - 1];
    if (previous && span.start <= previous.end) previous.end = Math.max(previous.end, span.end);
    else merged.push({ ...span });
  }
  const parts: EvidencePart[] = [];
  let cursor = 0;
  for (const span of merged) {
    if (cursor < span.start) parts.push({ text: points.slice(cursor, span.start).join(''), highlighted: false });
    parts.push({ text: points.slice(span.start, span.end).join(''), highlighted: true, label: span.label });
    cursor = span.end;
  }
  if (cursor < points.length) parts.push({ text: points.slice(cursor).join(''), highlighted: false });
  return parts;
}
