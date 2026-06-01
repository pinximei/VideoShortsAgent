import React, {useMemo} from 'react';
import {useCurrentFrame, useVideoConfig, spring, interpolate} from 'remotion';
import {BODY_FONT} from '../fonts';
import type {PrebuiltCaptionPage} from './TikTokActiveCaption';

interface Word {
  text: string;
  start: number;
  end: number;
}

interface Props {
  words: Word[];
  captionPages?: PrebuiltCaptionPage[];
  accentColor?: string;
  textColor?: string;
  fontScale?: number;
  bottomPx?: number;
}

/** 小红书：底栏 editorial 字幕条，字号更小、翻页更慢、毛玻璃底 */
export const XhsEditorialCaption: React.FC<Props> = ({
  words,
  captionPages = [],
  accentColor = '#3b82f6',
  textColor = '#e8eef7',
  fontScale = 0.72,
  bottomPx = 200,
}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const timeMs = (frame / fps) * 1000;

  const pages = useMemo(() => {
    if (captionPages.length) {
      return captionPages;
    }
    return words.map((w) => ({
      text: w.text.trim(),
      startMs: Math.round(w.start * 1000),
      durationMs: Math.max(400, Math.round((w.end - w.start) * 1000)),
      tokens: [
        {
          text: w.text.trim(),
          fromMs: Math.round(w.start * 1000),
          toMs: Math.round(w.end * 1000),
        },
      ],
    }));
  }, [captionPages, words]);

  let page = pages[0];
  for (const p of pages) {
    const end = p.startMs + p.durationMs;
    if (timeMs >= p.startMs && timeMs < end) {
      page = p;
      break;
    }
  }
  if (!page?.text) {
    return null;
  }

  const pageStart = Math.round((page.startMs / 1000) * fps);
  const local = Math.max(0, frame - pageStart);
  const enter = spring({frame: local, fps, config: {damping: 200}, durationInFrames: 8});
  const baseSize = Math.min(52, Math.floor(42 * fontScale));
  const charN = Math.max(4, page.text.replace(/\s/g, '').length);
  const fontSize = Math.min(baseSize, Math.floor((width * 0.82) / Math.max(6, charN * 0.55)));

  return (
    <div
      style={{
        position: 'absolute',
        left: 48,
        right: 48,
        bottom: bottomPx,
        zIndex: 110,
        display: 'flex',
        justifyContent: 'center',
        opacity: enter,
        transform: `translateY(${interpolate(enter, [0, 1], [8, 0])}px)`,
      }}
    >
      <div
        style={{
          maxWidth: width * 0.88,
          padding: '14px 22px',
          borderRadius: 12,
          background: 'rgba(15, 23, 42, 0.72)',
          border: `1px solid ${accentColor}44`,
          backdropFilter: 'blur(12px)',
          boxShadow: '0 8px 32px rgba(0,0,0,0.35)',
        }}
      >
        <div
          style={{
            fontFamily: BODY_FONT,
            fontSize,
            fontWeight: 600,
            lineHeight: 1.45,
            color: textColor,
            textAlign: 'center',
            wordBreak: 'keep-all',
            letterSpacing: 0.5,
          }}
        >
          {page.text}
        </div>
      </div>
    </div>
  );
};
