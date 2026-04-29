# B站爬虫

B站评论爬取（视频 + 动态）+ AI 智能分析 + 视频解析下载的 Windows 桌面工具，Python tkinter 构建。

## 功能

- **评论爬取** — 支持 **视频评论**（BV 号）和 **动态评论**（动态 ID）双模式，爬取一级评论和二级回复，支持多种排序，导出 CSV
- **AI 智能分析** — 接入 DeepSeek Flash API，对爬取的评论进行智能总结和分析
- **视频解析** — 输入 BV 号获取视频详情（标题、简介、分P列表）
- **视频下载** — DASH/FLV 格式下载，自动合并音视频（需 FFmpeg）
- **Cookie 管理** — 一键从 Chrome 读取 B站 Cookie，自动填充登录态

## 快速开始（普通用户）

1. 前往 **[Releases 页面](https://github.com/misaka19471-tech/bilibili-spider/releases)** 下载最新版的 `B站爬虫-v1.0.0.zip`
2. 解压后双击 `B站爬虫.exe` 即可运行

> 无需安装 Python，下载即用。

### 视频下载（可选）

下载 DASH 格式视频需要 FFmpeg 合并音视频流：

1. 从 [FFmpeg 官网](https://ffmpeg.org/download.html) 下载 Windows 构建版
2. 将 `ffmpeg.exe` 放到 `B站爬虫.exe` 同目录下

## 从源码运行（开发者）

### 前置条件

- Python 3.10+
- Chrome 浏览器（用于 Cookie 读取）

### 步骤

```bash
git clone https://github.com/misaka19471-tech/bilibili-spider.git
cd bilibili-spider
pip install -r requirements.txt
python bilibili_comment_spider.py
```

## 使用

1. **首次使用** — 点击「读取 Cookie」→ 在打开的 Chrome 中登录 B站 → Cookie 自动填充
2. **评论爬取** — 输入 **视频 BV 号** 或 **动态 ID** → 选排序方式 →「开始爬取」
3. **AI 分析** — 爬取完成后输入 DeepSeek API Key → 点击分析 → 自动对评论做智能总结
4. **视频下载** — 输入 BV 号 →「解析」→ 选择清晰度 →「下载」

> 目前 AI 分析仅支持 **DeepSeek Flash (dsflash)** 模型。
> 未登录状态下只能看到有限评论，建议始终使用已登录的 Cookie。

## 技术栈

| 组件 | 选型 |
|------|------|
| GUI | tkinter / ttk |
| B站 API | bilibili-api-python |
| HTTP | requests + curl_cffi |
| AI 模型 | DeepSeek Flash (dsflash) |
| 打包 | PyInstaller |
| 图标 | 自绘 .ico |

## 免责声明

本工具仅供学习和研究使用。使用本工具时请遵守 **哔哩哔哩用户协议** 及相关法律法规。

- 请勿将本工具用于大规模爬取、商业用途或侵犯他人权益的场景
- 下载的视频请仅用于个人学习，勿进行二次分发
- 作者不对因使用本工具产生的任何法律问题承担责任

## 许可证

MIT
