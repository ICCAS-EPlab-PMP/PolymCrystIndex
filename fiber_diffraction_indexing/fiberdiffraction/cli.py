"""
命令行接口
==========

该模块提供命令行入口点。

用法：
    python -m fiberdiffraction -i input.txt -d diffraction.txt
    python -m fiberdiffraction -v  # 显示版本和引用信息
"""

import argparse
import sys
from .indexer import FiberDiffractionIndexer
from .version import VERSION, RELEASE_DATE, PROGRAM_NAME, get_citation


def print_version() -> None:
    """打印版本信息和引用文献。"""
    print(f"""
{PROGRAM_NAME}
======================== VERSION {VERSION} ========================
RELEASE in {RELEASE_DATE}

{get_citation()}
""")


def main() -> None:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description='Fiber diffraction indexing orchestration program',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m fiberdiffraction -i input.txt -d diffraction.txt
    python -m fiberdiffraction -v  # Show version and citation
        """
    )
    
    parser.add_argument(
        '-i', '--input',
        help='Input file name',
        required=False
    )
    
    parser.add_argument(
        '-d', '--diffraction',
        help='Diffraction file name',
        required=False
    )
    
    parser.add_argument(
        '-v', '--version',
        help='Print version and citation information',
        action='store_true',
        required=False
    )
    
    parser.add_argument(
        '-s', '--show-config',
        help='Show configuration summary',
        action='store_true',
        required=False
    )
    
    args = parser.parse_args()
    
    if args.version:
        print_version()
        return
    
    if not args.input or not args.diffraction:
        parser.print_help()
        print(f"\nError: The following arguments are required: -i/--input, -d/--diffraction")
        sys.exit(1)
    
    try:
        indexer = FiberDiffractionIndexer(args.input, args.diffraction)
        
        if args.show_config:
            print(indexer.get_config_summary())
            return
        
        indexer.run()
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
