"""
V2接口测试脚本
测试图片: 微信图片_20251227205807_94_111.jpg
"""
import os
import sys
import time
import base64

# 添加后端路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.config import get_settings
from app.services.prompt_template import get_prompt_manager
from app.services.image_gen_v2 import process_image_with_gemini

settings = get_settings()

# 测试配置
TEST_IMAGE = "微信图片_20251227205807_94_111.jpg"
OUTPUT_DIR = "results"
OUTPUT_FILE = "v2_test_result.png"

# 默认模板链
DEFAULT_TEMPLATE_IDS = [
    'remove_bg',      # 背景去除
    'standardize',    # 产品标准化
    'ecommerce',      # 电商化渲染
    'color_correct',  # 颜色校正
]


def check_prerequisites():
    """检查前置条件"""
    print("=" * 60)
    print("V2接口测试")
    print("=" * 60)
    
    print("\n[1] 检查前置条件")
    
    # 检查测试图片
    if not os.path.exists(TEST_IMAGE):
        print(f"  [失败] 测试图片不存在: {TEST_IMAGE}")
        return False
    
    image_size = os.path.getsize(TEST_IMAGE) / (1024 * 1024)
    print(f"  [通过] 测试图片存在: {TEST_IMAGE} ({image_size:.2f} MB)")
    
    # 检查API密钥
    if not settings.GEMINI_API_KEY:
        print(f"  [失败] GEMINI_API_KEY 未配置")
        return False
    print(f"  [通过] API密钥已配置: {settings.GEMINI_API_KEY[:10]}...")
    
    # 检查输出目录
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    print(f"  [通过] 输出目录: {OUTPUT_DIR}")
    
    return True


def test_prompt_manager():
    """测试提示词管理器"""
    print("\n[2] 测试提示词管理器")
    
    manager = get_prompt_manager()
    
    # 列出所有模板
    templates = manager.list_templates()
    print(f"  - 可用模板数量: {len(templates)}")
    for t in templates:
        print(f"    [{t.category.value}] {t.name} (优先级: {t.priority})")
    
    # 列出所有模板链
    chains = manager.list_chains()
    print(f"  - 可用模板链数量: {len(chains)}")
    for c in chains:
        print(f"    - {c['name']}: {c['template_ids']}")
    
    # 测试提示词构建
    prompt = manager.build_prompt_from_chain(
        DEFAULT_TEMPLATE_IDS,
        product_category="服装"
    )
    print(f"  - 构建提示词长度: {len(prompt)} 字符")
    
    print("  [通过] 提示词管理器正常")


def test_image_processing():
    """测试图片处理"""
    print(f"\n[3] 测试图片处理: {TEST_IMAGE}")
    
    output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE)
    
    # 开始处理
    start_time = time.time()
    
    try:
        result = process_image_with_gemini(
            image_path=TEST_IMAGE,
            output_path=output_path,
            template_ids=DEFAULT_TEMPLATE_IDS,
            timeout_seconds=600  # 10分钟超时
        )
        
        elapsed = time.time() - start_time
        
        print(f"\n  处理结果:")
        print(f"  - 成功: {'是' if result['success'] else '否'}")
        print(f"  - 总耗时: {elapsed:.2f} 秒")
        print(f"  - API返回耗时: {result.get('elapsed_time', 'N/A')} 秒")
        print(f"  - 结果路径: {result.get('result_path', 'N/A')}")
        print(f"  - 使用模板: {result.get('used_templates', [])}")
        
        if result['success']:
            # 检查输出文件
            if os.path.exists(output_path):
                output_size = os.path.getsize(output_path) / (1024 * 1024)
                print(f"  - 输出文件大小: {output_size:.2f} MB")
                print(f"  - 输出文件路径: {output_path}")
                print("\n  [通过] 图片处理成功!")
            else:
                print(f"\n  [警告] 输出文件不存在: {output_path}")
        else:
            error_msg = result.get('error_message', '未知错误')
            print(f"\n  [失败] 处理失败: {error_msg}")
            return False
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n  [失败] 处理异常: {str(e)}")
        print(f"  - 耗时: {elapsed:.2f} 秒")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def test_quick_chain():
    """测试快速处理链（减少模板数量）"""
    print(f"\n[4] 测试快速处理链")
    
    # 只使用两个模板
    quick_template_ids = ['remove_bg', 'ecommerce']
    output_path = os.path.join(OUTPUT_DIR, "v2_quick_result.png")
    
    start_time = time.time()
    
    try:
        result = process_image_with_gemini(
            image_path=TEST_IMAGE,
            output_path=output_path,
            template_ids=quick_template_ids,
            timeout_seconds=300
        )
        
        elapsed = time.time() - start_time
        
        print(f"  - 使用模板: {quick_template_ids}")
        print(f"  - 成功: {'是' if result['success'] else '否'}")
        print(f"  - 耗时: {elapsed:.2f} 秒")
        
        if result['success']:
            print("  [通过] 快速处理成功")
        else:
            print(f"  [失败] {result.get('error_message', '未知错误')}")
            
    except Exception as e:
        print(f"  [失败] {str(e)}")


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("V2接口测试开始")
    print(f"测试图片: {TEST_IMAGE}")
    print("=" * 60 + "\n")
    
    # 1. 检查前置条件
    if not check_prerequisites():
        print("\n[失败] 前置条件检查未通过，测试终止")
        return 1
    
    # 2. 测试提示词管理器
    test_prompt_manager()
    
    # 3. 测试完整处理链
    success = test_image_processing()
    
    # 4. 测试快速处理链（可选）
    if success:
        test_quick_chain()
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    print(f"\n测试图片: {TEST_IMAGE}")
    print(f"使用模板链: {DEFAULT_TEMPLATE_IDS}")
    print(f"输出目录: {OUTPUT_DIR}")
    
    if success:
        print("\n结果文件:")
        result_file = os.path.join(OUTPUT_DIR, OUTPUT_FILE)
        if os.path.exists(result_file):
            size = os.path.getsize(result_file) / (1024 * 1024)
            print(f"  - {result_file} ({size:.2f} MB)")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

