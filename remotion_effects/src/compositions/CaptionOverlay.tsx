import React from 'react';
import {
  useCurrentFrame,
  useVideoConfig,
  spring,
  interpolate,
  Easing,
} from 'remotion';

/**
 * CaptionOverlay - 字幕弹出特效
 *
 * 特效：
 * 1. 文字从底部弹出（spring 物理动画）
 * 2. 半透明黑色底栏
 * 3. 文字发光效果
 * 4. 淡出结束
 */
interface CaptionOverlayProps {
  text: string;
  style: 'spring' | 'fade' | 'typewriter';
}

export const CaptionOverlay: React.FC<CaptionOverlayProps> = ({
  text,
  style = 'spring',
}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();

  // 弹出动画
  const springValue = spring({
    frame,
    fps,
    config: {damping: 12, stiffness: 120, mass: 0.8},
  });

  // 淡出（最后 20 帧）
  const fadeOut = interpolate(
    frame,
    [durationInFrames - 20, durationInFrames],
    [1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
  );

  // 底栏高度动画
  const barHeight = interpolate(springValue, [0, 1], [0, 200]);

  // 文字位移
  const textY = interpolate(springValue, [0, 1], [100, 0]);

  // 发光脉冲
  const glowIntensity = interpolate(
    frame % 60,
    [0, 30, 60],
    [2, 6, 2],
    {extrapolateRight: 'clamp'}
  );

  return (
    <div
      style={{
        position: 'absolute',
        bottom: 0,
        left: 0,
        right: 0,
        opacity: fadeOut,
      }}
    >
      {/* 半透明底栏 */}
      <div
        style={{
          height: barHeight,
          background: 'linear-gradient(transparent, rgba(0,0,0,0.85))',
          display: 'flex',
          alignItems: 'flex-end',
          justifyContent: 'center',
          padding: '0 60px 40px',
        }}
      >
        {/* 金句文字 */}
        <div
          style={{
            transform: `translateY(${textY}px)`,
            fontSize: 56,
            fontWeight: 900,
            color: '#FFFFFF',
            textAlign: 'center',
            lineHeight: 1.4,
            textShadow: `0 0 ${glowIntensity}px rgba(255,215,0,0.8), 0 2px 8px rgba(0,0,0,0.9)`,
            fontFamily: '"Microsoft YaHei", "PingFang SC", sans-serif',
            letterSpacing: 2,
          }}
        >
          {text}
        </div>
      </div>
    </div>
  );
};
