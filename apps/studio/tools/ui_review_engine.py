#!/usr/bin/env python3
"""
VideoShorts Studio — UI 评审引擎（≥10 轮）

用法:
  py -3.12 apps/studio/tools/ui_review_engine.py
  py -3.12 apps/studio/tools/ui_review_engine.py --rounds 12 --src apps/studio/src

每轮聚焦不同维度；全部维度通过且综合分 ≥ 85 时输出 APPROVED。
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

# 仅匹配彩色 emoji 与历史遗留符号，不把 ✓ 等 UI 字符算入
EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\u2600-\u26FF"
    "\uFE0F"
    "◆✂📱🛒🤖📝🔑⚙"
    "]"
)

HEX_COLOR_RE = re.compile(r"#([0-9a-fA-F]{6})\b")

# 10+ 评审轮次：每轮主维度 + 通过阈值
ROUNDS: list[dict] = [
    {"id": 1, "name": "视觉层次", "min_score": 80},
    {"id": 2, "name": "色彩对比度", "min_score": 82},
    {"id": 3, "name": "字体与排版", "min_score": 80},
    {"id": 4, "name": "间距节奏", "min_score": 80},
    {"id": 5, "name": "组件一致性", "min_score": 82},
    {"id": 6, "name": "图标体系", "min_score": 85},
    {"id": 7, "name": "状态与反馈", "min_score": 80},
    {"id": 8, "name": "主操作突出", "min_score": 82},
    {"id": 9, "name": "导航与侧栏", "min_score": 85},
    {"id": 10, "name": "卡片与景深", "min_score": 82},
    {"id": 11, "name": "动效克制", "min_score": 78},
    {"id": 12, "name": "品牌识别", "min_score": 85},
]

PASS_OVERALL = 85


@dataclass
class Issue:
    round_id: int
    dimension: str
    severity: str  # error | warn
    message: str
    fix: str
    file: str = ""


@dataclass
class RoundResult:
    round_id: int
    dimension: str
    score: float
    passed: bool
    issues: list[Issue] = field(default_factory=list)


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _luminance(r: int, g: int, b: int) -> float:
    def ch(c: float) -> float:
        c /= 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast_ratio(fg: str, bg: str) -> float:
    l1 = _luminance(*_hex_to_rgb(fg))
    l2 = _luminance(*_hex_to_rgb(bg))
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def read_files(src: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for p in sorted(src.rglob("*")):
        if p.suffix in {".vue", ".css", ".ts"} and "node_modules" not in p.parts:
            rel = str(p.relative_to(src)).replace("\\", "/")
            try:
                out[rel] = p.read_text(encoding="utf-8")
            except OSError:
                pass
    return out


def theme_tokens(theme_css: str) -> dict[str, str]:
    tokens: dict[str, str] = {}
    for m in re.finditer(r"--([\w-]+):\s*([^;]+);", theme_css):
        tokens[m.group(1)] = m.group(2).strip()
    return tokens


class UiReviewEngine:
    def __init__(self, src_root: Path):
        self.src = src_root
        self.files = read_files(src_root)
        self.theme = theme_tokens(
            self.files.get("styles/theme.css", "")
            or self.files.get("src/styles/theme.css", "")
        )
        self.vue_text = "\n".join(v for k, v in self.files.items() if k.endswith(".vue"))

    def run_all(self, min_rounds: int = 10) -> tuple[list[RoundResult], bool]:
        rounds = ROUNDS if min_rounds <= len(ROUNDS) else ROUNDS + [
            {"id": i, "name": f"复检-{i}", "min_score": PASS_OVERALL}
            for i in range(len(ROUNDS) + 1, min_rounds + 1)
        ]
        results: list[RoundResult] = []
        for spec in rounds[: max(min_rounds, 10)]:
            r = self._run_round(spec["id"], spec["name"], spec["min_score"])
            results.append(r)
        overall = sum(x.score for x in results) / len(results)
        all_pass = all(r.passed for r in results) and overall >= PASS_OVERALL
        return results, all_pass

    def _run_round(self, rid: int, dimension: str, min_score: float) -> RoundResult:
        checks: list[tuple[str, Callable[[], list[Issue]]]] = [
            ("hierarchy", self._check_hierarchy),
            ("contrast", self._check_contrast),
            ("typography", self._check_typography),
            ("spacing", self._check_spacing),
            ("consistency", self._check_consistency),
            ("icons", self._check_icons),
            ("feedback", self._check_feedback),
            ("cta", self._check_cta),
            ("nav", self._check_nav),
            ("depth", self._check_depth),
            ("motion", self._check_motion),
            ("brand", self._check_brand),
        ]
        idx = (rid - 1) % len(checks)
        primary = checks[idx][1]
        issues = primary()
        # 每轮附带轻量全局扫描
        if rid % 3 == 0:
            issues.extend(self._check_icons())
        if rid % 4 == 0:
            issues.extend(self._check_contrast())

        errors = [i for i in issues if i.severity == "error"]
        warns = [i for i in issues if i.severity == "warn"]
        penalty = len(errors) * 12 + len(warns) * 4
        score = max(0.0, 100.0 - penalty)
        passed = score >= min_score and not errors
        for i in issues:
            i.round_id = rid
            i.dimension = dimension
        return RoundResult(rid, dimension, score, passed, issues)

    def _check_hierarchy(self) -> list[Issue]:
        issues: list[Issue] = []
        if ".page-title" not in self.vue_text and "PageHeader" not in self.vue_text:
            issues.append(
                Issue(0, "", "error", "缺少统一页面标题组件", "使用 PageHeader 统一 h1/h2 层级", "")
            )
        if "hero" not in self.vue_text and "HomeView" in self.vue_text:
            issues.append(Issue(0, "", "warn", "工作台缺少主视觉区", "增加 hero / bento 主区", "views/HomeView.vue"))
        if not re.search(r"font-size:\s*(2[2-9]|[3-9]\d)px", self.vue_text):
            issues.append(
                Issue(0, "", "warn", "主标题字号偏小", "PageHeader h2 建议 ≥22px", "components/PageHeader.vue")
            )
        return issues

    def _check_contrast(self) -> list[Issue]:
        issues: list[Issue] = []
        bg = "#0c0e14"
        muted = "#9ca3af"
        if self.theme.get("vsa-text-muted", "").startswith("#"):
            muted = self.theme["vsa-text-muted"]
        ratio = contrast_ratio(muted, bg)
        if ratio < 4.5:
            issues.append(
                Issue(
                    0,
                    "",
                    "error",
                    f"次要文字对比度 {ratio:.2f}:1 低于 WCAG AA(4.5:1)",
                    "将 --vsa-text-muted 提亮至 #a8b0c4 或更深背景",
                    "styles/theme.css",
                )
            )
        return issues

    def _check_typography(self) -> list[Issue]:
        issues: list[Issue] = []
        if "font-feature-settings" not in self.files.get("styles/theme.css", ""):
            issues.append(
                Issue(
                    0,
                    "",
                    "warn",
                    "未启用字体特性（kerning/tabular）",
                    "body 增加 font-feature-settings: 'kern', 'liga'",
                    "styles/theme.css",
                )
            )
        if "--vsa-font-display" not in self.theme:
            issues.append(
                Issue(
                    0,
                    "",
                    "warn",
                    "缺少展示用字体 token",
                    "增加 --vsa-font-display 用于标题",
                    "styles/theme.css",
                )
            )
        return issues

    def _check_spacing(self) -> list[Issue]:
        issues: list[Issue] = []
        odd = re.findall(r"(?:padding|gap|margin):\s*(\d+)px", self.vue_text)
        bad = [x for x in odd if int(x) % 4 != 0]
        if len(bad) > 8:
            issues.append(
                Issue(
                    0,
                    "",
                    "warn",
                    f"存在 {len(bad)} 处非 4px 倍数间距",
                    "统一为 4/8/12/16/20/24 节奏",
                    "各 .vue",
                )
            )
        return issues

    def _check_consistency(self) -> list[Issue]:
        issues: list[Issue] = []
        has_token_radius = "var(--vsa-radius" in self.vue_text or "var(--vsa-radius" in self.files.get(
            "styles/theme.css", ""
        )
        if self.vue_text.count("border-radius:") > 12 and not has_token_radius:
            issues.append(
                Issue(
                    0,
                    "",
                    "warn",
                    "部分圆角未使用 design token",
                    "统一 border-radius: var(--vsa-radius*)",
                    "components/*.vue",
                )
            )
        theme = self.files.get("styles/theme.css", "")
        if ".btn-primary" not in theme and ".btn-primary" not in self.vue_text:
            issues.append(Issue(0, "", "error", "缺少全局主按钮样式", "在 theme.css 定义 .btn-primary", "styles/theme.css"))
        return issues

    def _check_icons(self) -> list[Issue]:
        issues: list[Issue] = []
        emoji_hits: list[str] = []
        for path, text in self.files.items():
            if not path.endswith(".vue"):
                continue
            if EMOJI_RE.search(text) and "nav.ts" not in path:
                emoji_hits.append(path)
        if emoji_hits:
            issues.append(
                Issue(
                    0,
                    "",
                    "error",
                    f"界面仍使用 emoji 图标 ({len(emoji_hits)} 个文件)",
                    "改用 components/icons/UiIcon.vue SVG 体系",
                    ", ".join(emoji_hits[:5]),
                )
            )
        if "UiIcon" not in self.vue_text and "ui-icon" not in self.vue_text.lower():
            issues.append(
                Issue(0, "", "error", "未检测到 SVG 图标组件", "新增 UiIcon 并在导航/卡片中使用", "components/icons/")
            )
        return issues

    def _check_feedback(self) -> list[Issue]:
        issues: list[Issue] = []
        if "progress" not in self.vue_text.lower() and "Progress" not in self.vue_text:
            issues.append(
                Issue(
                    0,
                    "",
                    "warn",
                    "导出流程缺少进度反馈组件",
                    "ExportWorkbench 增加 ProgressBar",
                    "components/ExportWorkbench.vue",
                )
            )
        if "status" not in self.vue_text.lower():
            issues.append(Issue(0, "", "warn", "缺少状态文案区", "保留 status + 成功/失败色", ""))
        return issues

    def _check_cta(self) -> list[Issue]:
        issues: list[Issue] = []
        if "btn-primary" not in self.vue_text:
            issues.append(Issue(0, "", "warn", "页面缺少主色 CTA", "核心操作使用 btn-primary", ""))
        if "export-btn" not in self.vue_text and "ExportWorkbench" in self.vue_text:
            issues.append(Issue(0, "", "warn", "导出按钮未突出", "全宽主按钮 + 高度 44px", "ExportWorkbench.vue"))
        return issues

    def _check_nav(self) -> list[Issue]:
        issues: list[Issue] = []
        if "nav-item.active" not in self.vue_text and "nav-item--active" not in self.vue_text:
            issues.append(
                Issue(
                    0,
                    "",
                    "warn",
                    "导航选中态不明显",
                    "增加左侧指示条 + 背景高亮",
                    "SidebarNav.vue",
                )
            )
        if "sidebar" not in self.vue_text.lower():
            issues.append(Issue(0, "", "error", "缺少侧栏布局", "AppShell + SidebarNav", ""))
        return issues

    def _check_depth(self) -> list[Issue]:
        issues: list[Issue] = []
        css = self.files.get("styles/theme.css", "")
        if "--vsa-shadow-sm" not in css and "--vsa-shadow" not in css and "box-shadow" not in css:
            issues.append(
                Issue(
                    0,
                    "",
                    "error",
                    "卡片无阴影/景深 token",
                    "增加 --vsa-shadow-sm/md 与 .card 阴影",
                    "styles/theme.css",
                )
            )
        if "backdrop-filter" not in self.vue_text and "backdrop-filter" not in css:
            issues.append(
                Issue(
                    0,
                    "",
                    "warn",
                    "顶栏/浮层缺少玻璃态",
                    "TopBar 使用 backdrop-filter + 半透明",
                    "TopBar.vue",
                )
            )
        return issues

    def _check_motion(self) -> list[Issue]:
        issues: list[Issue] = []
        if "transition" not in self.vue_text:
            issues.append(Issue(0, "", "warn", "缺少过渡动效", "hover/active 增加 150ms transition", ""))
        if "prefers-reduced-motion" not in self.files.get("styles/theme.css", ""):
            issues.append(
                Issue(
                    0,
                    "",
                    "warn",
                    "未尊重减弱动效偏好",
                    "theme.css 增加 @media (prefers-reduced-motion)",
                    "styles/theme.css",
                )
            )
        return issues

    def _check_brand(self) -> list[Issue]:
        issues: list[Issue] = []
        if "mesh" not in self.vue_text and "orb" not in self.vue_text and "ambient" not in self.vue_text:
            issues.append(
                Issue(
                    0,
                    "",
                    "warn",
                    "背景缺少品牌氛围（渐变/光斑）",
                    "AppShell 增加 ambient 背景层",
                    "layouts/AppShell.vue",
                )
            )
        if "linear-gradient" not in self.vue_text:
            issues.append(
                Issue(0, "", "warn", "品牌渐变使用不足", "Logo/主按钮使用主色渐变", "SidebarNav.vue")
            )
        return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="VideoShorts UI Review Engine")
    parser.add_argument("--src", default="apps/studio/src", help="Vue src 根目录")
    parser.add_argument("--rounds", type=int, default=12, help="评审轮数 (最少 10)")
    parser.add_argument("--out", default="apps/studio/design/reviews/latest.json")
    args = parser.parse_args()

    studio_root = Path(__file__).resolve().parents[1]  # apps/studio
    repo = studio_root.parents[1]  # VideoShortsAgent
    src = (repo / args.src).resolve()
    if not src.is_dir():
        src = Path(args.src).resolve()

    engine = UiReviewEngine(src)
    n = max(10, args.rounds)
    results, approved = engine.run_all(n)

    report = {
        "approved": approved,
        "overall_score": round(sum(r.score for r in results) / len(results), 1),
        "rounds": len(results),
        "pass_count": sum(1 for r in results if r.passed),
        "results": [
            {
                "round": r.round_id,
                "dimension": r.dimension,
                "score": r.score,
                "passed": r.passed,
                "issues": [
                    {
                        "severity": i.severity,
                        "message": i.message,
                        "fix": i.fix,
                        "file": i.file,
                    }
                    for i in r.issues
                ],
            }
            for r in results
        ],
    }

    out_path = (studio_root / args.out.replace("apps/studio/", "")).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"UI Review Engine — {len(results)} rounds")
    print(f"Overall: {report['overall_score']}/100  Passed rounds: {report['pass_count']}/{len(results)}")
    print(f"Status: {'APPROVED' if approved else 'NEEDS_WORK'}")
    print(f"Report: {out_path}\n")

    for r in results:
        mark = "OK" if r.passed else "FAIL"
        print(f"  Round {r.round_id:2d} [{mark}] {r.dimension}: {r.score:.0f}")
        for i in r.issues:
            if i.severity == "error":
                print(f"       ! {i.message}")
                print(f"         → {i.fix}")

    return 0 if approved else 1


if __name__ == "__main__":
    sys.exit(main())
