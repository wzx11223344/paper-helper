# AI论文助手 (paper-helper)

全周期中文学术写作助手 -- 覆盖选题、大纲、文献综述、格式检查、写作质量审查的完整流程。

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## 功能特性

### 1. 论文大纲生成器 (`outline`)
根据研究主题自动生成五级学术论文大纲：
- 章 (第一章) -> 节 (一、) -> 小节 (（一）) -> 小标题 (1.) -> 要点 (（1）)
- 自动识别论文类型（实证研究/理论研究）
- 每级附带写作指导注释
- 支持 Markdown / 纯文本 / JSON 输出

### 2. 文献综述框架 (`lit_review`)
基于 Gap-Analysis 方法构建文献综述：
- 通过 Semantic Scholar API 搜索真实学术论文
- 自动中英文关键词翻译
- 按主题聚类文献
- 生成研究缺口分析 + 研究定位建议
- 输出 GB/T 7714 格式引文框架

### 3. 格式检查与修复 (`formatter`)
中文学术论文格式规范检测：
- GB/T 7714-2015 引文格式检查
- 标题层级一致性检测（"一、" vs "1." vs "1.1"）
- 中英文间距规范检查
- 全角/半角标点检测
- 段首缩进检测
- 支持自动修复（中英文间距等）

### 4. 写作质量检查 (`checker`)
学术论文常见问题检测：
- 重复句子 / 高度相似段落
- 模糊表达（"很多""比较""可能""似乎"等）
- AI 风格句式（"首先...其次...再次""不仅...而且""综上所述"等）
- 孤立引用（正文引用与参考文献不一致）
- 段落长度均衡性
- 论文结构完整性（研究背景、文献综述、研究方法、结论等）
- 写作质量评分（0-100）

## 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/your-username/paper-helper.git
cd paper-helper

# 安装依赖
pip install -r requirements.txt
```

### 基础用法

```bash
# 查看帮助
python helper.py --help

# 生成论文大纲
python helper.py outline --topic "数字经济对劳动力市场的影响"
python helper.py outline -t "人工智能伦理问题研究" -f markdown -o outline.md

# 生成文献综述框架
python helper.py litreview --topic "碳中和政策的就业效应"
python helper.py litreview -t "数字化转型与企业创新" -n 30 -o lit_review.md

# 检查论文写作问题
python helper.py check --file thesis.docx
python helper.py check -f chapter1.txt

# 检查并修复格式
python helper.py format --file thesis.docx
python helper.py format -f thesis.docx --fix -o thesis_fixed.docx
```

## 示例输出

### 大纲生成 (Markdown)

```markdown
# 第一章 绪论
> 写作提示：绪论是论文的"门面"，需清晰回答"研究什么、为什么、怎么研究"。

## 一、 研究背景与意义

### （一） 研究背景

#### 1. 现实背景

##### （1）现象描述与数据支撑

#### 1. 理论背景

##### （1）相关理论发展脉络

### （一） 研究意义

#### 1. 理论意义

##### （1）对学科理论的边际贡献

...
```

## 项目结构

```
paper-helper/
├── helper.py                # CLI 入口 (click + rich)
├── paper_helper/
│   ├── __init__.py          # 包初始化
│   ├── outline.py           # 大纲生成器
│   ├── lit_review.py        # 文献综述框架
│   ├── formatter.py         # 格式检查与修复
│   └── checker.py           # 写作质量检查
├── SKILL.md                 # Skill 元数据
├── README.md                # 项目文档
└── requirements.txt         # 依赖清单
```

## 依赖

| 包 | 版本 | 用途 |
|---|---|---|
| click | >=8.1.0 | CLI 命令行框架 |
| rich | >=13.0.0 | 终端美化输出 |
| python-docx | >=0.8.11 | Word 文档读写 |
| requests | >=2.28.0 | Semantic Scholar API 调用 |

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request。在提交 PR 之前，请确保：

1. 代码风格与现有代码保持一致
2. 添加适当的文档注释
3. 测试新增或修改的功能
