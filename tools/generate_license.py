#!/usr/bin/env python3
"""生成 VideoShortsAgent 专业版激活码（卖家本地运行，勿提交密钥到公开仓库）。"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from python_agent.licensing import generate_license_key, _machine_id  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="生成 VSA1- 激活码")
    p.add_argument(
        "customer",
        nargs="?",
        default="pro",
        help="客户标识：pro=通用码；或粘贴用户机器码",
    )
    args = p.parse_args()
    secret = os.getenv("VSA_LICENSE_SECRET", "")
    if not secret:
        print("提示: 未设置 VSA_LICENSE_SECRET，使用内置开发密钥（仅供测试）")
    key = generate_license_key(args.customer)
    print(f"客户/标识: {args.customer}")
    print(f"激活码: {key}")
    if args.customer == "pro":
        print("\n通用 Pro 码（任意机器可用）。绑定单机请传入用户机器码。")
    print(f"\n本机机器码（测试绑定）: {_machine_id()}")


if __name__ == "__main__":
    main()
