/** 底栏字幕视觉分行：避免「在本机完/成」类断词。 */
const SOFT_BREAK = /[，,、；;]/;
const CLAUSE_END = /[。！？.!?]$/;
const BAD_SUFFIX = /(在|的|和|与|为|将|把|向|从|到|用|是|了|过|着|得|本|改|文)$/;
const BAD_PREFIX = /^(成|行|件|名|完|的|了|吗|什|么|工|具)/;

function visibleLen(s: string): number {
  return s.replace(/\s/g, '').length;
}

function mergeOrphans(lines: string[]): string[] {
  const out: string[] = [];
  for (const raw of lines) {
    const p = raw.trim();
    if (!p) continue;
    if (out.length && (BAD_SUFFIX.test(out[out.length - 1]) || BAD_PREFIX.test(p))) {
      out[out.length - 1] = out[out.length - 1] + p;
      continue;
    }
    if (out.length && (visibleLen(p) < 3 || visibleLen(out[out.length - 1]) < 4)) {
      out[out.length - 1] = out[out.length - 1] + p;
      continue;
    }
    out.push(p);
  }
  return out;
}

export function splitCaptionVisualLines(text: string, maxChars: number = 14): string[] {
  const t = text.trim();
  if (!t) return [];
  if (visibleLen(t) <= maxChars) return [t];

  const chunks: string[] = [];
  let buf = '';
  for (const ch of t) {
    const next = buf + ch;
    if (visibleLen(next) > maxChars && buf) {
      chunks.push(buf);
      buf = ch;
    } else {
      buf = next;
    }
    if (SOFT_BREAK.test(ch) && visibleLen(buf) >= 6) {
      chunks.push(buf);
      buf = '';
    }
  }
  if (buf) chunks.push(buf);

  const lines = mergeOrphans(chunks.filter((c) => c.trim()));
  if (lines.length <= 1) return lines.length ? lines : [t];

  const balanced: string[] = [];
  let acc = '';
  for (const line of lines) {
    const candidate = acc ? acc + line : line;
    if (visibleLen(candidate) <= maxChars + 2) {
      acc = candidate;
    } else {
      if (acc) balanced.push(acc);
      acc = line;
    }
  }
  if (acc) balanced.push(acc);
  return mergeOrphans(balanced.length ? balanced : [t]);
}

export function groupTokensIntoLines(
  tokens: Array<{text: string}>,
  maxCharsPerLine: number = 14,
): Array<Array<{text: string; fromMs: number; toMs: number}>> {
  if (!tokens.length) return [];
  const full = tokens.map((t) => t.text).join('');
  const lines = splitCaptionVisualLines(full, maxCharsPerLine);
  if (lines.length <= 1) return [tokens as Array<{text: string; fromMs: number; toMs: number}>];

  const out: Array<Array<{text: string; fromMs: number; toMs: number}>> = [];
  let ti = 0;
  for (const line of lines) {
    const row: Array<{text: string; fromMs: number; toMs: number}> = [];
    let built = '';
    while (ti < tokens.length && visibleLen(built) < visibleLen(line)) {
      const tok = tokens[ti] as {text: string; fromMs: number; toMs: number};
      row.push(tok);
      built += tok.text;
      ti += 1;
      if (built.replace(/\s/g, '') === line.replace(/\s/g, '')) break;
    }
    if (row.length) out.push(row);
  }
  if (ti < tokens.length && out.length) {
    out[out.length - 1].push(...(tokens.slice(ti) as Array<{text: string; fromMs: number; toMs: number}>));
  }
  return out.length ? out : [tokens as Array<{text: string; fromMs: number; toMs: number}>];
}
