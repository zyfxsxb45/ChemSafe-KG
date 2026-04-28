"""
RAG 上下文构建模块

将检索到的因果路径与用户问题组合，构建 LLM 的输入上下文。
"""
from typing import List, Dict


class ContextBuilder:
    """RAG 上下文构建器"""

    # ─── Graph RAG 约束生成 Prompt ──────────────────────────────────────
    GRAPH_RAG_SYSTEM_PROMPT = """你是一位化工安全专家。请基于以下从知识图谱中检索到的因果路径，回答用户的问题。

约束条件：
1. **严格按照检索到的因果路径中的事实回答**，不得添加路径之外的推测性内容
2. 必须按照因果关系的时间顺序组织回答
3. 如果检索到的因果路径不足以完整回答问题，请明确说明信息局限性
4. 对于涉及化学品物性的问题，引用物性数据辅助解释
5. 回答应包含：事故链条概述 → 关键节点解释 → 安全建议"""

    def build(
        self,
        question: str,
        causal_context: str,
    ) -> tuple:
        """
        构建完整的 LLM 输入。

        Args:
            question: 用户原始问题
            causal_context: CausalPathRetriever 格式化的因果路径文本

        Returns:
            (system_prompt, user_prompt) 二元组

        TODO [完善]:
          1. 上下文窗口管理 (超出限制时截断或摘要)
          2. 多源信息融合提示
          3. 引用来源标注
        """
        user_prompt = f"""用户问题：{question}

知识图谱检索到的因果证据：
{causal_context}

请基于以上因果证据回答问题，严格遵循约束条件。"""
        return self.GRAPH_RAG_SYSTEM_PROMPT, user_prompt

    def build_with_chemical_data(
        self,
        question: str,
        causal_context: str,
        chemical_data: str,
    ) -> tuple:
        """
        构建包含化学品物性数据的增强上下文。

        TODO [完善]:
          1. 集成物性数据作为辅助信息
          2. 关联物性与事故因果链
        """
        enhanced_context = f"""{causal_context}

相关化学品物性数据：
{chemical_data}"""
        return self.build(question, enhanced_context)
