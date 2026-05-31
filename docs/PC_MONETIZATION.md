# VideoShorts Studio 桌面版与变现说明

完整路线图见 [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md)。

## 启动桌面版

```bat
install.bat
start_pc.bat
```

或：`python -m python_agent.desktop`

会打开独立窗口（pywebview），内嵌本地 Gradio，不依赖浏览器书签。

## 版本差异

| 功能 | 免费版 | 专业版 |
|------|--------|--------|
| 本地裁剪（FFmpeg，无 API） | 不限次 | 不限次 |
| AI Agent / 中文字幕 | 每月 2 次导出 | 不限次 |
| 导出水印 | 有（免费版） | 无 |
| API 费用 | 用户自备通义/Groq | 同左 |

授权数据目录：`%APPDATA%\VideoShortsAgent\`（license.json、usage.json）

## 卖家：生成激活码

```bash
# 设置发行密钥（务必改掉默认开发密钥）
set VSA_LICENSE_SECRET=你的私密字符串

# 通用 Pro（任意机器）
py tools/generate_license.py pro

# 绑定用户机器码（界面「授权」页可复制）
py tools/generate_license.py <用户机器码>
```

## 建议售价（参考）

- 专业版买断：¥49–99（闲鱼/爱发电/微店发激活码）
- 不提供云端代跑，避免替你垫 API 费

## 打包 exe（可选）

```bat
build_pc.bat
```

可将 `resources/ffmpeg/bin` 放到 exe 旁，实现免安装 FFmpeg。

## 推广话术

「本地视频裁剪 + 可选 AI 切片，数据不出本机；免费版够剪片，专业版去水印无限 AI。」
