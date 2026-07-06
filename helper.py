#!/usr/bin/env python3
"""
helper.py — AI 论文助手 CLI 入口

用法:
    python helper.py outline --topic "研究主题"    生成论文大纲
    python helper.py litreview --topic "研究主题"  生成文献综述框架
    python helper.py check --file 论文.docx        检查写作问题
    python helper.py format --file 论文.docx       检查并修复格式
"""

from __future__ import annotations

import sys
import os

# 确保包路径正确
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax

console = Console()


# ── Shared helpers ─────────────────────────────────────────────────────────────


def _print_banner():
    console.print(Panel.fit(
        "[bold cyan]AI 论文助手[/bold cyan] [dim]v1.0.0[/dim]\n"
        "[dim]全周期中文学术写作辅助工具[/dim]",
        border_style="cyan",
    ))


def _check_deps():
    """检查必要的依赖。"""
    missing = []
    try:
        import click  # noqa: F401
    except ImportError:
        missing.append("click")
    try:
        import rich  # noqa: F401
    except ImportError:
        missing.append("rich")
    try:
        import docx  # noqa: F401
    except ImportError:
        missing.append("python-docx (仅 .docx 文件需要)")
    if missing:
        console.print(f"[yellow]缺少依赖: {', '.join(missing)}[/yellow]")
        console.print("[dim]请运行: pip install -r requirements.txt[/dim]")


# ── CLI group ──────────────────────────────────────────────────────────────────


@click.group()
@click.version_option(version="1.0.0", prog_name="paper-helper")
def cli():
    """AI 论文助手 — 全周期中文学术写作辅助工具。"""
    pass


# ── outline ────────────────────────────────────────────────────────────────────


@cli.command()
@click.option("--topic", "-t", required=True, help="研究主题，如：数字经济对劳动力市场的影响")
@click.option("--style", "-s", default=None, help="论文类型：实证研究 / 理论研究（默认自动检测）")
@click.option("--format", "-f", "out_fmt", default="text",
              type=click.Choice(["text", "markdown", "json"]),
              help="输出格式（默认 text）")
@click.option("--output", "-o", default=None, help="输出文件路径（可选）")
def outline(topic, style, out_fmt, output):
    """生成五级中文学术论文大纲。

    示例：
        python helper.py outline --topic "数字经济对劳动力市场的影响"
        python helper.py outline -t "人工智能伦理问题研究" -f markdown -o outline.md
    """
    from paper_helper.outline import generate_outline

    _print_banner()
    console.print(f"[bold]生成大纲[/bold] — 主题：[green]{topic}[/green]")
    if style:
        console.print(f"  论文类型：[dim]{style}[/dim]")
    console.print()

    with console.status("[cyan]正在生成大纲..."):
        result = generate_outline(topic, style=style, fmt=out_fmt)

    if out_fmt == "json":
        console.print(Syntax(result, "json", theme="monokai"))
    elif out_fmt == "markdown":
        console.print(Markdown(result))
    else:
        console.print(result)

    if output:
        with open(output, 'w', encoding='utf-8') as f:
            f.write(result)
        console.print(f"\n[green]大纲已保存至: {output}[/green]")
    else:
        console.print(f"\n[dim]提示：使用 --output/-o 参数可将大纲保存到文件。[/dim]")


# ── litreview ──────────────────────────────────────────────────────────────────


@cli.command()
@click.option("--topic", "-t", required=True, help="研究主题")
@click.option("--papers", "-n", default=20, type=int, help="最大检索论文数（默认 20）")
@click.option("--no-search", is_flag=True, help="不搜索在线论文，仅生成框架模板")
@click.option("--output", "-o", default=None, help="输出文件路径（可选）")
def litreview(topic, papers, no_search, output):
    """生成 Gap-Analysis 文献综述框架（含真实论文搜索）。

    示例：
        python helper.py litreview --topic "数字经济与就业"
        python helper.py litreview -t "碳中和政策评估" -n 30 -o lit_review.md
    """
    from paper_helper.lit_review import build_lit_review

    _print_banner()
    console.print(f"[bold]文献综述框架[/bold] — 主题：[green]{topic}[/green]")
    console.print(f"  检索上限：[dim]{papers} 篇[/dim]")
    if no_search:
        console.print(f"  在线搜索：[dim]已关闭（仅生成模板框架）[/dim]")
    console.print()

    with console.status("[cyan]正在构建文献综述框架（搜索论文中...）"):
        result = build_lit_review(topic, max_papers=papers, search_papers=not no_search)

    if output:
        with open(output, 'w', encoding='utf-8') as f:
            f.write(result)
        console.print(f"[green]文献综述框架已保存至: {output}[/green]")
        # 也打印摘要
        lines = result.split('\n')
        console.print('\n'.join(lines[:40]))
        console.print(f"\n[dim]... 完整内容请查看 {output}[/dim]")
    else:
        console.print(Markdown(result))


