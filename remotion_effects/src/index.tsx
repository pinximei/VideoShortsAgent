import {registerRoot, Composition} from 'remotion';
import {CaptionOverlay} from './compositions/CaptionOverlay';
import {GradientBackground} from './compositions/GradientBackground';

/**
 * Remotion Root - 注册所有特效组件
 *
 * 每个 Composition 是一个独立的特效模板，可通过 CLI 渲染：
 *   npx remotion render src/index.tsx CaptionOverlay --props='...'
 */
export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* 字幕弹出特效 - 大字居中 + 弹性动画 */}
      <Composition
        id="CaptionOverlay"
        component={CaptionOverlay}
        durationInFrames={9000}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{
          text: '示例金句文案',
          sentences: [],
          style: 'spring' as const,
        }}
      />

      {/* 渐变背景特效 - 作为透明覆盖层 */}
      <Composition
        id="GradientBackground"
        component={GradientBackground}
        durationInFrames={9000}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{
          colorFrom: '#FF6B6B',
          colorTo: '#4ECDC4',
          opacity: 0.3,
        }}
      />
    </>
  );
};

registerRoot(RemotionRoot);
