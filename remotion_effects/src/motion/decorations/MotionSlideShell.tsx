import React from 'react';
import {ProfileBackground} from '../backgrounds/ProfileBackground';
import {GithubDailyDecorations} from './GithubDailyDecorations';
import {BroadcastChrome} from './BroadcastChrome';
import {CaptionSafeScrim} from './CaptionSafeScrim';
import {BODY_FONT} from '../fonts';

interface Props {
  width: number;
  height: number;
  motionProfile: string;
  imagePath?: string;
  backgroundColor?: string;
  cssDecorations?: string[];
  slideRole?: 'title' | 'content' | 'cta';
  colorMood?: string;
  particleType?: string;
  broadcastFrame?: boolean;
  captionPlatform?: string;
  captionBottomPx?: number;
  midSafeBottomRatio?: number;
  starCount?: number;
  repoUrl?: string;
  children: React.ReactNode;
}

/** 统一背景 + 装饰 + 播报外框 */
export const MotionSlideShell: React.FC<Props> = ({
  width,
  height,
  motionProfile,
  imagePath,
  backgroundColor,
  cssDecorations,
  slideRole = 'title',
  colorMood = '',
  particleType = '',
  broadcastFrame = false,
  captionPlatform = '',
  captionBottomPx,
  midSafeBottomRatio,
  starCount = 12800,
  repoUrl = '',
  children,
}) => {
  const plat = (captionPlatform || '').toLowerCase();
  const chromeAccent =
    colorMood === 'warm'
      ? '#FF9F43'
      : plat === 'xhs' || colorMood === 'xhs-editorial'
        ? '#FF6B8A'
        : '#E85D04';

  return (
  <div
    style={{
      position: 'absolute',
      top: 0,
      left: 0,
      width,
      height,
      fontFamily: BODY_FONT,
    }}
  >
    <ProfileBackground
      profile={motionProfile}
      imagePath={imagePath}
      backgroundColor={backgroundColor}
      cssDecorations={cssDecorations}
      colorMood={colorMood}
      particleType={particleType}
    />
    <GithubDailyDecorations
      decorations={cssDecorations}
      slideRole={slideRole}
      starCount={starCount}
      repoUrl={repoUrl}
    />
    {broadcastFrame ? <BroadcastChrome accent={chromeAccent} /> : null}
    {plat === 'xhs' || broadcastFrame ? (
      <CaptionSafeScrim
        captionPlatform={captionPlatform}
        captionBottomPx={captionBottomPx}
        midSafeBottomRatio={midSafeBottomRatio}
      />
    ) : null}
    {children}
  </div>
  );
};
