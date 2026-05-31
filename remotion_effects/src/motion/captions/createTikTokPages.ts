/**
 * 与 @remotion/captions createTikTokStyleCaptions 同逻辑（预研对齐官方源码）
 * https://github.com/remotion-dev/remotion/blob/main/packages/captions/src/create-tiktok-style-captions.ts
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
    const t = w.text;
    const needsSpace = t.length > 0 && !t.startsWith(' ') && out.length > 0;
    out.push({
      text: needsSpace ? ` ${t}` : t,
      startMs: Math.round(w.start * 1000),
      endMs: Math.round(w.end * 1000),
    });
  }
  return out;
}

export function createTikTokPages(
  captions: Array<{text: string; startMs: number; endMs: number}>,
  combineTokensWithinMilliseconds: number,
): CaptionPage[] {
  const pages: CaptionPage[] = [];
  let currentText = '';
  let currentTokens: CaptionToken[] = [];
  let currentFrom = 0;
  let currentTo = 0;

  const add = () => {
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

  captions.forEach((item, index) => {
    const {text} = item;
    if (
      text.startsWith(' ') &&
      currentTo - currentFrom > combineTokensWithinMilliseconds
    ) {
      if (currentText !== '') add();
      currentText = text.trimStart();
      currentTokens = [{text: currentText, fromMs: item.startMs, toMs: item.endMs}].filter(
        (t) => t.text !== '',
      );
      currentFrom = item.startMs;
      currentTo = item.endMs;
    } else {
      if (currentText === '') currentFrom = item.startMs;
      currentText += text;
      currentText = currentText.trimStart();
      if (text.trim() !== '') {
        currentTokens.push({
          text: currentTokens.length === 0 ? currentText.trimStart() : text,
          fromMs: item.startMs,
          toMs: item.endMs,
        });
      }
      currentTo = item.endMs;
    }
    if (index === captions.length - 1 && currentText !== '') {
      add();
      pages[pages.length - 1].durationMs =
        currentTo - pages[pages.length - 1].startMs;
    }
  });

  return pages;
}
