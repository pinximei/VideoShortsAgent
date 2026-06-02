/** 竖屏安全区：口播字幕 vs 中屏动效，避免叠字 */
export type LayoutZones = {
  captionBottomPx: number;
  midSafeTopRatio: number;
  midSafeBottomRatio: number;
  midAlign: 'flex-start' | 'center';
  captionScrimHeightRatio: number;
};

export function getLayoutZones(
  captionPlatform: string,
  height: number,
  motionParams?: {
    captionBottomPx?: number;
    midSafeBottomRatio?: number;
    midSafeTopRatio?: number;
  },
): LayoutZones {
  const isXhs = (captionPlatform || '').toLowerCase() === 'xhs';
  return {
    captionBottomPx:
      motionParams?.captionBottomPx ?? (isXhs ? 400 : 300),
    midSafeTopRatio: motionParams?.midSafeTopRatio ?? (isXhs ? 0.1 : 0.14),
    midSafeBottomRatio:
      motionParams?.midSafeBottomRatio ?? (isXhs ? 0.52 : 0.4),
    midAlign: 'flex-start',
    captionScrimHeightRatio: isXhs ? 0.3 : 0.22,
  };
}

export function midZoneHeight(height: number, zones: LayoutZones): number {
  return Math.round(
    height * (1 - zones.midSafeTopRatio - zones.midSafeBottomRatio),
  );
}
