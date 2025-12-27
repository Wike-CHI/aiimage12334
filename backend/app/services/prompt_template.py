"""
提示词模板管理系统
提供服饰图生图的提示词模板定义、拼接和管理功能
"""
import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class TemplateCategory(str, Enum):
    """模板分类"""
    BACKGROUND_REMOVE = "remove_bg"       # 背景去除
    STANDARDIZE = "standardize"           # 标准化
    ECOMMERCE = "ecommerce"               # 电商化渲染
    ENHANCE = "enhance"                   # 细节增强
    COLOR_CORRECT = "color_correct"       # 颜色校正


@dataclass
class PromptTemplate:
    """提示词模板类"""
    
    template_id: str                      # 模板唯一标识
    name: str                             # 模板名称
    category: TemplateCategory            # 模板分类
    description: str                      # 模板描述
    prompt_template: str                  # 提示词模板（支持变量替换）
    priority: int = 0                     # 执行优先级（数字越小越先执行）
    enabled: bool = True                  # 是否启用
    params: Dict[str, Any] = field(default_factory=dict)  # 模板参数
    
    def render(self, **kwargs) -> str:
        """
        渲染模板
        
        Args:
            **kwargs: 变量替换键值对
            
        Returns:
            str: 渲染后的提示词
        """
        result = self.prompt_template
        for key, value in kwargs.items():
            placeholder = "{" + key + "}"
            result = result.replace(placeholder, str(value))
        return result


class PromptChain:
    """
    提示词链管理器
    管理多个模板的拼接和执行顺序
    """
    
    def __init__(self, name: str = "默认链"):
        self.name = name
        self.templates: List[PromptTemplate] = []
    
    def add_template(self, template: PromptTemplate, position: Optional[int] = None) -> None:
        """
        添加模板到链中
        
        Args:
            template: 要添加的模板
            position: 插入位置（None表示追加）
        """
        if position is None:
            self.templates.append(template)
        else:
            self.templates.insert(position, template)
        # 按优先级排序
        self.templates.sort(key=lambda t: t.priority)
    
    def remove_template(self, template_id: str) -> bool:
        """
        从链中移除模板
        
        Args:
            template_id: 模板ID
            
        Returns:
            bool: 是否成功移除
        """
        for i, template in enumerate(self.templates):
            if template.template_id == template_id:
                self.templates.pop(i)
                return True
        return False
    
    def build_prompt(self, **global_kwargs) -> str:
        """
        构建完整提示词
        将所有模板按顺序拼接
        
        Args:
            **global_kwargs: 全局变量（所有模板共享）
            
        Returns:
            str: 拼接后的完整提示词
        """
        prompt_parts = []
        
        for template in self.templates:
            if not template.enabled:
                continue
            # 渲染模板
            prompt_text = template.render(**global_kwargs)
            prompt_parts.append(prompt_text)
        
        # 使用换行符拼接
        return "\n\n".join(prompt_parts)
    
    def get_template_ids(self) -> List[str]:
        """获取所有模板ID"""
        return [t.template_id for t in self.templates]
    
    def clear(self) -> None:
        """清空链中所有模板"""
        self.templates.clear()
    
    def __len__(self) -> int:
        """返回模板数量"""
        return len(self.templates)


class PromptTemplateManager:
    """
    提示词模板管理器
    统一管理所有内置模板和自定义模板
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._templates: Dict[str, PromptTemplate] = {}
        self._chains: Dict[str, PromptChain] = {}
        self._load_builtin_templates()
        self._initialized = True
    
    def _load_builtin_templates(self) -> None:
        """加载内置模板"""
        # 背景去除模板
        self.register_template(PromptTemplate(
            template_id="remove_bg",
            name="背景去除",
            category=TemplateCategory.BACKGROUND_REMOVE,
            description="去除图片背景，保留产品主体",
            prompt_template="""**第一阶段: 背景识别与去除**

精确识别输入图像中的产品主体（服装/配饰）：
- 分离产品与背景元素
- 保留产品的完整轮廓和边缘细节
- 确保头发、配饰等细节不被切除
- 精确处理镂空、蕾丝等复杂区域

输出要求：
- 仅保留产品主体，去除所有背景
- 保持产品原始尺寸比例
- 边缘处理自然，无锯齿或毛边""",
            priority=1,
            params={"preserve_edges": True}
        ))
        
        # 标准化模板
        self.register_template(PromptTemplate(
            template_id="standardize",
            name="产品标准化",
            category=TemplateCategory.STANDARDIZE,
            description="标准化产品形态和比例",
            prompt_template="""**第二阶段: 产品形态标准化重建**

视角调整：
- 正向对准产品中心的垂直视角
- 电商标准展示图，不改变整体比例
- 确保产品居中显示

结构约束：
- 服装关键结构点（纽扣位置、缝线走向、口袋形状）与原图完全一致
- 版型比例优先于褶皱消除
- 保持服装的自然垂坠感

褶皱处理：
- 消除拍摄导致的真实不规则褶皱
- 重建为电商展示标准的平整形态
- 严格保留面料的自然纹理""",
            priority=2,
            params={"preserve_structure": True}
        ))
        
        # 电商化渲染模板
        self.register_template(PromptTemplate(
            template_id="ecommerce",
            name="电商化渲染",
            category=TemplateCategory.ECOMMERCE,
            description="电商标准白底图渲染",
            prompt_template="""**第三阶段: 电商化白底渲染**

背景要求：
- 100%纯白背景（RGB 255,255,255）
- 无任何阴影、反光、渐变
- 背景纯净无噪点

