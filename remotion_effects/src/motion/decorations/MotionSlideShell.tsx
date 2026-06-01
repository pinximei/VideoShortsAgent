import React from 'react';
import {ProfileBackground} from '../backgrounds/ProfileBackground';
import {GithubDailyDecorations} from './GithubDailyDecorations';
import {BroadcastChrome} from './BroadcastChrome';
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
  children,
}) => (
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
    <GithubDailyDecorations decorations={cssDecorations} slideRole={slideRole} />
    {broadcastFrame ? <BroadcastChrome accent={colorMood === 'warm' ? '#FF9F43' : '#E85D04'} /> : null}
    {children}
  </div>
);
