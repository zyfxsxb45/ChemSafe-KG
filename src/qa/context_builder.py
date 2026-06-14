"""
RAG 上下文构建模块

将检索到的因果路径与用户问题组合，构建 LLM 的输入上下文。
支持来源引用标注和上下文窗口管理。
"""
import re


class ContextBuilder:
    """RAG 上下文构建器"""

    DEFAULT_MAX_CONTEXT_CHARS = 12000

    # ─── Graph RAG 约束生成 Prompt（含来源引用要求）──────────────────────
    GRAPH_RAG_SYSTEM_PROMPT = """你是一位化工安全专家。请基于以下从知识图谱中检索到的因果路径，回答用户的问题。

约束条件：
1. **严格按照检索到的因果路径中的事实回答**，不得添加路径之外的推测性内容。
2. 如果检索到的因果路径为空，或者与问题完全无关，请直接回答"根据当前知识图谱，无法回答该问题"，绝不能编造。
3. 必须按照因果关系的时间顺序组织回答。
4. 如果检索到的因果路径不足以完整回答问题，请明确说明信息局限性。
5. 回答应包含三个部分：
   - **事故链条概述**：简要说明从原因到后果的因果链
   - **关键节点解释**：对链条中的关键步骤进行专业解读
   - **安全建议**：基于链条中的薄弱环节给出预防建议
6. **每条关键陈述末尾必须标注来源路径编号**，格式为 `[路径N]`。例如"泵故障导致温度升高[路径1]"。
7. 如果多条路径支持同一结论，可以合并标注如 `[路径1,路径3]`。"""

    def build(
        self,
        question: str,
        causal_context: str,
        max_context_chars: int | None = None,
    ) -> tuple:
        """
        构建完整的 LLM 输入。

        Args:
            question: 用户原始问题
            causal_context: CausalPathRetriever 格式化的因果路径文本

        Returns:
            (system_prompt, user_prompt) 二元组
        """
        causal_context = self._truncate_context(
            causal_context,
            max_chars=max_context_chars or self.DEFAULT_MAX_CONTEXT_CHARS,
        )

        user_prompt = f"""用户问题：{question}

知识图谱检索到的因果证据（共 {self._count_paths(causal_context)} 条路径）：
{causal_context}

请基于以上因果证据回答问题，严格遵循约束条件。
注意：每条关键陈述必须标注来源路径编号，格式为 [路径N]。"""
        return self.GRAPH_RAG_SYSTEM_PROMPT, user_prompt

    def _count_paths(self, context: str) -> int:
        """统计上下文中的路径数量"""
        return context.count("【路径")

    def _truncate_context(self, context: str, max_chars: int) -> str:
        """按路径边界截断超长上下文，避免提示词超过模型窗口。"""
        context = context or ""
        if len(context) <= max_chars:
            return context

        parts = re.split(r"(?=【路径\s*\d+】)", context)
        kept = []
        current_len = 0
        for part in parts:
            if not part:
                continue
            if current_len + len(part) > max_chars:
                break
            kept.append(part)
            current_len += len(part)

        truncated = "".join(kept).strip()
        if not truncated:
            truncated = context[:max_chars].rstrip()
        return f"{truncated}\n\n[上下文已截断，仅保留前 {max_chars} 字符内的因果证据。]"

    def build_with_chemical_data(
        self,
        question: str,
        causal_context: str,
        chemical_data: str,
    ) -> tuple:
        """
        构建包含化学品物性数据的增强上下文。
        """
        enhanced_context = f"""{causal_context}

相关化学品物性数据：
{chemical_data}"""
        return self.build(question, enhanced_context)
