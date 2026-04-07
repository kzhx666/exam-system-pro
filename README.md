# 智考 Pro (Exam System Pro) V3.1 🚀

这是一个专为现代化教学场景打造的轻量级、高性能在线考试系统。无需复杂的数据库配置，基于 Docker 一键部署，特别适合中职院校、高校教师以及培训机构用于快速组织随堂测试或期末模拟考。

![系统状态](https://img.shields.io/badge/Status-Active-success)
![部署方式](https://img.shields.io/badge/Deploy-Docker-blue)
![后端技术](https://img.shields.io/badge/Backend-FastAPI-009688)
![开源协议](https://img.shields.io/badge/License-MIT-green)

## ✨ 核心特性 (Features)

* **📝 Markdown 极速出题**：告别繁琐的表单录入！直接粘贴按特定规则排版的 Markdown 文本（支持插入图片），系统自动解析为交互式试卷。
* **👥 智能名单匹配**：后台可预设学生名单，前台考试终端支持下拉模糊搜索与选择，防止学生填错姓名，同时兼容外部人员手动输入。
* **⚡ 现代化交互界面**：采用 Glassmorphism（毛玻璃）设计、高对比度排版与丝滑动画，同屏利用率极高，专为大屏幕和多设备展示优化。
* **📊 实时自动批改与后台统计**：学生交卷瞬间出分并展示排名；教师后台提供直观的答题对错统计图表，支持随时一键删除无效成绩。
* **🔍 沉浸式解析页面**：考试结束后，自动生成带原题、正确答案与深度解析的独立页面，方便课堂大屏投屏讲评。
* **🔄 无缝修改与重载**：发现题目有误？后台支持一键回填编辑 Markdown 源码与重设分值，保存即时生效，无需重新发布链接。

## 🛠️ 技术栈 (Tech Stack)

* **后端**：Python + FastAPI + SQLAlchemy
* **数据库**：SQLite (轻量无依赖，数据持久化极简)
* **前端**：原生 HTML5 + CSS3 + Vanilla JavaScript (零构建工具，极致轻量)
* **容器化**：Docker + Docker Compose

## 🚀 快速部署 (Deployment)

仅需一台安装了 Docker 和 Docker Compose 的服务器（VPS），即可在 1 分钟内完成部署。

```bash
# 1. 克隆本仓库到服务器
git clone [https://github.com/kzhx666/exam-system-pro.git](https://github.com/kzhx666/exam-system-pro.git)
cd exam-system-pro

# 2. 一键构建并启动服务后台运行
docker-compose up -d --build
```

系统默认运行在 `8000` 端口。访问以下链接即可使用：
* **教师管理后台**：`http://你的服务器IP:8000/admin` 
*(⚠️ 默认安全密码为 `123456`，强烈建议在实际投入生产环境前，修改 `backend/templates/admin.html` 中的密码验证逻辑！)*

## ✍️ 出题语法规范 (Markdown Syntax)

系统采用高度优化的正则解析引擎，出题时请严格遵守以下 Markdown 格式：

### 1. 单选题 / 多选题

```markdown
**1. [单选]** 这里是题干内容（可以换行，可以插图）
![图片说明](https://图片直链.jpg)
A. 选项A的内容
B. 选项B的内容
C. 选项C的内容
D. 选项D的内容
<details><summary>🔎 点击查看答案与解析</summary><blockquote><b>答案：</b>A<br><b>解析：</b>这里写详细的解析内容。</blockquote></details>
```

### 2. 判断题

```markdown
**2. [判断]** 这里是判断题的题干内容。
正确
错误
<details><summary>🔎 点击查看答案与解析</summary><blockquote><b>答案：</b>正确<br><b>解析：</b>这里写详细的解析内容。</blockquote></details>
```

## 📂 目录结构 (Structure)

```text
exam-system-pro/
├── backend/
│   ├── main.py              # FastAPI 核心逻辑与 API 路由
│   └── templates/           # 前端 UI 视图库
│       ├── admin.html       # 教师发布与管理中心
│       ├── index.html       # 学生考试终端 V3.1
│       ├── dashboard.html   # 成绩统计监控大屏
│       └── analysis.html    # 错题讲评解析页面
├── data/                    # SQLite 数据库挂载目录 (已被 gitignore 保护)
├── docker-compose.yml       # Docker 编排文件
├── requirements.txt         # Python 依赖清单
└── README.md                # 项目说明文档
```

## 🔒 数据安全提示
本仓库已配置 `.gitignore`，默认忽略 `data/` 目录下的所有 `.db` 数据库文件。当您执行 `git push` 备份自己修改的代码时，真实的考试数据绝对不会被公开上传至云端。

## 📄 协议 (License)
本项目采用 [MIT License](https://opensource.org/licenses/MIT) 开源协议。欢迎广大教师与开发者 Fork 学习、修改或将其用于自己的教学实践中。
