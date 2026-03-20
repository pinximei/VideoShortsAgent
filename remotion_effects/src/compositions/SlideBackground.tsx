import React from 'react';
import {
  useCurrentFrame,
  useVideoConfig,
  spring,
  interpolate,
} from 'remotion';

/**
 * SlideBackground - 通用幻灯片背景
 *
 * 支持：渐变背景 / 图片背景 + 蒙层
 * 带缓慢旋转的渐变动画，增加视觉动感。
 */
interface SlideBackgroundProps {
  colors: string[];
  imagePath?: string;
  overlayOpacity?: number;
}

export const SlideBackground: React.FC<SlideBackgroundProps> = ({
  colors = ['#0f0c29', '#302b63'],
  imagePath,
  overlayOpacity = 0.6,
}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();

  // 渐变旋转角度（缓慢旋转）
  const angle = interpolate(frame, [0, 900], [0, 360]);

  // 呼吸透明度
  const breathe = interpolate(
    frame % 120,
    [0, 60, 120],
    [0.85, 1, 0.85],
  );

  const gradientColors = colors.length >= 2
    ? colors.join(', ')
    : `${colors[0]}, ${colors[0]}`;

  return (
    <div style={{
      position: 'absolute',
      top: 0, left: 0,
      width, height,
    }}>
      {/* 图片背景层 */}
      {imagePath && (
        <img
          src={imagePath}
          style={{
            position: 'absolute',
            top: 0, left: 0,
            width: '100%', height: '100%',
            objectFit: 'cover',
            // Ken Burns 缓慢推近效果
            transform: `scale(${1 + frame * 0.0003})`,
          }}
        />
      )}

      {/* 渐变蒙层 */}
      <div style={{
        position: 'absolute',
        top: 0, left: 0,
        width: '100%', height: '100%',
        background: `linear-gradient(${angle}deg, ${gradientColors})`,
        opacity: imagePath ? overlayOpacity : breathe,
      }} />
    </div>
  );
};
