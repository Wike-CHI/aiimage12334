"""
V2接口测试脚本
测试提示词模板管理和图片生成功能
"""
import sys
import os

# 添加后端路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.prompt_template import (
    get_prompt_manager,
    PromptTemplateManager,
    TemplateCategory
)
from app.services.image_gen_v2 import (
    get_available_templates,
    get_template_chains,
    preview_prompt
)


def test_prompt_template_manager():
    """测试提示词模板管理器"""
    print("=" * 60)
    print("测试1: 提示词模板管理器")
    print("=" * 60)
    
    manager = get_prompt_manager()
    
    # 列出所有模板
    templates = manager.list_templates()
    print(f"\n可用模板数量: {len(templates)}")
    for t in templates:
        print(f"  - [{t.category.value}] {t.name} (优先级: {t.priority})")
    
    # 列出所有链
    chains = manager.list_chains()
    print(f"\n可用模板链数量: {len(chains)}")
    for c in chains:
        print(f"  - {c['name']}: {c['template_ids']}")
    
    # 获取单个模板详情
    template_info = manager.get_template_info("remove_bg")
    if template_info:
        print(f"\n模板详情 (remove_bg):")
        print(f"  名称: {template_info['name']}")
        print(f"  分类: {template_info['category']}")
        print(f"  描述: {template_info['description']}")
    
    print("\n[通过] 提示词模板管理器测试通过\n")


def test_prompt_preview():
    """测试提示词预览"""
    print("=" * 60)
    print("测试2: 提示词预览")
    print("=" * 60)
    
    # 预览默认链
    template_ids = ["remove_bg", "standardize", "ecommerce", "color_correct"]
    prompt = preview_prompt(template_ids, product_category="服装")
    
    print(f"\n使用模板: {template_ids}")
    print(f"提示词长度: {len(prompt)} 字符")
    print(f"\n提示词预览（前500字符）:")
    print("-" * 40)
    print(prompt[:500])
    print("-" * 40)
    
    # 预览单个模板
    single_prompt = preview_prompt(["remove_bg"], product_category="T恤")
    print(f"\n单个模板提示词长度: {len(single_prompt)} 字符")
    
    print("\n[通过] 提示词预览测试通过\n")


def test_custom_chain():
    """测试自定义模板链"""
    print("=" * 60)
    print("测试3: 自定义模板链")
    print("=" * 60)
    
    manager = get_prompt_manager()
    
    # 创建自定义链
    from app.services.prompt_template import PromptChain, PromptTemplate
    
    custom_chain = PromptChain(name="快速处理链")
    
    # 只选择前两个模板
    for template_id in ["remove_bg", "ecommerce"]:
        template = manager.get_template(template_id)
        if template:
            custom_chain.add_template(template)
    
    print(f"\n自定义链: {custom_chain.name}")
    print(f"模板数量: {len(custom_chain)}")
    print(f"模板列表: {custom_chain.get_template_ids()}")
    
    # 构建提示词
    prompt = custom_chain.build_prompt(product_category="连衣裙")
    print(f"\n生成提示词长度: {len(prompt)} 字符")
    
    print("\n[通过] 自定义模板链测试通过\n")


def test_image_gen_v2_functions():
    """测试image_gen_v2模块函数"""
    print("=" * 60)
    print("测试4: image_gen_v2 模块函数")
    print("=" * 60)
    
    # 测试 get_available_templates
    templates = get_available_templates()
    print(f"\n可用模板数量: {len(templates)}")
    
    # 测试 get_template_chains
    chains = get_template_chains()
    print(f"可用模板链数量: {len(chains)}")
    
    print("\n[通过] image_gen_v2 模块函数测试通过\n")


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("V2 接口测试开始")
    print("=" * 60 + "\n")
    
    try:
        test_prompt_template_manager()
        test_prompt_preview()
        test_custom_chain()
        test_image_gen_v2_functions()
        
        print("=" * 60)
        print("所有测试通过！")
        print("=" * 60)
        print("\nV2接口已就绪，可通过以下端点访问:")
        print("  - POST /api/v2/process          - 处理图片（同步）")
        print("  - POST /api/v2/process/upload   - 上传并处理图片")
        print("  - GET  /api/v2/templates        - 获取模板列表")
        print("  - GET  /api/v2/chains           - 获取模板链列表")
        print("  - POST /api/v2/preview          - 预览提示词")
        print("\n文档地址: http://localhost:8001/docs")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n[失败] 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

