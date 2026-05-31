"""Pipeline 媒体资源：封面下载、Remotion public 路径。"""
from __future__ import annotations

import shutil
from pathlib import Path
from urllib.parse import urlparse

REMOTION_DIR = Path(__file__).resolve().parents[1] / "remotion_effects"


def resolve_cover_for_task(task_dir: Path, cover_url: str) -> Path | None:
    """下载封面到 task_dir/assets/cover.*，已存在则复用。"""
    url = (cover_url or "").strip()
    if not url.startswith(("http://", "https://")):
        return None
    assets = task_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    path = urlparse(url).path.lower()
    ext = ".png" if path.endswith(".png") else ".webp" if path.endswith(".webp") else ".jpg"
    dest = assets / f"cover{ext}"
    if dest.is_file() and dest.stat().st_size > 800:
        return dest
    try:
        import httpx

        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            r = client.get(url)
            r.raise_for_status()
            dest.write_bytes(r.content)
        if dest.stat().st_size > 800:
            return dest
    except Exception:
        return None
    return None


def remotion_public_image(local_path: str | Path, *, task_tag: str = "cover") -> str | None:
    """复制图片到 remotion public/images，返回 Remotion 可用的 /images/... 路径。"""
    src = Path(local_path)
    if not src.is_file():
        return None
    pub = REMOTION_DIR / "public" / "images"
    pub.mkdir(parents=True, exist_ok=True)
    ext = src.suffix.lower() if src.suffix else ".jpg"
    name = f"pipeline_{task_tag}{ext}"
    dest = pub / name
    shutil.copy2(src, dest)
    return f"/images/{name}"


def prefetch_task_cover(task_dir: Path, brief: dict) -> Path | None:
    """任务落盘时预下载封面，供片头 TitleCard / ContentCard 使用。"""
    url = str(brief.get("cover_image_url") or "").strip()
    if not url:
        return None
    return resolve_cover_for_task(Path(task_dir), url)


def apply_intro_cover_from_brief(
    render_effects: dict,
    task_dir: Path,
    brief: dict,
) -> dict:
    """将 brief.cover_image_url 写入 effects（TitleCard imagePath + subheading）。"""
    fx = dict(render_effects)
    url = str(brief.get("cover_image_url") or "").strip()
    title = str(brief.get("title") or "").strip()
    if title and not fx.get("intro_subheading"):
        fx["intro_subheading"] = title[:60]
    local: Path | None = None
    assets = task_dir / "assets"
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        candidate = assets / f"cover{ext}"
        if candidate.is_file() and candidate.stat().st_size > 800:
            local = candidate
            break
    if local is None:
        local = resolve_cover_for_task(task_dir, url)
    if local:
        fk = str(brief.get("feed_kind") or "news").strip().lower()
        # 资讯正文第 1 段用 cinematic B-roll；封面仅给片头 TitleCard（PH 封面常为抽象球体）
        if fk != "news":
            fx["cover_segment_path"] = str(local.resolve())
        rem = remotion_public_image(local, task_tag=str(brief.get("article_id") or task_dir.name))
        if rem:
            fx["intro_image_path"] = rem
            if fx.get("intro_card") is not False:
                fx["intro_card"] = True
    return fx
