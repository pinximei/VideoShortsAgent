#!/usr/bin/env python3
"""验证 Pipeline Web 界面依赖的 API 与静态资源（无需浏览器）。"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
PORT = 18780
BASE = f"http://127.0.0.1:{PORT}"


def _ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def _fail(msg: str) -> None:
    print(f"  [FAIL] {msg}")
    raise SystemExit(1)


def _api(client: httpx.Client, method: str, path: str, **kwargs) -> dict:
    r = client.request(method, f"{BASE}{path}", **kwargs)
    if r.status_code >= 400:
        _fail(f"{method} {path} -> HTTP {r.status_code}: {r.text[:200]}")
    if path == "/" or path.startswith("/assets"):
        return {}
    body = r.json()
    if body.get("code") != 0:
        _fail(f"{method} {path} -> code={body.get('code')} msg={body.get('message')}")
    return body.get("data") or {}


def main() -> int:
    env = {**dict(__import__("os").environ), "PIPELINE_CONFIG": str(ROOT / "config.yaml")}
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "scripts" / "start_server.py"), "--port", str(PORT), "--no-browser", "--skip-build"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        print(f"启动测试服务 :{PORT} …")
        with httpx.Client(timeout=120.0) as client:
            for _ in range(40):
                try:
                    client.get(f"{BASE}/api/v1/health")
                    break
                except Exception:
                    time.sleep(0.25)
            else:
                out = proc.stdout.read() if proc.stdout else ""
                _fail(f"服务未就绪\n{out}")

            print("\n1) 静态界面")
            r = client.get(f"{BASE}/")
            if r.status_code != 200 or "id=\"app\"" not in r.text:
                _fail("首页未返回 Vue 挂载点")
            _ok("GET / 返回管理界面 HTML")
            if "/assets/" not in r.text:
                _fail("首页未引用前端资源")
            _ok("前端 bundle 已挂载")

            print("\n2) API — 总览页")
            dash = _api(client, "GET", "/api/v1/health")
            if dash.get("service") != "aisoul-pipeline":
                _fail("health 数据异常")
            _ok("health")

            dash = _api(client, "GET", "/api/v1/dashboard")
            for key in ("job_counts", "total_jobs", "pending_publish", "run"):
                if key not in dash:
                    _fail(f"dashboard 缺少 {key}")
            _ok(f"dashboard total_jobs={dash['total_jobs']}")

            run_st = _api(client, "GET", "/api/v1/run/status")
            if "running" not in run_st:
                _fail("run/status 缺少 running")
            _ok("run/status")

            print("\n3) API — 任务列表页")
            jobs = _api(client, "GET", "/api/v1/jobs")
            if not isinstance(jobs, list):
                _fail("jobs 应返回数组")
            _ok(f"jobs 共 {len(jobs)} 条")

            packed = [j for j in jobs if j.get("status") == "packed"]
            if not packed:
                print("  [WARN] 无 packed 任务，跳过详情/文件/发布测试（可先 run_once）")
                sample_id = None
            else:
                sample_id = int(packed[0]["article_id"])

            if sample_id:
                print("\n4) API — 任务详情页")
                detail = _api(client, "GET", f"/api/v1/jobs/{sample_id}")
                for key in ("brief_json", "artifacts", "published"):
                    if key not in detail:
                        _fail(f"job detail 缺少 {key}")
                _ok(f"job/{sample_id} 含 brief 与 {len(detail['artifacts'])} 个文件")

                script_art = next((a for a in detail["artifacts"] if a["path"] == "script.txt"), None)
                if script_art:
                    fr = client.get(f"{BASE}{script_art['url']}")
                    if fr.status_code != 200 or len(fr.text) < 10:
                        _fail("script.txt 无法读取")
                    _ok("口播稿 script.txt 可下载")

                pub_art = next((a for a in detail["artifacts"] if a["path"] == "publish/douyin_title.txt"), None)
                if pub_art:
                    fr = client.get(f"{BASE}{pub_art['url']}")
                    if fr.status_code != 200:
                        _fail("douyin_title.txt 无法读取")
                    _ok("抖音标题文案可下载")

                print("\n5) API — 发布标记（测试渠道 toutiao，可重复幂等）")
                pub = client.post(
                    f"{BASE}/api/v1/publish",
                    json={"article_id": sample_id, "channel": "toutiao", "note": "ui-verify"},
                ).json()
                if pub.get("code") != 0:
                    _fail(f"publish 失败: {pub}")
                _ok(f"publish toutiao created={pub['data'].get('created')}")

                detail2 = _api(client, "GET", f"/api/v1/jobs/{sample_id}")
                if not detail2["published"].get("toutiao"):
                    _fail("发布后 published.toutiao 应为 true")
                _ok("详情页 published 状态已更新")

                print("\n6) API — 待发列表页")
                pending = _api(client, "GET", "/api/v1/pending/douyin")
                if not isinstance(pending, list):
                    _fail("pending 应返回数组")
                if any(int(j["article_id"]) == sample_id for j in pending):
                    # sample might still be pending on douyin if not marked - that's ok
                    pass
                _ok(f"pending/douyin {len(pending)} 条")

            print("\n7) API — 触发同步（真实拉 Soul，限时）")
            if run_st.get("running"):
                _fail("不应已在运行")
            trig = client.post(f"{BASE}/api/v1/run")
            if trig.status_code != 200:
                _fail(f"run 触发失败 {trig.status_code}")
            _ok("POST /run 已接受")

            for _ in range(90):
                st = _api(client, "GET", "/api/v1/run/status")
                if not st.get("running"):
                    break
                time.sleep(1)
            else:
                _fail("run 超过 90s 未完成")

            if st.get("last_error"):
                _fail(f"run 错误: {st['last_error']}")
            if not st.get("last_run"):
                _fail("run 完成但无 last_run")
            _ok(f"同步完成 last_run={json.dumps(st['last_run'], ensure_ascii=False)[:120]}…")

            trig2 = client.post(f"{BASE}/api/v1/run")
            if trig2.status_code != 200:
                _fail(f"空闲时再次 run 应成功，得 {trig2.status_code}")
            _ok("空闲时可再次触发同步")

            # 并发防护：运行中第二次触发应 409
            time.sleep(0.05)
            client.post(f"{BASE}/api/v1/run")
            time.sleep(0.15)
            if _api(client, "GET", "/api/v1/run/status").get("running"):
                dup = client.post(f"{BASE}/api/v1/run")
                if dup.status_code != 409:
                    _fail(f"运行中重复 run 应 409，得 {dup.status_code}")
                _ok("运行中拒绝重复触发 (409)")
                for _ in range(90):
                    if not _api(client, "GET", "/api/v1/run/status").get("running"):
                        break
                    time.sleep(0.5)

        print("\n=== 界面功能验证通过（API + 静态资源）===")
        print(f"手动目视：浏览器打开 {BASE}/ 查看总览/任务/待发页")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
