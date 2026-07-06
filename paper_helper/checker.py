"""
Writing Checker — 中文学术论文常见写作问题检测。

检测项：
    1. 重复句子 / 高度相似段落
    2. 模糊表达（"很多""比较""可能""大概""似乎"）
    3. AI 风格句式（"首先...其次...再次...最后""不仅...而且...""综上所述"）
    4. 孤立的参考文献引用（正文引用但在参考文献中不存在）
    5. 段落长度不均衡
    6. 缺少必要的学术成分（研究问题、研究方法、结论等）

支持 .docx 和 .txt 输入。
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Optional
from difflib import SequenceMatcher


# ── Check item data structures ─────────────────────────────────────────────────


@dataclass
class CheckIssue:
    """写作问题记录。"""
    severity: str         # "error" | "warning" | "info"
    category: str         # 问题类别
    location: str         # 位置描述
    description: str      # 问题描述
    detail: str = ""      # 详细内容/样例
    suggestion: str = ""  # 修改建议


@dataclass
class CheckReport:
    """写作检查报告。"""
    file_path: str
    total_words: int = 0
    total_paragraphs: int = 0
    issues: list[CheckIssue] = field(default_factory=list)
    stats: dict = field(default_factory=lambda: {
        "errors": 0, "warnings": 0, "info": 0,
    })
    score: int = 100  # 写作质量分（100 = 完美）

    def summary(self) -> str:
        return (
            f"写作检查完成。质量评分：{self.score}/100。"
            f"共发现 {len(self.issues)} 个问题"
            f"（错误 {self.stats['errors']}，警告 {self.stats['warnings']}，提示 {self.stats['info']}）。"
        )


# ── Detection patterns ─────────────────────────────────────────────────────────


# 模糊表达词库
VAGUE_TERMS = {
    "程度": ["很多", "许多", "大量", "不少", "较多", "较少", "很少"],
    "频率": ["经常", "往往", "偶尔", "时常", "通常", "一般"],
    "程度副词": ["比较", "非常", "十分", "极其", "格外", "相当", "较为"],
    "可能性": ["可能", "也许", "大概", "似乎", "好像", "貌似", "或许", "兴许"],
    "主观判断": ["显然", "明显", "当然", "自然", "必然"],
    "模糊量化": ["一定程度上", "某种意义上", "某种程度上", "一定意义上"],
}

# AI 风格句式
AI_STYLE_PATTERNS = [
    (r'首先[,，].*?其次[,，].*?再次[,，].*?最后[,，]', '\u201c首先...其次...再次...最后\u201d 递进句式'),
    (r'不仅[^，,。.!！?？]{0,30}而且', '\u201c不仅...而且...\u201d 句式'),
    (r'既[^，,。.!！?？]{0,30}又', '\u201c既...又...\u201d 句式'),
    (r'一方面[^，,。.!！?？]{0,50}另一方面', '\u201c一方面...另一方面...\u201d 句式'),
    (r'综上所述[,，]', '\u201c综上所述\u201d 过度使用'),
    (r'总而言之[,，]', '\u201c总而言之\u201d 过度使用'),
    (r'值得注意的是[,，]', '\u201c值得注意的是\u201d 模板化表述'),
    (r'从某种(?:意义|程度)上说[,，]', '\u201c从某种意义上说\u201d 模板化表述'),
    (r'不可否认的是[,，]', '\u201c不可否认的是\u201d 模板化表述'),
    (r'毋庸置疑[,，]', '\u201c毋庸置疑\u201d 过度使用'),
    (r'正因如此[,，]', '\u201c正因如此\u201d 模板化表述'),
    (r'通过(?:以上|上述)分析(?:我们)?(?:可以)?(?:看出|发现|得出)', '\u201c通过以上分析...\u201d 模板化总结'),
    (r'为[^，,。.!！?？]{0,40}提供了(?:有力|重要|坚实)的(?:理论|实证)支撑', '\u201c提供了...支撑\u201d 模板化表述'),
    (r'具有(?:重要|重大)的(?:理论|现实|实践)意义', '\u201c具有重要的...意义\u201d 万能句式'),
]

# 学术论文必要成分检查
REQUIRED_SECTIONS = {
    "研究背景": [r'研究背景', r'背景', r'问题提出'],
    "文献综述": [r'文献综述', r'文献回顾', r'研究现状', r'literature review'],
    "研究问题/假设": [r'研究问题', r'研究假设', r'hypothes[ie]s'],
    "研究方法": [r'研究方法', r'研究设计', r'methodology', r'method'],
    "实证分析/论证": [r'实证', r'分析', r'论证', r'结果', r'result'],
    "研究结论": [r'结论', r'建议', r'启示', r'展望', r'conclusion'],
}

# 孤引检测
CITATION_PATTERN = re.compile(r'\[(\d+(?:[,，\s-]+\d+)*)\]')


# ── Checker ────────────────────────────────────────────────────────────────────


class Checker:
    """学术论文写作质量检查器。

    使用方式::

        checker = Checker()
        report = checker.check("thesis.docx")
        print(report.summary())
        for issue in report.issues:
            print(f"[{issue.severity}] {issue.description}")
    """

    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        self._text = ""
        self._paragraphs: list[str] = []
        self._issues: list[CheckIssue] = []
        self._report: Optional[CheckReport] = None

    # ── Public API ─────────────────────────────────────────────────────────

    def check(self, file_path: str) -> CheckReport:
        """执行全面检查并返回报告。"""
        self._issues = []
        text = self._read_file(file_path)
        if not text:
            return CheckReport(file_path=file_path, issues=self._issues)

        self._text = text
        self._paragraphs = [p.strip() for p in text.split('\n') if p.strip()]

        total_words = len(re.findall(r'[\u4e00-\u9fff]', text))
        self._report = CheckReport(
            file_path=file_path,
            total_words=total_words,
            total_paragraphs=len(self._paragraphs),
        )

        # 执行各项检查
        self._check_repetition()
        self._check_vague_terms()
        self._check_ai_style()
        self._check_orphan_refs()
        self._check_paragraph_balance()
        self._check_required_sections()

        # 汇总
        for issue in self._issues:
            self._report.issues.append(issue)
            key = issue.severity + "s"
            self._report.stats[key] = self._report.stats.get(key, 0) + 1

        # 计算质量分
        self._report.score = self._calculate_score()
        return self._report

    # ── File I/O ───────────────────────────────────────────────────────────

    def _read_file(self, file_path: str) -> str:
        if file_path.endswith('.docx'):
            return self._read_docx(file_path)
        elif file_path.endswith('.txt'):
            return self._read_txt(file_path)
        else:
            try:
                return self._read_txt(file_path)
            except Exception:
                return ""

    def _read_docx(self, file_path: str) -> str:
        try:
            from docx import Document
            doc = Document(file_path)
            return '\n'.join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception:
            return ""

    def _read_txt(self, file_path: str) -> str:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='gbk') as f:
                    return f.read()
            except Exception:
                return ""

    # ── Check 1: Repetition ────────────────────────────────────────────────

    def _check_repetition(self) -> None:
        """检测重复句子和高度相似段落。"""
        # 将正文拆分为句子
        sentences = re.split(r'[。！？!?\n]', self._text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 15]

        # 精确重复
        sentence_counts = Counter(sentences)
        duplicates = {s: c for s, c in sentence_counts.items() if c > 1 and len(s) > 20}

        for sent, count in duplicates.items():
            if len(sent) > 80:
                sent_display = sent[:80] + "..."
            else:
                sent_display = sent
            self._issues.append(CheckIssue(
                severity="warning",
                category="重复句子",
                location="全文",
                description=f"以下句子重复出现 {count} 次：",
                detail=sent_display,
                suggestion="建议删除重复或改写其中一处。如需强调观点，使用不同的表达方式。",
            ))

        # 高度相似段落（相邻段落）
        for i in range(len(self._paragraphs) - 1):
            p1 = self._paragraphs[i]
            p2 = self._paragraphs[i + 1]
            if len(p1) < 30 or len(p2) < 30:
                continue
            sim = SequenceMatcher(None, p1, p2).ratio()
            if sim > self.similarity_threshold:
                self._issues.append(CheckIssue(
                    severity="info",
                    category="相似段落",
                    location=f"第 {i+1}-{i+2} 段",
                    description=f"相邻段落相似度过高（{sim:.0%}），可能存在内容重复。",
                    suggestion="建议合并两段或重写其中一段，避免内容冗余。",
                ))

    # ── Check 2: Vague terms ───────────────────────────────────────────────

    def _check_vague_terms(self) -> None:
        """检测模糊表达。"""
        found_by_category = defaultdict(list)

        for category, terms in VAGUE_TERMS.items():
            for term in terms:
                matches = list(re.finditer(re.escape(term), self._text))
                if matches:
                    # 获取上下文
                    for match in matches[:3]:  # 每类最多3个样例
                        start = max(0, match.start() - 15)
                        end = min(len(self._text), match.end() + 15)
                        ctx = self._text[start:end].replace('\n', ' ')
                        found_by_category[category].append((term, ctx, match.start()))

        for category, items in found_by_category.items():
            term_list = ", ".join([f'"{t}"' for t, _, _ in items])
            examples = "; ".join([ctx for _, ctx, _ in items[:2]])
            self._issues.append(CheckIssue(
                severity="warning" if len(items) > 5 else "info",
                category=f"模糊表达（{category}）",
                location="全文",
                description=f"发现模糊表达词共 {len(items)} 处：{term_list}",
                detail=f"示例上下文：{examples}" if examples else "",
                suggestion='学术论文应使用精确、量化的表述。如将\u201c很多\u201d改为\u201c占比 XX%\u201d或具体数值，将\u201c可能\u201d改为有证据支撑的判断。',
            ))

    # ── Check 3: AI-style phrases ──────────────────────────────────────────

    def _check_ai_style(self) -> None:
        """检测 AI 风格句式。"""
        total_matches = 0

        for pattern, description in AI_STYLE_PATTERNS:
            matches = list(re.finditer(pattern, self._text))
            if matches:
                total_matches += len(matches)
                # 获取样例
                examples = []
                for m in matches[:3]:
                    ctx = self._text[max(0, m.start() - 5):min(len(self._text), m.end() + 20)].replace('\n', ' ')
                    examples.append(ctx)

                self._issues.append(CheckIssue(
                    severity="info",
                    category="AI风格句式",
                    location="全文",
                    description=f'检测到 {len(matches)} 处\u201c{description}\u201d句式',
                    detail="; ".join(examples),
                    suggestion='建议替换为更自然的学术表达。例如：\u201c首先...其次...\u201d可以改为有机的段落过渡。',
                ))

        if total_matches > 10:
            self._issues.append(CheckIssue(
                severity="warning",
                category="AI风格句式（总体）",
                location="全文",
                description=f"全文共检测到 {total_matches} 处 AI 风格句式，可能影响论文的自然度和原创性。",
                suggestion="建议对全文进行深度改写，减少模板化表达，增加个性化的学术论证。",
            ))

    # ── Check 4: Orphan references ─────────────────────────────────────────

    def _check_orphan_refs(self) -> None:
        """检测正文引用与参考文献列表的一致性。"""
        # 查找参考文献区域
        ref_section_start = -1
        for i, para in enumerate(self._paragraphs):
            if re.match(r'^(参考文献|REFERENCES|【参考文献】)\s*$', para, re.IGNORECASE):
                ref_section_start = i
                break

        if ref_section_start < 0:
            return  # 没有参考文献区域，跳过

        # 从正文中提取引用序号（参考文献区域之前的部分）
        body_text = '\n'.join(self._paragraphs[:ref_section_start])
        body_refs = set()
        for match in CITATION_PATTERN.finditer(body_text):
            nums = re.findall(r'\d+', match.group(1))
            body_refs.update(int(n) for n in nums)

        # 从参考文献区域提取序号
        ref_text = '\n'.join(self._paragraphs[ref_section_start + 1:])
        ref_nums = set()
        for match in re.finditer(r'\[(\d+)\]', ref_text):
            ref_nums.add(int(match.group(1)))

        # 正文引用但参考文献中不存在
        orphan_in_body = body_refs - ref_nums
        if orphan_in_body:
            self._issues.append(CheckIssue(
                severity="error",
                category="孤立引用",
                location="正文",
                description=f"正文中引用了以下序号，但在参考文献列表中未找到：{sorted(orphan_in_body)}",
                suggestion="请检查是否遗漏了对应的参考文献条目，或正文引用序号是否有误。",
            ))

        # 参考文献中存在但正文未引用
        orphan_in_refs = ref_nums - body_refs
        if orphan_in_refs:
            self._issues.append(CheckIssue(
                severity="warning",
                category="孤立引用",
                location="参考文献",
                description=f"参考文献中存在以下序号，但正文中未引用：{sorted(orphan_in_refs)}",
                suggestion="请检查是否遗漏了正文中的引用标注，或删除多余的参考文献条目。",
            ))

        # 检查序号连续性
        if ref_nums:
            max_ref = max(ref_nums)
            expected = set(range(1, max_ref + 1))
            missing = expected - ref_nums
            if missing:
                self._issues.append(CheckIssue(
                    severity="info",
                    category="引用序号",
                    location="参考文献",
                    description=f"参考文献序号不连续，缺少以下编号：{sorted(missing)}",
                    suggestion="参考文献序号应按正文出现顺序连续编号。",
                ))

    # ── Check 5: Paragraph balance ─────────────────────────────────────────

    def _check_paragraph_balance(self) -> None:
        """检查段落长度均衡性。"""
        para_lengths = [(i, len(p)) for i, p in enumerate(self._paragraphs) if len(p) > 30]

        if not para_lengths:
            return

        lengths = [pl[1] for pl in para_lengths]
        avg_len = sum(lengths) / len(lengths)

        very_short = [(i + 1, pl[1]) for i, pl in enumerate(para_lengths) if pl[1] < avg_len * 0.2 and pl[1] > 30]
        very_long = [(i + 1, pl[1]) for i, pl in enumerate(para_lengths) if pl[1] > avg_len * 3]

        if very_short:
            examples = ", ".join([f"第{idx}段({l}字)" for idx, l in very_short[:5]])
            self._issues.append(CheckIssue(
                severity="info",
                category="段落结构",
                location="全文",
                description=f"发现 {len(very_short)} 个过短段落（少于平均长度的 20%）：{examples}",
                suggestion="过短的段落可能缺乏充分展开，建议将相关内容合并或扩充论证。",
            ))

        if very_long:
            examples = ", ".join([f"第{idx}段({l}字)" for idx, l in very_long[:3]])
            self._issues.append(CheckIssue(
                severity="info",
                category="段落结构",
                location="全文",
                description=f"发现 {len(very_long)} 个过长段落（超过平均长度的 3 倍）：{examples}",
                suggestion="过长的段落建议拆分，每个段落聚焦一个核心论点。",
            ))

    # ── Check 6: Required sections ─────────────────────────────────────────

    def _check_required_sections(self) -> None:
        """检查是否包含必要的学术成分。"""
        missing = []

        for section_name, patterns in REQUIRED_SECTIONS.items():
            found = False
            for pattern in patterns:
                if re.search(pattern, self._text, re.IGNORECASE):
                    found = True
                    break
            if not found:
                missing.append(section_name)

        if missing:
            self._issues.append(CheckIssue(
                severity="warning" if len(missing) <= 2 else "error",
                category="结构完整性",
                location="全文",
                description=f"论文可能缺少以下必要部分：{'、'.join(missing)}",
                suggestion="完整的学术论文应包含：研究背景、文献综述、研究问题/假设、研究方法、实证分析/论证、研究结论。",
            ))

    # ── Scoring ────────────────────────────────────────────────────────────

    def _calculate_score(self) -> int:
        """计算写作质量分（100 分制）。"""
        score = 100

        # 重复句子：每处 -3
        repeat_issues = [i for i in self._issues if i.category == "重复句子"]
        score -= len(repeat_issues) * 3

        # 模糊表达：每类 -2
        vague_issues = [i for i in self._issues if i.category.startswith("模糊表达")]
        score -= len(vague_issues) * 2

        # 孤立引用：每处错误 -5
        orphan_errors = [i for i in self._issues if i.category == "孤立引用" and i.severity == "error"]
        score -= len(orphan_errors) * 5

        # 孤立引用警告：每处 -2
        orphan_warnings = [i for i in self._issues if i.category == "孤立引用" and i.severity == "warning"]
        score -= len(orphan_warnings) * 2

        # AI风格：超过5处 -5，超过10处 -10
        ai_issues = [i for i in self._issues if i.category == "AI风格句式"]
        ai_count = sum(1 for _ in ai_issues)
        if ai_count > 10:
            score -= 10
        elif ai_count > 5:
            score -= 5

        # 结构缺失：每项 -5
        structure_issues = [i for i in self._issues if i.category == "结构完整性"]
        if structure_issues and structure_issues[0].severity == "error":
            score -= 10
        elif structure_issues:
            score -= 5

        return max(0, min(100, score))


# ── Convenience function ──────────────────────────────────────────────────────


def check_document(file_path: str) -> CheckReport:
    """便捷函数：检查文档写作质量。"""
    checker = Checker()
    return checker.check(file_path)
