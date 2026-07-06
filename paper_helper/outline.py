"""
Outline Generator — 自动生成中文学术论文五级大纲。

生成结构：
    第一章（章） → 一、（节） → （一）（小节） → 1.（小标题） → （1）（要点）

支持根据研究主题自动构建完整论文大纲，每级附带写作指导注释。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional

OUTLINE_TEMPLATES = {
    "实证研究": {
        "structure": [
            ("第一章", "绪论", [
                ("一、", "研究背景与意义", [
                    ("（一）", "研究背景", [
                        ("1.", "现实背景", [("（1）", "现象描述与数据支撑")]),
                        ("1.", "理论背景", [("（1）", "相关理论发展脉络")]),
                    ]),
                    ("（一）", "研究意义", [
                        ("1.", "理论意义", [("（1）", "对学科理论的边际贡献")]),
                        ("1.", "实践意义", [("（1）", "对政策/实践的应用价值")]),
                    ]),
                ]),
                ("一、", "研究问题与研究目标", [
                    ("（一）", "核心研究问题", []),
                    ("（一）", "研究目标", []),
                ]),
                ("一、", "研究方法与技术路线", [
                    ("（一）", "研究方法概述", []),
                    ("（一）", "技术路线图", []),
                ]),
                ("一、", "研究创新点", [
                    ("（一）", "理论创新", []),
                    ("（一）", "方法创新", []),
                    ("（一）", "实践创新", []),
                ]),
            ]),
            ("第二章", "文献综述与理论基础", [
                ("一、", "核心概念界定", [
                    ("（一）", "概念梳理", []),
                    ("（一）", "概念辨析", []),
                ]),
                ("一、", "理论基础", [
                    ("（一）", "理论框架一", []),
                    ("（一）", "理论框架二", []),
                ]),
                ("一、", "国内外研究现状", [
                    ("（一）", "国外研究进展", []),
                    ("（一）", "国内研究进展", []),
                ]),
                ("一、", "文献述评与研究缺口", [
                    ("（一）", "现有研究贡献", []),
                    ("（一）", "研究不足与缺口识别", []),
                    ("（一）", "本文的研究定位", []),
                ]),
            ]),
            ("第三章", "研究设计与数据", [
                ("一、", "理论分析与研究假设", [
                    ("（一）", "理论推导逻辑", []),
                    ("（一）", "研究假设提出", []),
                ]),
                ("一、", "变量选取与测度", [
                    ("（一）", "被解释变量", []),
                    ("（一）", "解释变量", []),
                    ("（一）", "控制变量", []),
                ]),
                ("一、", "模型构建", [
                    ("（一）", "基准回归模型", []),
                    ("（一）", "机制检验模型", []),
                ]),
                ("一、", "数据来源与样本", [
                    ("（一）", "数据来源说明", []),
                    ("（一）", "样本筛选与处理", []),
                    ("（一）", "描述性统计", []),
                ]),
            ]),
            ("第四章", "实证结果与分析", [
                ("一、", "基准回归结果", [
                    ("（一）", "基准回归分析", []),
                    ("（一）", "结果讨论", []),
                ]),
                ("一、", "稳健性检验", [
                    ("（一）", "替换变量", []),
                    ("（一）", "替换模型", []),
                    ("（一）", "缩尾/剔除样本", []),
                ]),
                ("一、", "内生性处理", [
                    ("（一）", "工具变量法", []),
                    ("（一）", "其他方法", []),
                ]),
                ("一、", "异质性分析", [
                    ("（一）", "区域异质性", []),
                    ("（一）", "行业/企业特征异质性", []),
                ]),
                ("一、", "机制检验", [
                    ("（一）", "中介效应检验", []),
                    ("（一）", "调节效应检验", []),
                ]),
            ]),
            ("第五章", "进一步讨论（可选）", [
                ("一、", "拓展分析", []),
                ("一、", "延伸讨论", []),
            ]),
            ("第六章", "研究结论与政策建议", [
                ("一、", "主要研究结论", []),
                ("一、", "政策建议", [
                    ("（一）", "建议一", []),
                    ("（一）", "建议二", []),
                    ("（一）", "建议三", []),
                ]),
                ("一、", "研究局限与展望", [
                    ("（一）", "研究局限性", []),
                    ("（一）", "未来研究方向", []),
                ]),
            ]),
        ]
    },
    "理论研究": {
        "structure": [
            ("第一章", "绪论", [
                ("一、", "研究背景与问题提出", []),
                ("一、", "研究意义", []),
                ("一、", "研究思路与方法", []),
                ("一、", "研究创新点", []),
            ]),
            ("第二章", "文献综述", [
                ("一、", "概念溯源与流变", []),
                ("一、", "经典理论回顾", []),
                ("一、", "当代研究进展", []),
                ("一、", "研究述评", []),
            ]),
            ("第三章", "理论基础与框架", [
                ("一、", "理论根基阐释", []),
                ("一、", "核心概念建构", []),
                ("一、", "理论分析框架", []),
            ]),
            ("第四章", "核心问题论证（可多章）", [
                ("一、", "论证维度一", []),
                ("一、", "论证维度二", []),
                ("一、", "论证维度三", []),
            ]),
            ("第五章", "研究结论与启示", [
                ("一、", "主要结论", []),
                ("一、", "理论贡献", []),
                ("一、", "研究展望", []),
            ]),
        ]
    },
}

# ── Chapter-level writing notes ─────────────────────────────────────────────────

CHAPTER_NOTES = {
    "绪论": '绪论是论文的\u201c门面\u201d，需要清晰回答\u201c研究什么问题、为什么研究、怎么研究\u201d三个问题。建议在完成全文后再回头打磨绪论。',
    "文献综述与理论基础": '文献综述不是文献的\u201c流水账\u201d，而是围绕核心研究问题组织的\u201c对话\u201d。每一段文献回顾都应指向\u201c研究缺口\u201d，为本文研究做好铺垫。',
    "研究设计与数据": '研究设计是实证论文的\u201c骨架\u201d。变量选取需有理论依据，模型构建需清晰交代设定逻辑，数据来源需注明可靠性。',
    "实证结果与分析": '实证结果是论文的\u201c硬核\u201d。不仅要报告系数和显著性，更要解释经济含义。稳健性与内生性是审稿人关注的重点，务必做到充分有力。',
    "进一步讨论": '此章为可选章节，用于补充与核心问题相关但不在主线的拓展性分析，或回应审稿人可能关切的延伸问题。',
    "研究结论与政策建议": '结论部分应凝练核心发现，避免简单重复实证结果。政策建议应具体、可操作，与研究结论一一对应。',
    "理论基础与框架": '理论章节需清晰展示概念之间的逻辑关系，建议使用图示辅助。理论框架应是全文分析的\u201c锚点\u201d，后续论证需始终回扣此框架。',
    "核心问题论证": '论证章节应按逻辑层次展开，每节解决一个子问题。论证过程中需保持概念一致性，避免概念游移。',
}

TOPIC_PATTERNS = {
    r"(?:对|影响|效应|作用)": "实证研究",
    r"(?:定义|内涵|本质|本体|认识论|方法论)": "理论研究",
}

SECTION_NOTES = {
    "研究背景与意义": "建议用数据或政策文件引出研究背景，避免空泛的宏大叙事。",
    "文献综述与文献述评": "建议按主题分类而非按时间排序组织文献。",
    "研究假设提出": "每个假设应有明确的理论推导过程，并标注对应的理论依据。",
    "基准回归结果": "报告系数、标准误、显著性水平，并在括号中说明经济含义。",
    "稳健性检验": "至少包含 2-3 种不同稳健性策略，才能有效说服审稿人。",
}


# ── Data structures ────────────────────────────────────────────────────────────


@dataclass
class OutlineNode:
    """大纲节点。"""
    level: int           # 1=章, 2=节, 3=小节, 4=小标题, 5=要点
    prefix: str          # 编号前缀如 "第一章"、"一、"
    title: str           # 标题文本
    note: str = ""       # 写作指导
    children: list["OutlineNode"] = field(default_factory=list)
    parent: Optional["OutlineNode"] = None

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "prefix": self.prefix,
            "title": self.title,
            "note": self.note,
            "children": [c.to_dict() for c in self.children],
        }

    def to_markdown(self, indent: int = 0) -> str:
        """渲染为 Markdown 大纲。"""
        prefix_map = {1: "#", 2: "##", 3: "###", 4: "####", 5: "#####"}
        md_prefix = prefix_map.get(self.level, "-")
        lines = []
        if self.level <= 5:
            lines.append(f"{md_prefix} {self.prefix}{self.title}")
        else:
            lines.append(f"- **{self.prefix}{self.title}**")
        if self.note:
            lines.append(f"> 写作提示：{self.note}")
            lines.append("")
        for child in self.children:
            lines.append(child.to_markdown(indent + 1))
        return "\n".join(lines)

    def to_text(self, indent: int = 0) -> str:
        """渲染为纯文本大纲。"""
        prefix = "    " * indent
        lines = [f"{prefix}{self.prefix}{self.title}"]
        if self.note:
            lines.append(f"{prefix}    [写作提示] {self.note}")
        for child in self.children:
            lines.append(child.to_text(indent + 1))
        return "\n".join(lines)


# ── Generator ──────────────────────────────────────────────────────────────────


class OutlineGenerator:
    """五级中文学术论文大纲生成器。

    使用方式::

        gen = OutlineGenerator(topic="数字经济对劳动力市场的影响")
        outline = gen.generate()
        print(outline.to_markdown())
    """

    def __init__(self, topic: str, style: Optional[str] = None):
        self.topic = topic.strip()
        self.style = style or self._detect_style()
        self._notes_index = dict(CHAPTER_NOTES)

    def _detect_style(self) -> str:
        for pattern, style in TOPIC_PATTERNS.items():
            if re.search(pattern, self.topic):
                return style
        return "实证研究"

    def generate(self) -> OutlineNode:
        """生成完整大纲，返回根节点。"""
        template = OUTLINE_TEMPLATES.get(self.style, OUTLINE_TEMPLATES["实证研究"])
        root = OutlineNode(level=0, prefix="", title=f"论文大纲：{self.topic}", note=f"论文类型：{self.style}")

        for ch_info in template["structure"]:
            ch_node = self._build_chapter(ch_info)
            root.children.append(ch_node)

        return root

    def _build_chapter(self, ch_info: tuple) -> OutlineNode:
        ch_prefix, ch_title, sections = ch_info
        note = self._notes_index.get(ch_title, "")
        ch_node = OutlineNode(level=1, prefix=ch_prefix, title=ch_title, note=note)

        for sec_info in sections:
            sec_node = self._build_section(sec_info, ch_node)
            ch_node.children.append(sec_node)

        return ch_node

    def _build_section(self, sec_info: tuple, parent: OutlineNode) -> OutlineNode:
        if not sec_info:
            return OutlineNode(level=2, prefix="", title="", parent=parent)

        sec_prefix, sec_title, subs = sec_info
        note = SECTION_NOTES.get(sec_title, "")
        sec_node = OutlineNode(level=2, prefix=sec_prefix, title=sec_title, note=note, parent=parent)

        for sub_info in (subs or []):
            sub_node = self._build_sub(sub_info, sec_node)
            sec_node.children.append(sub_node)

        return sec_node

    def _build_sub(self, sub_info: tuple, parent: OutlineNode) -> OutlineNode:
        if not sub_info:
            return OutlineNode(level=3, prefix="", title="", parent=parent)

        sub_prefix, sub_title, points = sub_info
        sub_node = OutlineNode(level=3, prefix=sub_prefix, title=sub_title, parent=parent)

        for pt_info in (points or []):
            if len(pt_info) == 2:
                pt_prefix, pt_title = pt_info
                pt_children = []
            else:
                pt_prefix, pt_title, pt_children = pt_info
            pt_node = OutlineNode(level=4, prefix=pt_prefix, title=pt_title, parent=sub_node)
            for gc_info in (pt_children or []):
                if len(gc_info) >= 2:
                    gc_node = OutlineNode(level=5, prefix=gc_info[0], title=gc_info[1], parent=pt_node)
                    pt_node.children.append(gc_node)
            sub_node.children.append(pt_node)

        return sub_node

    def to_json(self, root: Optional[OutlineNode] = None) -> str:
        if root is None:
            root = self.generate()
        return json.dumps(root.to_dict(), ensure_ascii=False, indent=2)


# ── Convenience function ───────────────────────────────────────────────────────


def generate_outline(topic: str, style: Optional[str] = None, fmt: str = "text") -> str:
    """便捷函数：根据主题生成大纲。

    Args:
        topic: 研究主题，如 "数字经济对劳动力市场的影响"
        style: 论文类型，可选 "实证研究" 或 "理论研究"，默认自动检测
        fmt: 输出格式，"text" 或 "markdown" 或 "json"

    Returns:
        格式化后的大纲文本
    """
    gen = OutlineGenerator(topic, style)
    root = gen.generate()
    if fmt == "markdown":
        return root.to_markdown()
    elif fmt == "json":
        return gen.to_json(root)
    else:
        return root.to_text()
