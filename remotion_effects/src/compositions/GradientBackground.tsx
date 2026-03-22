import React from 'react';
import {useCurrentFrame, useVideoConfig, interpolate} from 'remotion';

/**
 * GradientBackground - 渐变背景动画（升级版）
 *
 * 三层渐变叠加：径向渐变 + 线性渐变旋转 + 噪点纹理
 * 色彩呼吸：两个颜色之间缓慢渐变过渡
 * 混合模式可配置
 */
interface GradientBackgroundProps {
  colorFrom?: string;
  colorTo?: string;
  opacity?: number;
  blendMode?: string;
}

// 简单的十六进制颜色插值
function lerpColor(a: string, b: string, t: number): string {
  const parseHex = (hex: string) => {
    const h = hex.replace('#', '');
    return {
      r: parseInt(h.substring(0, 2), 16),
      g: parseInt(h.substring(2, 4), 16),
      b: parseInt(h.substring(4, 6), 16),
    };
  };

  try {
    const ca = parseHex(a);
    const cb = parseHex(b);
    const r = Math.round(ca.r + (cb.r - ca.r) * t);
    const g = Math.round(ca.g + (cb.g - ca.g) * t);
    const b_val = Math.round(ca.b + (cb.b - ca.b) * t);
    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b_val.toString(16).padStart(2, '0')}`;
  } catch {
    return a;
  }
}

export const GradientBackground: React.FC<GradientBackgroundProps> = ({
  colorFrom = '#FF6B6B',
  colorTo = '#4ECDC4',
  opacity = 0.3,
  blendMode = 'overlay',
}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();

  // 渐变角度随时间旋转（中层）
  const angle = interpolate(frame, [0, durationInFrames], [0, 360]);

  // 色彩呼吸：在 colorFrom 和 colorTo 之间来回渐变
  const colorBreatheCycle = 180; // 每 180 帧一个完整呼吸
  const colorT = interpolate(
    frame % colorBreatheCycle,
    [0, colorBreatheCycle / 2, colorBreatheCycle],
    [0, 1, 0],
  );
  const breatheColorFrom = lerpColor(colorFrom, colorTo, colorT * 0.4);
  const breatheColorTo = lerpColor(colorTo, colorFrom, colorT * 0.4);

  // 透明度呼吸效果
  const breathe = interpolate(
    frame % 90,
    [0, 45, 90],
    [opacity * 0.8, opacity, opacity * 0.8],
    {extrapolateRight: 'clamp'},
  );

  // 径向渐变中心缓慢移动
  const radialX = 50 + Math.sin(frame * 0.004) * 15;
  const radialY = 50 + Math.cos(frame * 0.006) * 15;

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
      }}
    >
      {/* 底层：径向渐变 */}
      <div
        style={{
          position: 'absolute',
          top: 0, left: 0, right: 0, bottom: 0,
          background: `radial-gradient(ellipse at ${radialX}% ${radialY}%, ${breatheColorFrom}, ${breatheColorTo})`,
          opacity: breathe,
          mixBlendMode: blendMode as any,
        }}
      />

      {/* 中层：线性渐变旋转 */}
      <div
        style={{
          position: 'absolute',
          top: 0, left: 0, right: 0, bottom: 0,
          background: `linear-gradient(${angle}deg, ${breatheColorFrom}80, ${breatheColorTo}80)`,
          opacity: breathe * 0.7,
          mixBlendMode: 'soft-light' as any,
        }}
      />

      {/* 顶层：噪点纹理（用 repeating-conic-gradient 模拟） */}
      <div
        style={{
          position: 'absolute',
          top: 0, left: 0, right: 0, bottom: 0,
          backgroundImage: `
            repeating-conic-gradient(
              rgba(255,255,255,0.03) 0%,
              transparent 0.5%,
              transparent 1%,
              rgba(255,255,255,0.02) 1.5%
            ),
            repeating-conic-gradient(
              transparent 0%,
              rgba(0,0,0,0.04) 0.3%,
              transparent 0.8%,
              rgba(255,255,255,0.01) 1.2%
            )
          `,
          backgroundSize: '120px 120px, 80px 80px',
          opacity: 0.6,
          mixBlendMode: blendMode as any,
          pointerEvents: 'none',
        }}
      />
    </div>
  );
};
