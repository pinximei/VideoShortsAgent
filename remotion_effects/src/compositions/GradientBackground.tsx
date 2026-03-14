import React from 'react';
import {useCurrentFrame, useVideoConfig, interpolate} from 'remotion';

/**
 * GradientBackground - 渐变背景动画
 *
 * 作为透明覆盖层叠加到视频上，增加氛围感。
 * 渐变角度随时间旋转，颜色平滑过渡。
 */
interface GradientBackgroundProps {
  colorFrom: string;
  colorTo: string;
  opacity: number;
}

export const GradientBackground: React.FC<GradientBackgroundProps> = ({
  colorFrom,
  colorTo,
  opacity,
}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();

  // 渐变角度随时间旋转
  const angle = interpolate(frame, [0, durationInFrames], [0, 360]);

  // 透明度呼吸效果
  const breathe = interpolate(
    frame % 90,
    [0, 45, 90],
    [opacity * 0.8, opacity, opacity * 0.8],
    {extrapolateRight: 'clamp'}
  );

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: `linear-gradient(${angle}deg, ${colorFrom}, ${colorTo})`,
        opacity: breathe,
        mixBlendMode: 'overlay',
      }}
    />
  );
};
