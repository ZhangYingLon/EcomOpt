# EcomOpt - 电商运营平台

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PyQt5](https://img.shields.io/badge/PyQt5-5.15.9-41CD52?style=for-the-badge&logo=qt&logoColor=white)](https://www.riverbankcomputing.com/software/pyqt/)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-0078D4?style=for-the-badge)](#)

**融合 Selenium 和 AI 技术的电商运营自动化平台**

支持多平台内容发布 · AI 智能创作 · 批量管理 · 自动化运营

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [使用文档](#-使用文档) • [技术架构](#-技术架构)

</div>

---

## 📖 项目简介

**EcomOpt** 是一个功能强大的电商运营自动化工具，专为内容创作者和电商运营人员设计。通过融合 Selenium 自动化技术和 AI 智能生成能力，帮助用户实现多平台内容的快速创建、优化和发布。

### 🎯 核心价值

- 🚀 **效率提升** - 自动化发布流程，节省 90% 的运营时间
- 🤖 **AI 驱动** - 智能内容生成、优化和标题创作
- 🎨 **友好界面** - 基于 PyQt5 的现代化桌面应用
- 📱 **多平台支持** - 百家号、小红书等主流平台

---

## ✨ 功能特性

### 🤖 AI 智能创作
- 📝 **内容生成** - 基于 AI 自动生成高质量文章内容
- ✨ **内容优化** - 智能优化文案，提升吸引力和可读性
- 🎯 **标题创作** - 针对不同平台生成吸引人的标题
- 🖼️ **图片识别** - 支持图片内容分析和描述生成
- 📊 **多平台适配** - 支持百家号、小红书等不同平台风格

### 🚀 自动化发布
- 📱 **百家号发布** - 自动化百家号内容发布
- 📕 **小红书发布** - 自动化小红书笔记发布
- 📤 **批量发布** - 支持多内容批量发布
- 🔄 **自动登录** - 支持 Cookie 管理和自动登录
- ⏰ **定时发布** - 支持任务计划执行

### 🛠️ 运营管理
- 👥 **账号管理** - 多账号管理和 Cookie 维护
- 📁 **内容管理** - 内容模板管理和批量操作
- 🎨 **模板系统** - 支持自定义内容模板
- 📊 **数据管理** - 本地数据库存储和管理

---

## 🚀 快速开始

### 环境要求

- **Python**: 3.8 或更高版本
- **操作系统**: Windows / Linux / macOS
- **浏览器**: Chrome / Edge（用于 Selenium 自动化）

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/ZhangYingLon/EcomOpt.git
cd EcomOpt
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置 API 密钥**
```bash
# 复制示例配置文件
cp config/settings.example.json config/settings.json

# 编辑配置文件，填入你的 API 密钥
# 支持以下 AI 服务：
# - 阿里通义千问 (dashscope)
# - 百度千帆 (qianfan)
```

4. **启动程序**
```bash
python main.py
```

### Windows 用户

可以直接双击运行：
```bash
启动程序.bat
```

---

## 📝 使用文档

### 配置 AI 服务

在 `config/settings.json` 中配置 AI API 密钥：

```json
{
    "ai": {
        "provider": "dashscope",  // 可选：dashscope, qianfan
        "dashscope": {
            "api_key": "你的通义千问API密钥",
            "model": "qwen-turbo"
        },
        "qianfan": {
            "api_key": "你的百度千帆API密钥",
            "model": "ernie-4.5-turbo-128k"
        }
    }
}
```

### 获取 API 密钥

- **阿里通义千问**: 访问 [阿里云 DashScope](https://dashscope.aliyun.com/)
- **百度千帆**: 访问 [百度智能云千帆](https://cloud.baidu.com/product/wenxinworkshop)

### 基本使用流程

1. **登录系统**
   - 启动程序后选择角色（管理员/运营人员）
   - 输入用户名登录

2. **管理账号**
   - 添加平台账号（百家号/小红书）
   - 获取并保存 Cookie

3. **创建内容**
   - 使用 AI 生成或手动编写内容
   - 优化文案和标题
   - 选择适用平台

4. **发布内容**
   - 选择目标账号
   - 预览内容效果
   - 执行发布

---

## 🏗️ 技术架构

### 项目结构

```
EcomOpt/
├── config/              # 配置文件
│   ├── config.py        # 配置管理类
│   └── settings.json    # 用户配置（不上传到 Git）
├── core/                # 核心服务
│   ├── ai_service.py    # AI 服务
│   └── selenium_manager.py  # Selenium 管理
├── platforms/           # 平台适配
│   ├── base_platform.py     # 基础平台类
│   ├── baijiahao_platform.py  # 百家号
│   └── xiaohongshu_platform.py  # 小红书
├── services/            # 业务服务
│   ├── account_service.py    # 账号服务
│   ├── content_service.py    # 内容服务
│   └── ai_service.py         # AI 服务
├── ui/                  # 用户界面
│   ├── main_window.py   # 主窗口
│   ├── login_window.py  # 登录窗口
│   └── widgets/         # 功能组件
├── models/              # 数据模型
│   ├── database.py      # 数据库管理
│   └── models.py        # 数据模型定义
├── utils/               # 工具类
│   ├── logger.py        # 日志系统
│   └── exceptions.py    # 异常处理
└── tools/               # 工具文件
    ├── chromedriver.exe # Chrome 驱动
    └── stealth.min.js   # 反检测脚本
```

### 技术栈

- **前端界面**: PyQt5
- **自动化**: Selenium 4.x
- **AI 服务**: 
  - 阿里通义千问 (DashScope)
  - 百度千帆 (QianFan)
- **数据库**: SQLite
- **图像处理**: Pillow
- **日志系统**: 自定义 Logger

---

## 📋 依赖说明

主要依赖包：

```
PyQt5==5.15.9        # GUI 框架
selenium==4.15.2     # 浏览器自动化
requests==2.31.0     # HTTP 请求
Pillow==10.1.0       # 图像处理
dashscope>=1.14.0    # 阿里通义千问 SDK
qianfan>=0.3.0       # 百度千帆 SDK
```

完整依赖列表请查看 [requirements.txt](requirements.txt)

---

## ⚙️ 配置说明

### settings.json 配置项

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `ai.provider` | AI 服务提供商 | dashscope |
| `ai.max_tokens` | AI 生成最大 token 数 | 2000 |
| `selenium.headless` | 无头模式 | false |
| `selenium.wait_timeout` | 等待超时时间（秒） | 10 |
| `account.auto_refresh` | 自动刷新账号 | true |
| `account.refresh_interval` | 刷新间隔（秒） | 3600 |

---

## 🔒 安全说明

### 敏感信息保护

本项目已通过 `.gitignore` 排除以下敏感文件：

- ✅ `config/settings.json` - 包含 API 密钥
- ✅ `data/*.db` - 数据库文件
- ✅ `logs/` - 日志文件
- ✅ `.env` - 环境变量文件

### 使用建议

1. **不要在公共仓库中提交 API 密钥**
2. **定期更新 API 密钥**
3. **使用环境变量管理敏感配置**
4. **生产环境使用独立的 API 密钥**

---

## 🤝 贡献指南

欢迎贡献代码、报告问题或提出建议！

### 贡献流程

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

### 开发规范

- 遵循 PEP 8 Python 编码规范
- 添加必要的注释和文档
- 确保代码通过基本测试
- 更新相关文档

---

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

---

## 🙏 致谢

- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) - GUI 框架
- [Selenium](https://www.selenium.dev/) - 浏览器自动化
- [阿里云通义千问](https://dashscope.aliyun.com/) - AI 服务
- [百度千帆](https://cloud.baidu.com/product/wenxinworkshop) - AI 服务

---

## 📧 联系方式

- **GitHub**: [ZhangYingLon](https://github.com/ZhangYingLon)
- **项目地址**: https://github.com/ZhangYingLon/EcomOpt

---

<div align="center">

如果这个项目对你有帮助，请给个 ⭐️ Star 支持一下！

Made with ❤️ by ZhangYingLon

</div>
