import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';

const CORNER_LEN = 46;
const ARM = 2;

/** 对角两角短 L 激光，单角轮流呼吸，避免四边同时发光显得乱 */
export const LaserCornerFrame: React.FC = () => {
  const frame = useCurrentFrame();
  const {width, height, fps} = useVideoConfig();
  const inset = {top: 128, bottom: 288, left: 52, right: 52};

  const corners = [
    {id: 'tl', top: inset.top, left: inset.left, sx: 1, sy: 1},
    {
      id: 'br',
      top: height - inset.bottom - CORNER_LEN,
      left: width - inset.right - CORNER_LEN,
      sx: -1,
      sy: -1,
    },
  ] as const;

  const activeIdx = Math.floor(frame / Math.round(fps * 1.6)) % corners.length;

  const renderCorner = (c: (typeof corners)[number], idx: number) => {
    const isActive = idx === activeIdx;
    const phaseOff = idx * 22;
    const cycle = Math.round(fps * 1.8);
    const t = interpolate((frame + phaseOff) % cycle, [0, cycle], [0, 1]);
    const grow = isActive
      ? interpolate(t, [0, 0.42, 1], [0.4, 1, 0.55])
      : 0.42;
    const glow = isActive
      ? 0.38 + 0.42 * Math.sin((frame + phaseOff) / 11)
      : 0.22;

    const hW = CORNER_LEN * grow;
    const vH = CORNER_LEN * grow;
    const hLeft = c.sx > 0 ? c.left : c.left + (CORNER_LEN - hW);
    const vTop = c.sy > 0 ? c.top : c.top + (CORNER_LEN - vH);

    const armStyle = (isH: boolean): React.CSSProperties => ({
      position: 'absolute',
      left: isH ? hLeft : c.sx > 0 ? c.left : c.left + CORNER_LEN - ARM,
      top: isH ? c.top : vTop,
      width: isH ? hW : ARM,
      height: isH ? ARM : vH,
      borderRadius: 2,
      background: isH
        ? `linear-gradient(${c.sx > 0 ? '90deg' : '270deg'}, transparent, rgba(255,190,120,${0.7 * glow}), rgba(255,230,200,${glow * 0.9}))`
        : `linear-gradient(${c.sy > 0 ? '180deg' : '0deg'}, transparent, rgba(255,190,120,${0.7 * glow}), rgba(255,230,200,${glow * 0.9}))`,
      boxShadow: isActive
        ? `0 0 10px rgba(255,159,67,${0.4 * glow}), 0 0 22px rgba(255,120,40,${0.18 * glow})`
        : 'none',
      filter: 'blur(0.8px)',
      opacity: isActive ? 0.5 + grow * 0.4 : 0.28,
    });

    return (
      <React.Fragment key={c.id}>
        <div style={armStyle(true)} />
        <div style={armStyle(false)} />
      </React.Fragment>
    );
  };

  return (
    <div style={{position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 5}}>
      {corners.map((c, i) => renderCorner(c, i))}
    </div>
  );
};
