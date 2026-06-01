import React from 'react';
import {useCurrentFrame, useVideoConfig, spring} from 'remotion';
import {DISPLAY_FONT} from '../fonts';

interface Props {
  text: string;
  fontSize: number;
  color: string;
  accentColor: string;
  startFrame?: number;
}

/** 主标题逐字打出 + 末字高亮底色（参考 remotion word-highlight） */
export const HeroTypewriter: React.FC<Props> = ({
  text,
  fontSize,
  color,
  accentColor,
  startFrame = 8,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const chars = Array.from(text);
  const local = Math.max(0, frame - startFrame);
  const charsToShow = Math.min(chars.length, Math.floor(local / 2.5));

  return (
    <div
      style={{
        fontFamily: DISPLAY_FONT,
        fontSize,
        fontWeight: 900,
        textAlign: 'center',
        lineHeight: 1.15,
        wordBreak: 'keep-all',
      }}
    >
      {chars.slice(0, charsToShow).map((ch, i) => {
        const isLast = i === charsToShow - 1 && charsToShow === chars.length;
        const s = spring({
          frame: Math.max(0, local - i * 2),
          fps,
          config: {damping: 14, stiffness: 180},
        });
        return (
          <span
            key={`${i}-${ch}`}
            style={{
              color,
              opacity: s,
              position: 'relative',
              display: 'inline-block',
              transform: `translateY(${(1 - s) * 12}px)`,
            }}
          >
            {isLast ? (
              <span
                style={{
                  background: `${accentColor}55`,
                  borderRadius: 4,
                  padding: '0 2px',
                }}
              >
                {ch}
              </span>
            ) : (
              ch
            )}
          </span>
        );
      })}
    </div>
  );
};
