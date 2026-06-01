/**
 * TikTok 字幕分页：时间间隙 + 每页字数上限，避免半句话拆两页。
 */
export type CaptionToken = {text: string; fromMs: number; toMs: number};
export type CaptionPage = {
  text: string;
  startMs: number;
  durationMs: number;
  tokens: CaptionToken[];
};

type WordInput = {text: string; start: number; end: number};

export function wordsToCaptions(words: WordInput[]): Array<{
  text: string;
  startMs: number;
  endMs: number;
}> {
  const out: Array<{text: string; startMs: number; endMs: number}> = [];
  for (const w of words) {
    const t = (w.text || '').trim();
    if (!t) continue;
    const needsSpace = out.length > 0 && !/[\s，,、]$/.test(out[out.length - 1].text);
    out.push({
      text: needsSpace ? ` ${t}` : t,
      startMs: Math.round(w.start * 1000),
      endMs: Math.round(w.end * 1000),
    });
  }
  return out;
}

function visibleLen(s: string): number {
  return s.replace(/\s/g, '').length;
}

export function createTikTokPages(
  captions: Array<{text: string; startMs: number; endMs: number}>,
  combineTokensWithinMilliseconds: number,
  maxCharsPerPage: number = 18,
): CaptionPage[] {
  const pages: CaptionPage[] = [];
  let currentText = '';
  let currentTokens: CaptionToken[] = [];
  let currentFrom = 0;
  let currentTo = 0;

  const flush = () => {
    if (!currentText.trim()) return;
    pages.push({
      text: currentText.trimStart(),
      startMs: currentFrom,
      tokens: currentTokens,
      durationMs: Infinity,
    });
    if (pages.length > 1) {
      pages[pages.length - 2].durationMs =
        currentFrom - pages[pages.length - 2].startMs;
    }
  };

  const shouldBreakPage = (item: {startMs: number; endMs: number; text: string}) => {
    if (!currentText.trim()) return false;
    const gap = item.startMs - currentTo;
    const nextLen = visibleLen(currentText + item.text);
    if (gap > combineTokensWithinMilliseconds) return true;
    if (nextLen > maxCharsPerPage) return true;
    return false;
  };

  captions.forEach((item, index) => {
    const piece = item.text.trim();
    if (!piece) return;

    if (shouldBreakPage(item)) {
      flush();
      currentText = piece;
      currentTokens = [{text: piece, fromMs: item.startMs, toMs: item.endMs}];
      currentFrom = item.startMs;
      currentTo = item.endMs;
    } else {
      if (!currentText) currentFrom = item.startMs;
      const sep = currentText && !currentText.endsWith(' ') ? ' ' : '';
      currentText += sep + piece;
      currentTokens.push({
        text: currentTokens.length === 0 ? piece : (sep ? ' ' : '') + piece,
        fromMs: item.startMs,
        toMs: item.endMs,
      });
      currentTo = item.endMs;
    }

    if (index === captions.length - 1) {
      flush();
      if (pages.length) {
        pages[pages.length - 1].durationMs =
          currentTo - pages[pages.length - 1].startMs;
      }
    }
  });

  return pages;
}
