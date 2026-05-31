export type IconName =
  | "home"
  | "clip"
  | "douyin"
  | "shop"
  | "ai"
  | "subtitle"
  | "key"
  | "settings";

export type NavItem = {
  path: string;
  label: string;
  icon: IconName;
  section?: "main" | "ai" | "system";
  needKey?: boolean;
  soon?: boolean;
};

export const navItems: NavItem[] = [
  { path: "/", label: "工作台", icon: "home", section: "main" },
  { path: "/clip", label: "本地裁剪", icon: "clip", section: "main" },
  { path: "/douyin", label: "抖音发布包", icon: "douyin", section: "main" },
  { path: "/ecommerce", label: "电商切片", icon: "shop", section: "main" },
  { path: "/ai", label: "AI 智能切片", icon: "ai", section: "ai", needKey: true, soon: true },
  { path: "/subtitle", label: "翻译配音", icon: "subtitle", section: "ai", needKey: true, soon: true },
  { path: "/license", label: "授权", icon: "key", section: "system" },
  { path: "/settings", label: "设置", icon: "settings", section: "system" },
];
