"""Centralized prompts for PDF to Markdown conversion.

This module contains all language-specific prompts used in the conversion
and formatting stages. To add a new language:
1. Add it to the Language enum
2. Add prompts to _CONVERSION_PROMPTS and _FORMATTING_PROMPTS dictionaries
"""

from enum import Enum


class Language(str, Enum):
    """Supported output languages for markdown conversion."""

    ENGLISH = "en"
    CHINESE = "zh"


# Conversion prompts for Qwen3-VL vision model
_CONVERSION_PROMPTS = {
    Language.ENGLISH: """Convert these PDF pages to well-formatted markdown.
Preserve the document structure including:
- Headings and subheadings
- Paragraphs
- Bullet points and numbered lists
- Tables (use markdown table format)
- Any emphasized or bold text

Output only the markdown content, no explanations.""",
    Language.CHINESE: """将这些PDF页面转换为格式良好的markdown。
保留文档结构，包括：
- 标题和副标题
- 段落
- 项目符号和编号列表
- 表格（使用markdown表格格式）
- 任何强调或加粗的文字

重要规则：
- 不要翻译！保持原文的语言（中文内容保持中文，不要翻译成英文）
- 完整保留原文内容，不要省略或改写

仅输出markdown内容，不要添加任何解释说明。""",
}

# Formatting prompts for Claude 3 Haiku
_FORMATTING_PROMPTS = {
    Language.ENGLISH: """Clean up and fix the structure of this markdown document.

Tasks:
1. Fix heading hierarchy (ensure proper H1 → H2 → H3 nesting)
2. Remove artifacts (page numbers, headers/footers if duplicated)
3. Normalize formatting (consistent list styles, table alignment)
4. Remove excessive blank lines while preserving readability
5. Fix any broken tables or lists

Preserve all content - do not summarize or omit text.
Output only the formatted markdown, no explanations.""",
    Language.CHINESE: """清理并修复此markdown文档的结构。

任务：
1. 修复标题层级（确保 H1 → H2 → H3 正确嵌套）
2. 移除文档杂项（重复的页码、页眉/页脚）
3. 规范格式（统一列表样式、表格对齐）
4. 移除多余空行，同时保持可读性
5. 修复任何损坏的表格或列表

重要规则：
- 不要翻译！保持原文的语言（中文内容保持中文，不要翻译成英文）
- 完整保留所有内容，不要总结或省略文字

仅输出格式化后的markdown，不要添加任何解释说明。""",
}


def get_conversion_prompt(language: Language) -> str:
    """Get the conversion prompt for the specified language.

    Args:
        language: Target output language

    Returns:
        Conversion prompt for the vision model

    Raises:
        ValueError: If language is not supported
    """
    if language not in _CONVERSION_PROMPTS:
        raise ValueError(f"Unsupported language: {language}. Supported languages: {[lang.value for lang in Language]}")
    return _CONVERSION_PROMPTS[language]


def get_formatting_prompt(language: Language) -> str:
    """Get the formatting prompt for the specified language.

    Args:
        language: Target output language

    Returns:
        Formatting prompt for the text model

    Raises:
        ValueError: If language is not supported
    """
    if language not in _FORMATTING_PROMPTS:
        raise ValueError(f"Unsupported language: {language}. Supported languages: {[lang.value for lang in Language]}")
    return _FORMATTING_PROMPTS[language]
