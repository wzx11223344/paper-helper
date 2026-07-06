---
slug: paper-helper
displayName: AI论文助手
summary: |
  全周期中文学术写作助手。自动生成五级论文大纲、基于Gap-Analysis的文献综述框架、
  GB/T 7714引文格式检查修复、AI风格句式/模糊表达/重复内容检测。
tags:
  - academic
  - thesis
  - writing
  - research
license: MIT
---

# AI论文助手 (paper-helper)

全周期中文学术写作助手，覆盖从选题到大纲、文献综述、格式检查、写作质量审查的完整流程。

## 功能模块

| 模块 | 功能 | CLI 命令 |
|------|------|----------|
| **outline** | 根据主题自动生成五级学术大纲（章/节/小节/小标题/要点），附带写作指导 | `outline --topic "..."` |
| **lit_review** | Gap-Analysis 文献综述框架，搜索 Semantic Scholar 真实论文，生成引文框架 | `litreview --topic "..."` |
| **formatter** | GB/T 7714 引文格式检查/修复、标题层级一致性检测、中英文间距规范 | `format --file thesis.docx` |
| **checker** | 重复句子、模糊表达、AI句式、孤立引用、段落均衡性、结构完整性检测 | `check --file thesis.docx` |

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 生成论文大纲
python helper.py outline --topic "数字经济对劳动力市场的影响"

# 生成文献综述框架（含真实论文搜索）
python helper.py litreview --topic "碳中和政策的就业效应" -n 30 -o output/lit_review.md

# 检查论文写作问题
python helper.py check --file thesis.docx

# 检查并修复格式问题
python helper.py format --file thesis.docx --fix -o thesis_formatted.docx
```

## 大纲生成示例

```bash
python helper.py outline --topic "人工智能对就业结构的影响" --format markdown

# 输出五级大纲：
# 第一章 绪论
#   一、 研究背景与意义
#     （一） 研究背景
#       1. 现实背景
#         （1） 现象描述与数据支撑
#   > 写作提示：建议用数据或政策文件引出研究背景
```

## 支持的文件格式

- **.docx**: 使用 python-docx 读取 Word 文档
- **.txt**: 纯文本文件（自动检测 UTF-8 / GBK 编码）

## 依赖

- Python 3.8+
- click (CLI 框架)
- rich (终端美化)
- python-docx (Word 文档处理)
- requests (Semantic Scholar API)

## Skill 元数据

当用户在对话中提到"论文大纲""文献综述""检查论文""论文格式""学术写作"等需求时，应触发此 Skill。
