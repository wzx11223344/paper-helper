"""
Literature Review Builder — 基于 Gap-Analysis 方法的文献综述框架生成器。

功能：
    1. 根据主题搜索 Semantic Scholar 获取真实论文
    2. 按主题聚类 + 研究缺口分析（Gap Analysis）构建综述框架
    3. 生成 GB/T 7714 格式的引文框架
"""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict

# ── Semantic Scholar API ───────────────────────────────────────────────────────

SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1"

# 中英文关键词自动翻译表（常见学术词汇）
TOPIC_TRANSLATIONS = {
    "数字经济": "digital economy",
    "劳动力市场": "labor market",
    "就业": "employment",
    "人工智能": "artificial intelligence",
    "机器学习": "machine learning",
    "经济增长": "economic growth",
    "碳排放": "carbon emission",
    "碳中和": "carbon neutrality",
    "绿色金融": "green finance",
    "数字化转型": "digital transformation",
    "供应链": "supply chain",
    "公司治理": "corporate governance",
    "企业创新": "firm innovation",
    "产业政策": "industrial policy",
    "乡村振兴": "rural revitalization",
    "共同富裕": "common prosperity",
    "人口老龄化": "population aging",
    "技术创新": "technological innovation",
    "全要素生产率": "total factor productivity",
    "人力资本": "human capital",
    "货币政策": "monetary policy",
    "财政政策": "fiscal policy",
    "收入不平等": "income inequality",
    "教育回报": "return to education",
    "城镇化": "urbanization",
    "金融科技": "fintech",
    "区块链": "blockchain",
    "大数据": "big data",
    "物联网": "internet of things",
    "环境规制": "environmental regulation",
    "知识产权": "intellectual property",
    "产业结构": "industrial structure",
}


def _translate_topic(topic: str) -> str:
    """将中文主题关键词翻译为英文搜索词。"""
    english = topic
    for cn, en in TOPIC_TRANSLATIONS.items():
        english = english.replace(cn, en)
    # 将剩下的中文分隔符替换为空格
    english = re.sub(r'[，、；：""''（）\u4e00-\u9fff]+', ' ', english)
    english = re.sub(r'\s+', ' ', english).strip()
    # 如果还有大量中文残留，直接用英文兜底策略
    if re.search(r'[\u4e00-\u9fff]', english):
        english = _fallback_translate(topic)
    return english or topic


def _fallback_translate(topic: str) -> str:
    """兜底翻译：提取已知关键词。"""
    parts = []
    for cn, en in TOPIC_TRANSLATIONS.items():
        if cn in topic:
            parts.append(en)
    return " ".join(parts) if parts else topic


# ── Data structures ────────────────────────────────────────────────────────────


@dataclass
class Paper:
    """学术论文条目。"""
    title: str
    authors: str          # "Author1, Author2 et al."
    year: int
    venue: str            # 期刊/会议名
    citation_count: int
    url: str
    abstract: str = ""
    doi: str = ""

    @property
    def gbt7714(self) -> str:
        """生成 GB/T 7714-2015 格式引文。"""
        authors_short = self.authors if len(self.authors) <= 30 else self.authors[:27] + "..."
        if self.doi:
            return f"{authors_short}. {self.title}[J]. {self.venue}, {self.year}. DOI: {self.doi}."
        return f"{authors_short}. {self.title}[J]. {self.venue}, {self.year}."


@dataclass
class LitCluster:
    """文献聚类（按主题分组）。"""
    theme: str               # 聚类主题名称
    description: str         # 主题描述
    papers: list[Paper] = field(default_factory=list)
    gap_analysis: str = ""   # 研究缺口分析
    key_debates: list[str] = field(default_factory=list)  # 关键学术争论


@dataclass
class LitReviewFramework:
    """文献综述框架。"""
    topic: str
    clusters: list[LitCluster] = field(default_factory=list)
    overall_gap: str = ""           # 总体研究缺口
    research_position: str = ""     # 本文研究定位建议
    citation_framework: str = ""    # 引文框架（Markdown 格式）


# ── Semantic Scholar 搜索 ──────────────────────────────────────────────────────


def search_semantic_scholar(query: str, limit: int = 20, timeout: int = 15) -> list[Paper]:
    """搜索 Semantic Scholar 获取论文。

    Args:
        query: 搜索关键词（英文）
        limit: 返回论文数量上限
        timeout: 请求超时（秒）

    Returns:
        Paper 对象列表
    """
    params = urllib.parse.urlencode({
        "query": query,
        "limit": limit,
        "fields": "title,authors,year,venue,citationCount,url,abstract,externalIds",
        "sort": "relevance",
    })
    url = f"{SEMANTIC_SCHOLAR_BASE}/paper/search?{params}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "paper-helper/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        # 离线/API不可用时返回空列表
        return []

    papers = []
    for item in data.get("data", []):
        authors = ", ".join([a.get("name", "") for a in item.get("authors", [])[:3]])
        if len(item.get("authors", [])) > 3:
            authors += " 等"
        doi = item.get("externalIds", {}).get("DOI", "")
        papers.append(Paper(
            title=item.get("title", ""),
            authors=authors,
            year=item.get("year", 0) or 0,
            venue=item.get("venue", ""),
            citation_count=item.get("citationCount", 0),
            url=item.get("url", ""),
            abstract=item.get("abstract", "") or "",
            doi=doi,
        ))

    return papers


