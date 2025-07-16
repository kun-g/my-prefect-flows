"""
智能内容分析与评价系统 - 核心数据结构和分析器
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass
class ContentAnalysis:
    """
    内容分析结果数据结构
    """

    url: str
    title: str
    summary: str  # 简洁摘要 (150-200字)
    tags: list[str]  # 智能标签
    reading_score: float  # 综合阅读价值评分 (0-10)
    reading_time_minutes: int  # 预估阅读时间
    difficulty_level: str  # 难度等级: "初级", "中级", "高级"
    score_breakdown: dict[str, float]  # 评分细分
    analyzed_at: datetime
    model_used: str
    confidence_score: float  # 置信度评分 (0-1)

    def to_dict(self) -> dict:
        """转换为字典格式"""
        result = asdict(self)
        # 转换datetime为ISO字符串
        result["analyzed_at"] = self.analyzed_at.isoformat()
        return result

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "ContentAnalysis":
        """从字典创建ContentAnalysis实例"""
        # 转换ISO字符串为datetime
        if isinstance(data["analyzed_at"], str):
            data["analyzed_at"] = datetime.fromisoformat(data["analyzed_at"])
        return cls(**data)


class DifficultyLevel:
    """难度等级常量"""

    BEGINNER = "初级"
    INTERMEDIATE = "中级"
    ADVANCED = "高级"


class ScoreDimensions:
    """评分维度常量"""

    PRACTICALITY = "实用性"  # 25%权重
    LEARNING_VALUE = "学习价值"  # 25%权重
    TIMELINESS = "时效性"  # 20%权重
    TECHNICAL_DEPTH = "技术深度"  # 15%权重
    COMPLETENESS = "完整性"  # 15%权重

    @classmethod
    def get_weights(cls) -> dict[str, float]:
        """获取各维度权重"""
        return {
            cls.PRACTICALITY: 0.25,
            cls.LEARNING_VALUE: 0.25,
            cls.TIMELINESS: 0.20,
            cls.TECHNICAL_DEPTH: 0.15,
            cls.COMPLETENESS: 0.15,
        }

    @classmethod
    def calculate_weighted_score(cls, scores: dict[str, float]) -> float:
        """计算加权总分"""
        weights = cls.get_weights()
        total_score = 0.0

        for dimension, weight in weights.items():
            if dimension in scores:
                total_score += scores[dimension] * weight

        return round(total_score, 2)


class TagCategories:
    """标签分类体系"""

    # 技术栈标签
    TECH_STACK = {
        "Python",
        "JavaScript",
        "Java",
        "Go",
        "Rust",
        "TypeScript",
        "React",
        "Vue",
        "Angular",
        "Node.js",
        "Django",
        "Flask",
        "Docker",
        "Kubernetes",
        "AWS",
        "Azure",
        "GCP",
        "机器学习",
        "人工智能",
        "区块链",
        "大数据",
    }

    # 内容类型标签
    CONTENT_TYPE = {
        "教程",
        "指南",
        "最佳实践",
        "案例研究",
        "技术分享",
        "工具介绍",
        "框架对比",
        "性能优化",
        "安全",
        "测试",
        "架构设计",
        "代码审查",
        "调试技巧",
    }

    # 应用场景标签
    SCENARIO = {
        "Web开发",
        "移动开发",
        "后端开发",
        "前端开发",
        "全栈开发",
        "DevOps",
        "数据科学",
        "系统架构",
        "微服务",
        "API设计",
    }

    # 行业领域标签
    INDUSTRY = {"电商", "金融", "医疗", "教育", "游戏", "社交", "企业软件", "IoT", "AR/VR", "自动驾驶"}

    @classmethod
    def get_all_tags(cls) -> set:
        """获取所有可用标签"""
        return cls.TECH_STACK | cls.CONTENT_TYPE | cls.SCENARIO | cls.INDUSTRY

    @classmethod
    def suggest_tags_by_content(cls, content: str) -> list[str]:
        """基于内容建议标签（简单关键词匹配）"""
        content_lower = content.lower()
        suggested = []

        all_tags = cls.get_all_tags()
        for tag in all_tags:
            if tag.lower() in content_lower:
                suggested.append(tag)

        return suggested[:10]  # 限制返回数量
