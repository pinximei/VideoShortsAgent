import React, {useMemo} from 'react';
import {useCurrentFrame, useVideoConfig, spring} from 'remotion';
import {
  createTikTokPages,
  wordsToCaptions,
  type CaptionPage,
} from '../captions/createTikTokPages';

/** Remotion 官方 TikTok 模板对齐值 */
const HIGHLIGHT_COLOR = '#39E508';
const INACTIVE_COLOR = '#ffffff';
const DESIRED_FONT_SIZE = 96;
const CAPTION_BOTTOM_PX = 320;

interface Word {
  text: string;
  start: number;
  end: number;
}

interface Props {
  words: Word[];
  profile?: string;
  wordsPerPageMs?: number;
}

export const TikTokActiveCaption: React.FC<Props> = ({
  words,
  profile,
  wordsPerPageMs = 1200,
}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();

  const pages: CaptionPage[] = useMemo(() => {
    const caps = wordsToCaptions(words);
    return createTikTokPages(caps, wordsPerPageMs);
  }, [words, wordsPerPageMs]);

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
  const fontSize = Math.min(
    DESIRED_FONT_SIZE,
    Math.floor((width * 0.9) / Math.max(6, page.text.length * 0.55)),
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
        padding: '0 48px',
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
          whiteSpace: 'pre',
          lineHeight: 1.15,
          maxWidth: width * 0.92,
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
                color: isActive ? HIGHLIGHT_COLOR : INACTIVE_COLOR,
                textShadow: isActive
                  ? '0 0 12px rgba(57,229,8,0.5), 2px 2px 8px rgba(0,0,0,0.85)'
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
