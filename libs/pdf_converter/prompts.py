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

# Formatting prompts for Claude 3 Haiku (optimized for Notion markdown)
_FORMATTING_PROMPTS = {
    Language.ENGLISH: """Format this markdown document for Notion with beautiful, clean structure.

Tasks:
1. **Heading hierarchy**: Ensure proper H1 → H2 → H3 nesting, use clear section titles
2. **Remove artifacts**: Delete page numbers, repeated headers/footers, OCR noise
3. **Beautify structure**:
   - Use `>` for quotes and important passages
   - Use `---` dividers between major sections
   - Use bullet lists (`-`) for unordered items
   - Use numbered lists (`1.`) for sequential steps
   - Use **bold** for key terms and emphasis
   - Use `code` for technical terms if applicable
4. **Tables**: Fix broken tables, ensure proper alignment
5. **Spacing**: Add blank lines between sections for readability, remove excessive blanks
6. **Poetry/Verse**: Format poems with proper line breaks using `>` quote blocks

Preserve all content - do not summarize or omit text.
Output only the formatted markdown, no explanations.""",
    Language.CHINESE: """将此markdown文档格式化为适合Notion的美观、清晰的结构。

任务：
1. **标题层级**：确保 H1 → H2 → H3 正确嵌套，使用清晰的章节标题
2. **移除杂项**：删除页码、重复的页眉/页脚、OCR噪音
3. **美化结构**：
   - 使用 `>` 引用块来突出重要段落、诗词、引文
   - 使用 `---` 分隔线区分主要章节
   - 使用无序列表（`-`）列举要点
   - 使用有序列表（`1.`）表示步骤或顺序
   - 使用 **加粗** 强调关键词和重要概念
   - 适当使用 `代码格式` 标注专有名词
4. **表格**：修复损坏的表格，确保对齐
5. **间距**：章节之间添加空行提升可读性，移除多余空行
6. **诗词格式**：使用 `>` 引用块格式化诗词，保持换行美观

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
