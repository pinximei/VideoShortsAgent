import React, {useMemo} from 'react';
import {useCurrentFrame, useVideoConfig, spring} from 'remotion';
import {
  createTikTokPages,
  wordsToCaptions,
  type CaptionPage,
} from '../captions/createTikTokPages';

/** 默认 TikTok 绿；暖色播报可覆盖 */
const DEFAULT_HIGHLIGHT = '#39E508';
const INACTIVE_COLOR = '#ffffff';
const DESIRED_FONT_SIZE = 96;
const CAPTION_BOTTOM_PX = 320;

interface Word {
  text: string;
  start: number;
  end: number;
}

export type PrebuiltCaptionPage = {
  text: string;
  startMs: number;
  durationMs: number;
  tokens: CaptionToken[];
};

interface Props {
  words: Word[];
  captionPages?: PrebuiltCaptionPage[];
  profile?: string;
  wordsPerPageMs?: number;
  maxCharsPerPage?: number;
  accentColor?: string;
}

export const TikTokActiveCaption: React.FC<Props> = ({
  words,
  captionPages: prebuiltPages,
  profile,
  wordsPerPageMs = 2400,
  accentColor = '#FF9F43',
  maxCharsPerPage = 18,
}) => {
  const highlightColor = accentColor || DEFAULT_HIGHLIGHT;
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();

  const pages: CaptionPage[] = useMemo(() => {
    if (prebuiltPages && prebuiltPages.length > 0) {
      return prebuiltPages.map((p) => ({
        text: p.text,
        startMs: p.startMs,
        durationMs: p.durationMs,
        tokens: p.tokens,
      }));
    }
    const caps = wordsToCaptions(words);
    return createTikTokPages(caps, wordsPerPageMs, maxCharsPerPage);
  }, [words, wordsPerPageMs, maxCharsPerPage, prebuiltPages]);

  const timeMs = (frame / fps) * 1000;
  let page: CaptionPage | null = pages[0] ?? null;
  for (const p of pages) {
    const end = p.startMs + (p.durationMs === Infinity ? wordsPerPageMs : p.durationMs);
    if (timeMs >= p.startMs && timeMs < end) {
      page = p;
      break;
    }
  }
  if (!page) return null;

  const pageStartFrame = Math.round((page.startMs / 1000) * fps);
  const localFrame = Math.max(0, frame - pageStartFrame);
  const enter = spring({
    frame: localFrame,
    fps,
    config: {damping: 200},
    durationInFrames: 5,
  });

  const absoluteTimeMs = page.startMs + (localFrame / fps) * 1000;
  const charCount = Math.max(1, page.text.replace(/\s/g, '').length);
  const fontSize = Math.min(
    DESIRED_FONT_SIZE,
    Math.floor((width * 0.88) / Math.max(4, charCount * 0.62)),
    charCount <= 8 ? 88 : charCount <= 12 ? 72 : 58,
  );

  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        right: 0,
        bottom: CAPTION_BOTTOM_PX,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        padding: '0 40px',
        zIndex: 120,
        transform: `translateY(${(1 - enter) * 12}px)`,
        opacity: enter,
      }}
    >
      <div
        style={{
          fontSize,
          fontWeight: 'bold',
          textAlign: 'center',
          whiteSpace: 'normal',
          lineHeight: 1.2,
          maxWidth: width * 0.9,
          wordBreak: 'keep-all',
          textTransform: 'none',
        }}
      >
        {page.tokens.map((token) => {
          const isActive =
            token.fromMs <= absoluteTimeMs && token.toMs > absoluteTimeMs;
          return (
            <span
              key={`${token.fromMs}-${token.text}`}
              style={{
                color: isActive ? highlightColor : INACTIVE_COLOR,
                textShadow: isActive
                  ? `0 0 12px ${highlightColor}88, 2px 2px 8px rgba(0,0,0,0.85)`
                  : '2px 2px 6px rgba(0,0,0,0.8)',
              }}
            >
              {token.text}
            </span>
          );
        })}
      </div>
    </div>
  );
};