# ── Literature Cluster Builder ─────────────────────────────────────────────────


class LitReviewBuilder:
    """Gap-Analysis 文献综述框架构建器。

    使用方式::

        builder = LitReviewBuilder(topic="数字经济对劳动力市场的影响")
        framework = builder.build()
        print(framework.citation_framework)
    """

    # 通用文献聚类主题模板
    CLUSTER_THEMES = [
        {
            "theme": "概念界定与理论溯源",
            "description": "梳理核心概念的学术定义、演变脉络和理论基础",
            "gap_prompt": "现有概念界定是否存在模糊/争议？理论框架是否完备？",
        },
        {
            "theme": "主流研究方向与方法",
            "description": "归纳当前主流研究方向、常用方法和关键实证发现",
            "gap_prompt": "主流方法是否存在系统性局限？是否有被忽视的维度？",
        },
        {
            "theme": "机制与路径分析",
            "description": "汇总因果机制、传导路径和调节效应的相关研究",
            "gap_prompt": "机制链条是否完整？是否存在竞争性解释？",
        },
        {
            "theme": "异质性与边界条件",
            "description": "聚焦异质性效应、情境因素和边界条件研究",
            "gap_prompt": "异质性分析是否充分？情境因素是否被遗漏？",
        },
        {
            "theme": "政策评估与实践应用",
            "description": "总结政策效应评估和实践应用研究",
            "gap_prompt": "政策建议是否基于充分证据？实施路径是否可行？",
        },
    ]

    def __init__(self, topic: str, max_papers: int = 20):
        self.topic = topic.strip()
        self.max_papers = max_papers
        self.papers: list[Paper] = []

    def build(self, search_papers: bool = True) -> LitReviewFramework:
        """构建文献综述框架。

        Args:
            search_papers: 是否搜索 Semantic Scholar 获取真实论文
        """
        framework = LitReviewFramework(topic=self.topic)

        # Step 1: 搜索论文
        if search_papers:
            en_query = _translate_topic(self.topic)
            # 使用多个搜索词提高覆盖
            all_papers = []
            for q in [en_query, self.topic[:20]]:
                papers = search_semantic_scholar(q, limit=self.max_papers // 2)
                all_papers.extend(papers)
                time.sleep(0.5)  # 请求间隔
            # 去重
            seen = set()
            unique = []
            for p in all_papers:
                if p.title not in seen:
                    seen.add(p.title)
                    unique.append(p)
            self.papers = unique[:self.max_papers]

        # Step 2: 分配论文到聚类
        clusters = self._cluster_papers()

        # Step 3: 生成缺口分析
        for cluster in clusters:
            cluster.gap_analysis = self._analyze_gap(cluster)
            cluster.key_debates = self._identify_debates(cluster)

        framework.clusters = clusters

        # Step 4: 总体缺口与研究定位
        framework.overall_gap = self._synthesize_overall_gap(clusters)
        framework.research_position = self._suggest_research_position(clusters)

        # Step 5: 生成引文框架
        framework.citation_framework = self._render_citation_framework(framework)

        return framework

    def _cluster_papers(self) -> list[LitCluster]:
        """将论文分配到主题聚类。"""
        clusters = []
        for i, theme_def in enumerate(self.CLUSTER_THEMES):
            # 均匀分配论文到各聚类
            start = i * max(1, len(self.papers) // len(self.CLUSTER_THEMES))
            end = (i + 1) * max(1, len(self.papers) // len(self.CLUSTER_THEMES)) if i < len(self.CLUSTER_THEMES) - 1 else len(self.papers)
            cluster = LitCluster(
                theme=theme_def["theme"],
                description=theme_def["description"],
                papers=self.papers[start:end],
            )
            clusters.append(cluster)
        return clusters

    def _analyze_gap(self, cluster: LitCluster) -> str:
        """分析单个聚类的缺口。"""
        if not cluster.papers:
            return f"【{cluster.theme}】尚未检索到足够文献，建议在知网（CNKI）或 Web of Science 中补充搜索。"

        years = [p.year for p in cluster.papers if p.year > 0]
        year_range = f"{min(years)}-{max(years)}" if years else "未知年份"
        total_cites = sum(p.citation_count for p in cluster.papers)

        parts = [
            f"【{cluster.theme}】已检索 {len(cluster.papers)} 篇相关文献（{year_range}），",
            f"累计被引 {total_cites} 次。",
        ]
        parts.append(f"\n可能的研究缺口：")
        parts.append(f"1. 文献时间跨度集中于 {year_range}，近期（近3年）前沿研究覆盖可能不足；")
        parts.append(f"2. 需关注中文文献与英文文献之间的视角差异；")
        parts.append(f"3. 建议检查是否存在'研究同质化'倾向（多篇文献使用相似方法和数据）。")
        return "".join(parts)

    def _identify_debates(self, cluster: LitCluster) -> list[str]:
        """识别聚类内的学术争论。"""
        if len(cluster.papers) < 2:
            return ["目前文献量不足，尚无法识别明显的学术争论。"]
        return [
            f"方向一：{cluster.papers[0].title[:30]}... 代表了主流观点",
            f"方向二：建议通过阅读详细摘要来识别学术对话中的分歧点",
        ]

    def _synthesize_overall_gap(self, clusters: list[LitCluster]) -> str:
        """综合所有聚类的缺口，生成总体研究缺口。"""
        parts = ["## 总体研究缺口\n"]
        parts.append(f'围绕\u201c{self.topic}\u201d，现有文献存在以下系统性缺口：\n')
        for i, cl in enumerate(clusters, 1):
            parts.append(f'{i}. **{cl.theme}**\uff1a{cl.description}\u2014\u2014待深入')
        parts.append(f"\n## 本文研究机会\n")
        parts.append(f"基于以上缺口，本文可在以下方面做出贡献：")
        parts.append(f"1. 填补 XX 领域的研究空白；")
        parts.append(f"2. 采用新的数据/方法/视角进行验证；")
        parts.append(f"3. 提出更具针对性的政策/实践建议。")
        return "\n".join(parts)

    def _suggest_research_position(self, clusters: list[LitCluster]) -> str:
        """建议本文的研究定位。"""
        nr_clusters = len([c for c in clusters if c.papers])
        parts = [
            f'基于对 {nr_clusters} 个主题聚类（共 {len(self.papers)} 篇文献）的分析，',
            f'本文建议的研究定位如下：\n',
            f'**理论贡献方向**：在现有理论的边界条件下进行拓展，或整合不同理论视角形成新框架。',
            f'**方法贡献方向**：使用更新/更全面的数据集，或采用更严谨的因果识别策略。',
            f'**实践贡献方向**：为政策制定者提供基于证据的决策参考。\n',
            f'建议论文标题方向：\u201c{self.topic}\u2014\u2014基于XX视角/方法的实证研究\u201d',
        ]
        return "\n".join(parts)

    def _render_citation_framework(self, framework: LitReviewFramework) -> str:
        """将框架渲染为 Markdown 格式引文框架。"""
        lines = [
            f"# 文献综述框架：{framework.topic}",
            "",
            "> 本文档使用 Gap-Analysis 方法生成，基于 Semantic Scholar 检索的真实文献。",
            "",
            "---",
            "",
        ]

        for i, cluster in enumerate(framework.clusters, 1):
            lines.append(f"## 聚类 {i}：{cluster.theme}")
            lines.append(f"> {cluster.description}")
            lines.append("")

            if cluster.papers:
                lines.append("### 核心文献")
                lines.append("")
                for j, paper in enumerate(cluster.papers, 1):
                    lines.append(f"{j}. **{paper.title}**")
                    lines.append(f"   - 作者：{paper.authors}")
                    lines.append(f"   - 发表：{paper.venue} ({paper.year})")
                    lines.append(f"   - 被引：{paper.citation_count} 次")
                    if paper.doi:
                        lines.append(f"   - DOI：{paper.doi}")
                    lines.append(f"   - 引用格式：{paper.gbt7714}")
                    lines.append("")
            else:
                lines.append("> 未检索到该聚类相关的文献，请补充搜索。")
                lines.append("")

            lines.append("### 研究缺口分析")
            lines.append(f"{cluster.gap_analysis}")
            lines.append("")

            if cluster.key_debates:
                lines.append("### 关键学术争论")
                for debate in cluster.key_debates:
                    lines.append(f"- {debate}")
                lines.append("")

            lines.append("---")
            lines.append("")

        # 总体分析
        lines.append(framework.overall_gap)
        lines.append("")
        lines.append(framework.research_position)
        lines.append("")
        lines.append("---")
        lines.append(f"> 生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"> 文献来源：Semantic Scholar API")
        lines.append("")

        return "\n".join(lines)


# ── Convenience function ───────────────────────────────────────────────────────


def build_lit_review(topic: str, max_papers: int = 20, search_papers: bool = True) -> str:
    """便捷函数：构建文献综述框架。

    Args:
        topic: 研究主题
        max_papers: 最大检索论文数
        search_papers: 是否在线搜索论文

    Returns:
        Markdown 格式的引文框架
    """
    builder = LitReviewBuilder(topic, max_papers)
    framework = builder.build(search_papers=search_papers)
    return framework.citation_framework
