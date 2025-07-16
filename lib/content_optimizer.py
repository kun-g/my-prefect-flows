"""
内容优化器 - 智能文本截断和优化
"""

import re
from dataclasses import dataclass


@dataclass
class TextChunk:
    """文本块"""

    content: str
    priority: int  # 优先级，数值越高越重要
    tokens: int


class ContentOptimizer:
    """
    智能内容优化器
    实现语义保持的文本截断和优化
    """

    def __init__(self, max_tokens: int = 4000, preserve_ratio: float = 0.8):
        self.max_tokens = max_tokens
        self.preserve_ratio = preserve_ratio  # 保留原文比例

    def estimate_tokens(self, text: str) -> int:
        """估算文本的token数量（简单方法：4字符≈1token）"""
        return len(text) // 4

    def extract_key_sections(self, content: str) -> list[TextChunk]:
        """
        提取关键段落并按重要性排序
        """
        chunks = []

        # 按段落分割
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

        for paragraph in paragraphs:
            if len(paragraph) < 20:  # 跳过太短的段落
                continue

            priority = self._calculate_priority(paragraph)
            tokens = self.estimate_tokens(paragraph)

            chunks.append(TextChunk(content=paragraph, priority=priority, tokens=tokens))

        # 按优先级排序
        chunks.sort(key=lambda x: x.priority, reverse=True)
        return chunks

    def _calculate_priority(self, paragraph: str) -> int:
        """
        计算段落重要性得分
        """
        score = 0
        text_lower = paragraph.lower()

        # 关键词权重
        technical_keywords = [
            "api",
            "function",
            "class",
            "method",
            "algorithm",
            "code",
            "example",
            "implementation",
            "solution",
            "error",
            "bug",
            "performance",
            "optimization",
            "算法",
            "函数",
            "方法",
            "实现",
            "解决方案",
            "代码",
            "示例",
            "性能",
            "优化",
        ]

        important_keywords = [
            "important",
            "key",
            "main",
            "primary",
            "core",
            "essential",
            "critical",
            "重要",
            "关键",
            "主要",
            "核心",
            "本质",
            "关键点",
        ]

        conclusion_keywords = [
            "conclusion",
            "summary",
            "result",
            "finally",
            "in short",
            "overall",
            "总结",
            "结论",
            "最终",
            "综上",
            "总的来说",
        ]

        # 计算关键词密度
        for keyword in technical_keywords:
            score += text_lower.count(keyword) * 2

        for keyword in important_keywords:
            score += text_lower.count(keyword) * 3

        for keyword in conclusion_keywords:
            score += text_lower.count(keyword) * 4

        # 段落长度加分（适中长度的段落通常更重要）
        length = len(paragraph)
        if 100 <= length <= 500:
            score += 2
        elif 50 <= length <= 800:
            score += 1

        # 包含代码块的段落加分
        if "```" in paragraph or "`" in paragraph:
            score += 3

        # 包含数字和数据的段落加分
        if re.search(r"\d+%|\d+\.\d+|\d+倍|\d+个", paragraph):
            score += 2

        # 标题样式的段落加分
        if paragraph.startswith("#") or paragraph.isupper():
            score += 2

        return score

    def smart_truncate(self, content: str, title: str = "") -> str:
        """
        智能截断文本，保持语义完整性
        """
        total_tokens = self.estimate_tokens(content)

        # 如果内容已经在限制内，直接返回
        if total_tokens <= self.max_tokens:
            return content

        # 提取关键段落
        chunks = self.extract_key_sections(content)

        # 计算需要保留的token数量
        target_tokens = int(self.max_tokens * self.preserve_ratio)

        # 选择最重要的段落
        selected_chunks = []
        current_tokens = 0

        # 如果有标题，优先保留
        if title:
            title_tokens = self.estimate_tokens(title)
            if title_tokens < target_tokens // 10:  # 标题不超过总量的10%
                current_tokens += title_tokens

        for chunk in chunks:
            if current_tokens + chunk.tokens <= target_tokens:
                selected_chunks.append(chunk)
                current_tokens += chunk.tokens
            elif current_tokens < target_tokens * 0.8:  # 还有空间时，尝试截断段落
                remaining_tokens = target_tokens - current_tokens
                truncated_content = self._truncate_paragraph(chunk.content, remaining_tokens)
                if truncated_content:
                    selected_chunks.append(
                        TextChunk(content=truncated_content, priority=chunk.priority, tokens=remaining_tokens)
                    )
                break

        # 按原文顺序重排（保持逻辑流程）
        if selected_chunks:
            # 重新排序以保持原文逻辑
            result_content = self._reorder_chunks(content, selected_chunks)

            # 添加截断提示
            if current_tokens < total_tokens * 0.9:
                result_content += "\n\n[内容已智能截断，保留核心信息]"

            return result_content
        else:
            # 如果没有选中任何段落，返回开头部分
            return self._simple_truncate(content, target_tokens)

    def _truncate_paragraph(self, paragraph: str, max_tokens: int) -> str | None:
        """
        截断单个段落，保持句子完整性
        """
        if self.estimate_tokens(paragraph) <= max_tokens:
            return paragraph

        # 按句子分割
        sentences = re.split(r"[。！？\.\!\?]", paragraph)

        result = ""
        current_tokens = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_tokens = self.estimate_tokens(sentence)

            if current_tokens + sentence_tokens <= max_tokens:
                result += sentence + "。"
                current_tokens += sentence_tokens
            else:
                break

        return result if result else None

    def _simple_truncate(self, content: str, max_tokens: int) -> str:
        """
        简单截断（按字符数）
        """
        max_chars = max_tokens * 4  # 估算字符数
        if len(content) <= max_chars:
            return content

        # 在句号处截断
        truncated = content[:max_chars]
        last_period = truncated.rfind("。")

        if last_period > max_chars * 0.8:  # 如果句号位置合理
            return truncated[: last_period + 1] + "\n\n[内容已截断]"
        else:
            return truncated + "...\n\n[内容已截断]"

    def _reorder_chunks(self, original_content: str, chunks: list[TextChunk]) -> str:
        """
        按原文顺序重新排列选中的文本块
        """
        # 简单实现：按优先级保持顺序
        chunk_contents = [chunk.content for chunk in chunks]
        return "\n\n".join(chunk_contents)

    def optimize_for_analysis(self, content: str, title: str = "") -> tuple[str, dict]:
        """
        为内容分析优化文本
        返回优化后的内容和元数据
        """
        original_tokens = self.estimate_tokens(content)
        optimized_content = self.smart_truncate(content, title)
        optimized_tokens = self.estimate_tokens(optimized_content)

        metadata = {
            "original_tokens": original_tokens,
            "optimized_tokens": optimized_tokens,
            "compression_ratio": optimized_tokens / original_tokens if original_tokens > 0 else 1.0,
            "was_truncated": original_tokens > self.max_tokens,
        }

        return optimized_content, metadata

    def extract_summary_candidates(self, content: str) -> list[str]:
        """
        提取可能作为摘要的段落候选
        """
        chunks = self.extract_key_sections(content)

        # 选择高优先级的短段落作为摘要候选
        candidates = []
        for chunk in chunks[:5]:  # 只看前5个最重要的段落
            if 50 <= len(chunk.content) <= 200:  # 适合作为摘要的长度
                candidates.append(chunk.content)

        return candidates
