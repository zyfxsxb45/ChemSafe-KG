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
    GRAPH_RAG_SYSTEM_PROMPT = """你是一位化工安全专家。请基于以下从知识图谱中检索到的因果路径，综合分析后回答用户的问题。

约束条件：
1. 回答必须**严格基于检索到的因果证据**，不得添加路径之外的推测。
2. 如果因果路径为空或与问题完全无关，直接回答"根据当前知识图谱，无法回答该问题"，绝不编造。
3. **综合分析**：不要逐条复述路径。应归纳共性模式、对比不同路径、提炼规律。例如：
   - 从多条路径中提取反复出现的关键环节（如"违规操作"在多条路径中出现）
   - 指出不同化学品/设备的事故链条差异
   - 如果多条路径指向相同结论，合并陈述而非分开重复
4. 回答结构（按需调整顺序）：
   - **总体发现**：基于全部路径的核心结论（1-2句）
   - **关键模式**：归纳出的共性规律，每条定量引用路径数（如"在5条路径中有3条涉及设备故障"）
   - **典型链条**：选1-2条最具代表性/信息最完整的路径简述
   - **预防启示**：基于模式给出的安全建议
5. 每条关键陈述末尾标注来源路径编号，格式 `[路径N]`。支持合并标注 `[路径1,路径3]`。
6. 如果证据不足以得出明确结论，诚实说明局限性。"""

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

请综合分析以上因果证据回答用户问题。注意：
- 归纳共性模式，不要逐条复述每条路径
- 引用多条路径时用 [路径1,路径3] 格式标注来源
- 证据不足时诚实说明局限性"""
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