# ── check ──────────────────────────────────────────────────────────────────────


@cli.command()
@click.option("--file", "-f", "file_path", required=True, help="待检查的文件（支持 .docx 和 .txt）")
def check(file_path):
    """检查论文中的常见写作问题。

    检查项：重复句子、模糊表达、AI风格句式、孤立引用、段落结构、必要成分。

    示例：
        python helper.py check --file thesis.docx
        python helper.py check -f chapter1.txt
    """
    from paper_helper.checker import check_document

    _print_banner()
    _check_deps()

    if not os.path.exists(file_path):
        console.print(f"[red]文件不存在: {file_path}[/red]")
        sys.exit(1)

    console.print(f"[bold]写作质量检查[/bold] — 文件：[green]{file_path}[/green]\n")

    with console.status("[cyan]正在分析论文..."):
        report = check_document(file_path)

    # 基本信息
    console.print(f"总字数：[bold]{report.total_words}[/bold]   "
                  f"段落数：[bold]{report.total_paragraphs}[/bold]   "
                  f"质量评分：[bold]{_score_color(report.score)}[/bold]")
    console.print()

    if not report.issues:
        console.print(Panel.fit("[green]未发现明显问题，论文写作质量良好！[/green]", border_style="green"))
        return

    # 按严重程度分组
    severity_order = {"error": 0, "warning": 1, "info": 2}
    severities = {"error": "错误", "warning": "警告", "info": "提示"}
    colors = {"error": "red", "warning": "yellow", "info": "dim"}

    sorted_issues = sorted(report.issues, key=lambda x: severity_order.get(x.severity, 99))

    for issue in sorted_issues:
        label = severities.get(issue.severity, issue.severity)
        color = colors.get(issue.severity, "white")
        cat = issue.category

        console.print(f"[{color}]■ [{label}][/{color}] [bold]{cat}[/bold] — {issue.location}")
        console.print(f"  {issue.description}")
        if issue.detail:
            console.print(f"  [dim]详情: {issue.detail}[/dim]")
        if issue.suggestion:
            console.print(f"  [green]建议: {issue.suggestion}[/green]")
        console.print()

    # 总结
    console.print(f"[bold]{report.summary()}[/bold]")


def _score_color(score):
    if score >= 90:
        return f"[green]{score}[/green]"
    elif score >= 70:
        return f"[yellow]{score}[/yellow]"
    else:
        return f"[red]{score}[/red]"


# ── format ─────────────────────────────────────────────────────────────────────


@cli.command()
@click.option("--file", "-f", "file_path", required=True, help="待检查/修复的文件（支持 .docx 和 .txt）")
@click.option("--fix", is_flag=True, help="自动修复可修复的格式问题")
@click.option("--output", "-o", default=None, help="修复后输出文件路径（与 --fix 一起使用）")
def format(file_path, fix, output):
    """检查并格式化论文（GB/T 7714引文、标题层级、中英文间距等）。

    示例：
        python helper.py format --file thesis.docx                # 仅检查
        python helper.py format --file thesis.docx --fix          # 检查并自动修复
        python helper.py format -f thesis.txt --fix -o fixed.txt  # 指定输出
    """
    from paper_helper.formatter import check_format, format_document

    _print_banner()
    _check_deps()

    if not os.path.exists(file_path):
        console.print(f"[red]文件不存在: {file_path}[/red]")
        sys.exit(1)

    console.print(f"[bold]格式检查[/bold] — 文件：[green]{file_path}[/green]")

    if fix:
        console.print(f"  模式：[cyan]检查 + 自动修复[/cyan]\n")
        with console.status("[cyan]正在检查并修复..."):
            report = format_document(file_path, output=output)
    else:
        console.print(f"  模式：[dim]仅检查（使用 --fix 启用自动修复）[/dim]\n")
        with console.status("[cyan]正在分析格式..."):
            report = check_format(file_path)

    console.print(f"引用数：[bold]{report.stats.get('total_citations', 0)}[/bold]   "
                  f"标题数：[bold]{report.stats.get('total_headings', 0)}[/bold]")
    console.print()

    if not report.issues:
        console.print(Panel.fit("[green]格式检查通过，未发现问题！[/green]", border_style="green"))
        return

    severities = {"error": "错误", "warning": "警告", "info": "提示"}
    colors = {"error": "red", "warning": "yellow", "info": "dim"}

    for issue in report.issues:
        label = severities.get(issue.severity, issue.severity)
        color = colors.get(issue.severity, "white")
        console.print(f"[{color}]■ [{label}][/{color}] [bold]{issue.category}[/bold] — {issue.location}")
        console.print(f"  {issue.description}")
        if issue.suggestion:
            console.print(f"  [green]修复: {issue.suggestion}[/green]")
        console.print()

    console.print(f"[bold]{report.summary()}[/bold]")


# ── Main ───────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    cli()
