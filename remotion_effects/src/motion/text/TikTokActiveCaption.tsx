import React, {useMemo} from 'react';
import {useCurrentFrame, useVideoConfig, spring} from 'remotion';
import {
  createTikTokPages,
  wordsToCaptions,
  type CaptionPage,
} from '../captions/createTikTokPages';
import {groupTokensIntoLines} from '../captions/captionVisualLines';

/** 默认 TikTok 绿；暖色播报可覆盖 */
const DEFAULT_HIGHLIGHT = '#39E508';
const INACTIVE_COLOR = '#ffffff';
const DESIRED_FONT_SIZE = 82;
const CAPTION_BOTTOM_PX = 300;

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
  letterSpacing?: number;
  lineHeight?: number;
  bottomPx?: number;
  midSafeBottomRatio?: number;
  captionPlatform?: string;
}

export const TikTokActiveCaption: React.FC<Props> = ({
  words,
  captionPages: prebuiltPages,
  profile,
  wordsPerPageMs = 2400,
  accentColor = '#FF9F43',
  maxCharsPerPage = 20,
  letterSpacing = 0,
  lineHeight = 1.06,
  bottomPx = CAPTION_BOTTOM_PX,
  midSafeBottomRatio = 0.36,
  captionPlatform = '',
}) => {
  const isXhs = (captionPlatform || '').toLowerCase() === 'xhs';
  const highlightColor = accentColor || DEFAULT_HIGHLIGHT;
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const captionZoneTop = Math.round(height * (1 - midSafeBottomRatio));

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
  let page: CaptionPage | null = null;
  for (const p of pages) {
    const end = p.startMs + (p.durationMs === Infinity ? wordsPerPageMs : p.durationMs);
    if (timeMs >= p.startMs && timeMs < end) {
      page = p;
      break;
    }
  }
  // 口播结束后保持空白，避免又弹回第一句
  if (!page) {
    return null;
  }

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
  const visualMax = Math.min(28, Math.max(14, maxCharsPerPage));
  const lineGroups = groupTokensIntoLines(page.tokens, visualMax);
  const lineCount = Math.max(1, lineGroups.length);
  const fontSize = Math.min(
    isXhs ? 72 : DESIRED_FONT_SIZE,
    Math.floor(
      (width * (isXhs ? 0.82 : 0.9)) /
        Math.max(4, charCount * (isXhs ? 0.72 : 0.52) + letterSpacing * charCount * 0.15),
    ),
    charCount <= 8
      ? isXhs
        ? 64
        : 76
      : charCount <= 12
        ? isXhs
          ? 54
          : 64
        : isXhs
          ? 44
          : lineCount > 1
            ? 48
            : 52,
  );

  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        right: 0,
        top: captionZoneTop,
        bottom: bottomPx,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        padding: '0 48px',
        zIndex: 120,
        transform: `translateY(${(1 - enter) * 8}px)`,
        opacity: enter,
      }}
    >
      <div
        style={{
          fontSize,
          fontWeight: 'bold',
          textAlign: 'center',
          lineHeight,
          letterSpacing,
          maxWidth: width * 0.86,
          wordBreak: 'keep-all',
          textTransform: 'none',
        }}
      >
        {lineGroups.map((row, li) => (
          <div
            key={`line-${li}-${row[0]?.fromMs ?? 0}`}
            style={{
              display: 'block',
              whiteSpace: 'nowrap',
              marginBottom: li < lineGroups.length - 1 ? 2 : 0,
            }}
          >
            {row.map((token) => {
              const isActive =
                token.fromMs <= absoluteTimeMs && token.toMs > absoluteTimeMs;
              return (
                <span
                  key={`${token.fromMs}-${token.text}`}
                  style={{
                    color: isActive ? highlightColor : INACTIVE_COLOR,
                    textShadow: isActive
                      ? `0 0 14px ${highlightColor}99, 0 2px 12px rgba(0,0,0,0.92), 2px 2px 4px rgba(0,0,0,0.9)`
                      : '0 2px 10px rgba(0,0,0,0.9), 2px 2px 6px rgba(0,0,0,0.85)',
                  }}
                >
                  {token.text}
                </span>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
};
