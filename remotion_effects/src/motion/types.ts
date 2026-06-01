export type MotionProfileId =
  | 'github_daily_hook'
  | 'github_daily_bullets'
  | 'tiktok_word_pop'
  | 'kinetic_slam_tight'
  | 'kinetic_slam_loose'
  | 'typewriter_terminal'
  | 'episode_counter'
  | 'glitch_hook_clean'
  | 'bullet_rail_right'
  | 'bullet_stagger_up'
  | 'minimal_headline'
  | 'cta_pulse_arrow'
  | 'mono_code_rain'
  | 'flash_hook_smash'
  | 'split_mask_reveal'
  | 'glass_card_stack'
  | 'marquee_ticker'
  | 'shake_emphasis'
  | 'product_split_frame'
  | 'tiktok_phrase_pages';

export interface MotionParams {
  staggerFrames?: number;
  springDamping?: number;
  springStiffness?: number;
  wordsPerPageMs?: number;
  maxCharsPerPage?: number;
  captionFontScale?: number;
  captionBottomPx?: number;
  glitchFrames?: number;
}

export interface MotionTheme {
  bg: string;
  fg: string;
  accent: string;
  accent2?: string;
}

export const THEMES: Record<string, MotionTheme> = {
  github: {bg: '#0d1117', fg: '#f0f6fc', accent: '#58a6ff', accent2: '#3fb950'},
  tiktok: {bg: '#000000', fg: '#ffffff', accent: '#39E508', accent2: '#39E508'},
  /** 抖音暖色科技播报 */
  warm: {bg: '#1a100c', fg: '#fff8f0', accent: '#FF9F43', accent2: '#FFD93D'},
  /** 小红书冷色 editorial：深蓝灰底 + 浅字 + 蓝青强调（非暖色） */
  xhs: {bg: '#151c28', fg: '#e8eef7', accent: '#3b82f6', accent2: '#22d3ee'},
  cool: {bg: '#0f1419', fg: '#e2e8f0', accent: '#3b82f6', accent2: '#38bdf8'},
  kinetic: {bg: '#0c0c0e', fg: '#fafafa', accent: '#ff3366', accent2: '#ffcc00'},
  terminal: {bg: '#0a0f0a', fg: '#33ff99', accent: '#33ff99', accent2: '#1a1a1a'},
  minimal: {bg: '#f3efe8', fg: '#1c1917', accent: '#E85D04', accent2: '#FF9F43'},
};

export function resolveMotionTheme(
  profile: string,
  colorMood?: string,
  backgroundColor?: string,
): MotionTheme {
  const mood = (colorMood || '').trim().toLowerCase();
  if (mood === 'warm') return THEMES.warm;
  if (mood === 'cool' || mood === 'xhs-soft' || mood === 'xhs') return THEMES.cool;
  const bg = (backgroundColor || '').toLowerCase();
  if (bg === '#f5f5f0' || bg === '#ececec' || bg === '#f0f0f0' || bg === '#f3efe8') {
    return THEMES.xhs;
  }
  const p = String(profile);
  if (p.includes('github')) return THEMES.github;
  if (p.includes('tiktok')) return THEMES.warm;
  if (p.includes('terminal')) return THEMES.terminal;
  if (p.includes('minimal')) return THEMES.xhs;
  return THEMES.kinetic;
}
