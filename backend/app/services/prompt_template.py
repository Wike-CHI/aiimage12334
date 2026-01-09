"""
提示词模板管理系统
提供服饰图生图的提示词模板定义、拼接和管理功能
"""
import base64
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


class ProductCategory(str, Enum):
    """服装品类分类"""
    TSHIRT = "tshirt"           # T恤
    OUTERWEAR = "outerwear"     # 外套/大衣
    DRESS = "dress"             # 连衣裙
    PANTS = "pants"             # 裤子
    ACCESSORY = "accessory"     # 配饰/包包
    KNITWEAR = "knitwear"       # 针织/毛衣
    UNKNOWN = "unknown"         # 未知


# ==================== 精简版核心提示词 ====================

# 通用基础提示词（所有品类共享）
BASE_PROMPT = """【背景处理】
去除所有背景，保留纯白底（RGB 255,255,255）。去除衣架、支架、模特等非产品元素。

【产品形态】
正视角居中展示，保持原始比例。去除褶皱，保持平整。

【材质保留】
清晰展示面料纹理。保留品牌logo、标签、纽扣等细节。

【禁止事项】
不改变产品结构，不添加文字水印，不修改设计元素。

【输出】
PNG格式，保持原始尺寸。"""


# 品类定制提示词
CATEGORY_PROMPTS = {
    ProductCategory.TSHIRT: """
【T恤专项】
- 保留领口螺纹形状和弹性感
- 袖口版型准确，不变形
- 印花/图案位置准确，不偏移
- 肩线自然，不扭曲
""",
    ProductCategory.OUTERWEAR: """
【外套/大衣专项】
- 拉链、纽扣完整保留，位置准确
- 口袋形状和位置准确
- 帽绳、抽绳自然垂坠
- 衣领自然立体，不过度扁平
- 门襟对齐，不偏移
""",
    ProductCategory.DRESS: """
【连衣裙专项】
- 裙摆自然垂坠，不僵硬
- 腰线位置准确，不移动
- 领口形状准确
- 下摆平整，无明显褶皱堆积
""",
    ProductCategory.PANTS: """
【裤子专项】
- 裤腿平整对称，不一长一短
- 口袋位置对称，形状准确
- 裤腰平整，不扭曲
- 裤脚自然，不变形
""",
    ProductCategory.ACCESSORY: """
【配饰/包包专项】
- 金属配件（拉链、扣子、logo）清晰锐利
- logo位置准确，不变形
- 纹理清晰，不模糊
- 保持配饰的立体感
""",
    ProductCategory.KNITWEAR: """
【针织/毛衣专项】
- 针织纹理清晰可见，不模糊化
- 保持面料的编织感
- 纹理方向与产品形态一致
- 不产生塑料感
""",
}


def build_category_prompt(category: ProductCategory) -> str:
    """
    根据品类构建完整提示词

    Args:
        category: 服装品类

    Returns:
        完整的提示词
    """
    base = BASE_PROMPT
    category_prompt = CATEGORY_PROMPTS.get(category, "")

    # 如果是未知品类，不添加专项提示
    if category == ProductCategory.UNKNOWN:
        return base

    return base + category_prompt


def detect_product_category_from_image(image_data: bytes) -> ProductCategory:
    """
    根据图片内容识别服装品类（使用规则匹配）

    Args:
        image_data: 图片二进制数据

    Returns:
        识别出的品类
    """
    # 这里可以实现基于规则的简单识别
    # 实际生产中应该调用 Gemini Vision API 进行准确识别

    # 临时返回 unknown，由后续流程中的 Gemini 自动判断
    return ProductCategory.UNKNOWN


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
            prompt_template="""【最高优先级：纯白背景处理】

**第一步：识别并分离产品主体**

精确识别服装/配饰的边缘轮廓，包括复杂区域（蕾丝、镂空、细节装饰）。
保留所有产品细节：纽扣、拉链、刺绣、印花、吊牌、标签。
保持产品的原始尺寸和比例。

**第二步：背景移除【核心要求】**

1. **彻底移除**原图背景（墙面、地板、家具、其他物体等）
2. **彻底去除**所有支撑结构：衣架（包括肩部弧形、挂钩）、模特支架、底座、支撑杆
3. **背景必须设置为 RGB(255,255,255) 的纯白色**
4. **产品边缘与白底交界处必须清晰，不得有灰色过渡区**
5. 去除产品周围的所有阴影和反光

**输出标准**：
- 只保留纯粹的产品主体
- 背景100%纯白，无任何杂色
- 产品形态保持原样，不变形不扭曲""",
            priority=1,
            params={"preserve_edges": True, "remove_hangers": True}
        ))
        
        # 标准化模板
        self.register_template(PromptTemplate(
            template_id="standardize",
            name="产品标准化",
            category=TemplateCategory.STANDARDIZE,
            description="标准化产品形态和比例",
            prompt_template="""**第二步：产品形态标准化**

**视角调整**：
- 正向对准产品中心的垂直视角
- 电商标准展示图，不改变整体比例
- 确保产品居中显示

**结构约束**：
- 服装关键结构点（纽扣位置、缝线走向、口袋形状）与原图保持一致
- 版型比例准确

**褶皱处理**：
- 去除堆叠、挤压产生的**明显杂乱褶皱**
- **保留面料本身的自然纹理质感**
- 不模拟过度熨烫的"完全平整"效果
- 只去除影响美观的大型折痕""",
            priority=2,
            params={"preserve_structure": True}
        ))
        
        # 电商化渲染模板
        self.register_template(PromptTemplate(
            template_id="ecommerce",
            name="电商化渲染",
            category=TemplateCategory.ECOMMERCE,
            description="电商标准白底图渲染",
            prompt_template="""**第三步：电商化白底渲染**

**背景要求【严格执行】**：
- 背景必须是100%纯白色（RGB 255,255,255）
- 绝对不允许有任何灰色、渐变或杂色
- 产品周围不得有阴影、倒影、光晕效果
- 背景必须完全均匀纯净，无噪点无纹理
- 产品边缘与白底交界处必须清晰，不得有灰色过渡区

**光照处理**：
- 均匀无影的全局光照
- 展示产品固有色
- 避免过度曝光或阴影

**产品优化**：
- 展现面料真实质感，避免塑料感
- 色彩还原自然，避免过度饱和
- 边缘光影处理自然""",
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

