"""
V2接口测试脚本
支持命令行参数配置测试
"""
import os
import sys
import time
import argparse
import base64

# 添加后端路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.config import get_settings
from app.services.prompt_template import get_prompt_manager
from app.services.image_gen_v2 import process_image_with_gemini

settings = get_settings()

# 默认配置
DEFAULT_OUTPUT_DIR = "results"
DEFAULT_OUTPUT_FILE = "v2_test_result.png"

# 默认模板链
DEFAULT_TEMPLATE_IDS = [
    'remove_bg',      # 背景去除
    'standardize',    # 产品标准化
    'ecommerce',      # 电商化渲染
    'color_correct',  # 颜色校正
]

# 可用模板列表
AVAILABLE_TEMPLATES = ['remove_bg', 'standardize', 'ecommerce', 'color_correct', 'enhance']

# 预设分辨率（Gemini API 支持的档位）
PRESET_SIZES = {
    '1k': '1K',
    '2k': '2K',
    '4k': '4K',
}


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='V2图片生成接口测试脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f'''示例:
  python test_v2_image.py                              # 使用默认配置测试
  python test_v2_image.py -i my_image.jpg              # 指定测试图片
  python test_v2_image.py -t remove_bg ecommerce       # 只使用两个模板
  python test_v2_image.py -o results -f my_result.png  # 指定输出目录和文件名
  python test_v2_image.py --size 2k                    # 2K分辨率输出
  python test_v2_image.py --size 4k                    # 4K分辨率输出
  python test_v2_image.py --debug                      # 开启调试模式
  python test_v2_image.py --list-templates             # 列出所有可用模板
'''
    )

    parser.add_argument('-i', '--image', type=str,
                        help='测试图片路径 (默认: 微信图片_20251227205807_94_111.jpg)')

    parser.add_argument('-t', '--templates', type=str, nargs='+',
                        help=f'使用的模板链 (默认: remove_bg standardize ecommerce color_correct)',
                        choices=AVAILABLE_TEMPLATES)

    parser.add_argument('-o', '--output', type=str,
                        help=f'输出目录 (默认: {DEFAULT_OUTPUT_DIR})')

    parser.add_argument('-f', '--filename', type=str,
                        help=f'输出文件名 (默认: {DEFAULT_OUTPUT_FILE})')

    parser.add_argument('-s', '--size', type=str, choices=list(PRESET_SIZES.keys()),
                        help=f'输出分辨率 (可选: {", ".join(PRESET_SIZES.keys())}, 默认: 不指定)')

    parser.add_argument('--width', type=int,
                        help='自定义输出宽度 (像素)')

    parser.add_argument('--height', type=int,
                        help='自定义输出高度 (像素)')

    parser.add_argument('--timeout', type=int, default=600,
                        help='超时时间秒数 (默认: 600)')

    parser.add_argument('--debug', action='store_true',
                        help='开启调试模式')

    parser.add_argument('--list-templates', action='store_true',
                        help='列出所有可用模板并退出')

    parser.add_argument('--no-quick-test', action='store_true',
                        help='跳过快速处理链测试')

    return parser.parse_args()


# 全局配置（从命令行参数读取）
args = parse_args()
TEST_IMAGE = args.image or "微信图片_20251227205807_94_111.jpg"
OUTPUT_DIR = args.output or DEFAULT_OUTPUT_DIR
OUTPUT_FILE = args.filename or DEFAULT_OUTPUT_FILE
TEMPLATE_IDS = args.templates or DEFAULT_TEMPLATE_IDS

# 解析分辨率参数（Gemini API image_size）
if args.size:
    IMAGE_SIZE = PRESET_SIZES[args.size]  # "1K", "2K", "4K"
else:
    IMAGE_SIZE = None  # 不指定则使用 API 默认 "1K"


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
        TEMPLATE_IDS,
        product_category="服装"
    )
    print(f"  - 构建提示词长度: {len(prompt)} 字符")

    print("  [通过] 提示词管理器正常")


def test_image_processing():
    """测试图片处理"""
    print(f"\n[3] 测试图片处理: {TEST_IMAGE}")
    print(f"  - 使用模板: {TEMPLATE_IDS}")
    if IMAGE_SIZE:
        print(f"  - 输出分辨率: {IMAGE_SIZE}")

    output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE)

    # 构建参数
    kwargs = {
        'image_path': TEST_IMAGE,
        'output_path': output_path,
        'template_ids': TEMPLATE_IDS,
        'timeout_seconds': args.timeout
    }

    # 如果指定了分辨率，添加到参数中
    if IMAGE_SIZE:
        kwargs['image_size'] = IMAGE_SIZE

    # 开始处理
    start_time = time.time()

    try:
        result = process_image_with_gemini(**kwargs)
        
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


def list_available_templates():
    """列出所有可用模板"""
    print("=" * 60)
    print("可用模板列表")
    print("=" * 60)

    manager = get_prompt_manager()
    templates = manager.list_templates()

    print(f"\n模板数量: {len(templates)}\n")

    for t in templates:
        print(f"[{t.category.value}] {t.name}")
        print(f"  ID: {t.template_id}")
        print(f"  优先级: {t.priority}")
        print(f"  描述: {t.description}")
        print()

    print("=" * 60)
    print("可用模板链")
    print("=" * 60)

    chains = manager.list_chains()
    for c in chains:
        print(f"\n{c['name']}:")
        print(f"  ID: {c['chain_id']}")
        print(f"  模板: {' -> '.join(c['template_ids'])}")

    print("\n" + "=" * 60)


def main():
    """主测试函数"""

    # 如果指定了列出模板，则直接列出并退出
    if args.list_templates:
        list_available_templates()
        return 0

    # 打印配置信息
    print("\n" + "=" * 60)
    print("V2接口测试开始")
    print("=" * 60)
    print(f"\n测试图片: {TEST_IMAGE}")
    print(f"使用模板: {' -> '.join(TEMPLATE_IDS)}")
    if IMAGE_SIZE:
        print(f"输出分辨率: {IMAGE_SIZE}")
    print(f"输出目录: {OUTPUT_DIR}")
    if args.debug:
        print("调试模式: 开启")
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
    if success and not args.no_quick_test:
        test_quick_chain()

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    print(f"\n测试图片: {TEST_IMAGE}")
    print(f"使用模板链: {' -> '.join(TEMPLATE_IDS)}")
    if IMAGE_SIZE:
        print(f"输出分辨率: {IMAGE_SIZE}")
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

