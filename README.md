# B站爬虫 · Ember 焰火版

B站评论爬取 + 视频解析下载的 Windows 桌面工具，Python tkinter 构建。

## 功能

- **评论爬取** — 按 BV 号/动态 ID 爬取一级评论和二级回复，支持多种排序，导出 CSV
- **视频解析** — 输入 BV 号获取视频详情（标题、简介、分P列表）
- **视频下载** — DASH/FLV 格式下载，自动合并音视频（需 FFmpeg）
- **Cookie 管理** — 一键从 Chrome 读取 B站 Cookie，自动填充登录态

## 截图

![主界面](screenshot.png)

## 安装

### 前置条件

- Python 3.10+
- Chrome 浏览器（用于 Cookie 读取）

### 步骤

```bash
# 1. 克隆仓库
git clone https://github.com/你的用户名/bilibili-spider.git
cd bilibili-spider

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行
python bilibili_comment_spider.py
```

### 视频下载（可选）

下载 DASH 格式视频需要 FFmpeg 合并音视频流：

1. 从 [FFmpeg 官网](https://ffmpeg.org/download.html) 下载 Windows 构建版
2. 将 `ffmpeg.exe` 放到程序所在目录，或添加到系统 PATH

## 使用

1. **首次使用** — 点击「读取 Cookie」→ 在打开的 Chrome 中登录 B站 → Cookie 自动填充
2. **评论爬取** — 输入 BV 号或动态 ID → 选排序方式 →「开始爬取」
3. **视频下载** — 输入 BV 号 →「解析」→ 选择清晰度 →「下载」

> **注意**：未登录状态下只能看到有限评论。建议始终使用已登录的 Cookie。

## 打包

```bash
pyinstaller --onedir --noconsole --name "B站爬虫" ^
  --add-data "my_app_icon.ico;." ^
  --collect-all=bilibili_api ^
  --collect-all=curl_cffi ^
  --collect-all=requests ^
  --hidden-import=PIL._tkinter_finder ^
  --icon=my_app_icon.ico ^
  bilibili_comment_spider.py
```

## 技术栈

| 组件 | 选型 |
|------|------|
| GUI | tkinter / ttk |
| B站 API | bilibili-api-python |
| HTTP | requests + curl_cffi |
| 打包 | PyInstaller |
| 图标 | 自绘 .ico |

## 免责声明

本工具仅供学习和研究使用。使用本工具时请遵守 **哔哩哔哩用户协议** 及相关法律法规。

- 请勿将本工具用于大规模爬取、商业用途或侵犯他人权益的场景
- 下载的视频请仅用于个人学习，勿进行二次分发
- 作者不对因使用本工具产生的任何法律问题承担责任

## 许可证

MIT
