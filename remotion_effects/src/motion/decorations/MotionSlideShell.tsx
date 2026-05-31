import React from 'react';
import {ProfileBackground} from '../backgrounds/ProfileBackground';
import {GithubDailyDecorations} from './GithubDailyDecorations';

interface Props {
  width: number;
  height: number;
  motionProfile: string;
  imagePath?: string;
  backgroundColor?: string;
  cssDecorations?: string[];
  slideRole?: 'title' | 'content' | 'cta';
  children: React.ReactNode;
}

/** 统一背景 + GitHub 日更装饰层 */
export const MotionSlideShell: React.FC<Props> = ({
  width,
  height,
  motionProfile,
  imagePath,
  backgroundColor,
  cssDecorations,
  slideRole = 'title',
  children,
}) => (
  <div
    style={{
      position: 'absolute',
      top: 0,
      left: 0,
      width,
      height,
      fontFamily: '"Microsoft YaHei", sans-serif',
    }}
  >
    <ProfileBackground
      profile={motionProfile}
      imagePath={imagePath}
      backgroundColor={backgroundColor}
      cssDecorations={cssDecorations}
    />
    <GithubDailyDecorations decorations={cssDecorations} slideRole={slideRole} />
    {children}
  </div>
);