光照处理：
- 均匀无影的全局光照
- 展示产品固有色
- 避免过度曝光或阴影

产品优化：
- 清晰平整的理想化面料质感
- 色彩饱和度适中，接近实物
- 细节清晰可辨""",
            priority=3,
            params={"bg_color": "white", "lighting": "uniform"}
        ))
        
        # 细节增强模板
        self.register_template(PromptTemplate(
            template_id="enhance",
            name="细节增强",
            category=TemplateCategory.ENHANCE,
            description="增强产品细节和质感",
            prompt_template="""**第四阶段: 产品细节增强**

面料质感：
- 清晰展示面料纹理和编织细节
- 保持面料的哑光或光泽特性
- 纹理方向与产品形态一致

细节清晰度：
- 图案、花纹清晰可辨
- 品牌标识清晰展示
- 缝线、装饰细节可见

整体质感：
- 产品看起来立体、有质感
- 避免塑料感或过度平滑
- 保持真实感和专业感""",
            priority=4,
            params={"enhance_details": True}
        ))
        
        # 颜色校正模板
        self.register_template(PromptTemplate(
            template_id="color_correct",
            name="颜色校正",
            category=TemplateCategory.COLOR_CORRECT,
            description="颜色校正和标准化",
            prompt_template="""**第五阶段: 颜色校正**

色彩准确性：
- 色彩饱和度适中，接近实物拍摄效果
- 避免过度饱和或失真
- 保持品牌标识色彩准确

色调一致性：
- 整体色调统一，无明显色偏
- 不同批次产品色调一致
- 适合电商平台的色彩标准

色彩表达：
- 精确表达潘通色值
- 色彩过渡自然
- 适合展示和销售""",
            priority=5,
            params={"color_accuracy": True}
        ))
        
        # 创建默认链
        default_chain = PromptChain(name="默认白底图处理链")
        for template_id in ["remove_bg", "standardize", "ecommerce", "color_correct"]:
            template = self.get_template(template_id)
            if template:
                default_chain.add_template(template)
        self.register_chain("default", default_chain)
    
    def register_template(self, template: PromptTemplate) -> None:
        """
        注册模板
        
        Args:
            template: 提示词模板
        """
        self._templates[template.template_id] = template
    
    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """
        获取模板
        
        Args:
            template_id: 模板ID
            
        Returns:
            PromptTemplate or None
        """
        return self._templates.get(template_id)
    
    def list_templates(self, category: Optional[TemplateCategory] = None) -> List[PromptTemplate]:
        """
        列出所有模板
        
        Args:
            category: 分类筛选
            
        Returns:
            List[PromptTemplate]: 模板列表
        """
        templates = list(self._templates.values())
        if category:
            templates = [t for t in templates if t.category == category]
        return sorted(templates, key=lambda t: t.priority)
    
    def delete_template(self, template_id: str) -> bool:
        """
        删除模板
        
        Args:
            template_id: 模板ID
            
        Returns:
            bool: 是否成功删除
        """
        if template_id in self._templates:
            del self._templates[template_id]
            return True
        return False
    
    def register_chain(self, chain_id: str, chain: PromptChain) -> None:
        """
        注册提示词链
        
        Args:
            chain_id: 链ID
            chain: 提示词链
        """
        self._chains[chain_id] = chain
    
    def get_chain(self, chain_id: str) -> Optional[PromptChain]:
        """
        获取提示词链
        
        Args:
            chain_id: 链ID
            
        Returns:
            PromptChain or None
        """
        return self._chains.get(chain_id)
    
    def list_chains(self) -> List[Dict[str, Any]]:
        """
        列出所有提示词链
        
        Returns:
            List[Dict]: 链信息列表
        """
        return [
            {
                "chain_id": chain_id,
                "name": chain.name,
                "template_count": len(chain),
                "template_ids": chain.get_template_ids()
            }
            for chain_id, chain in self._chains.items()
        ]
    
    def build_prompt_from_chain(
        self,
        template_ids: List[str],
        **global_kwargs
    ) -> str:
        """
        根据模板ID列表构建提示词
        
        Args:
            template_ids: 模板ID列表
            **global_kwargs: 全局变量
            
        Returns:
            str: 拼接后的提示词
        """
        chain = PromptChain(name="临时链")
        for template_id in template_ids:
            template = self.get_template(template_id)
            if template:
                chain.add_template(template)
        return chain.build_prompt(**global_kwargs)
    
    def build_default_prompt(self, **global_kwargs) -> str:
        """
        使用默认链构建提示词
        
        Args:
            **global_kwargs: 全局变量
            
        Returns:
            str: 拼接后的提示词
        """
        default_chain = self.get_chain("default")
        if default_chain:
            return default_chain.build_prompt(**global_kwargs)
        return ""
    
    def get_template_info(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        获取模板详细信息
        
        Args:
            template_id: 模板ID
            
        Returns:
            Dict or None
        """
        template = self.get_template(template_id)
        if not template:
            return None
        return {
            "template_id": template.template_id,
            "name": template.name,
            "category": template.category.value,
            "description": template.description,
            "priority": template.priority,
            "enabled": template.enabled,
            "params": template.params,
            "prompt_preview": template.prompt_template[:200] + "..." if len(template.prompt_template) > 200 else template.prompt_template
        }


# 全局模板管理器实例
prompt_manager = PromptTemplateManager()


def get_prompt_manager() -> PromptTemplateManager:
    """获取全局提示词管理器"""
    return prompt_manager

