#!/usr/bin/env python3
"""
端口清理脚本
自动清理占用指定端口的进程
"""
import subprocess
import sys
import os


def get_pid_using_port(port: int) -> list[int]:
    """获取占用指定端口的进程PID列表"""
    try:
        # 使用 lsof 获取占用端口的进程
        result = subprocess.run(
            ["lsof", "-i", f":{port}", "-t"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            pids = [int(pid) for pid in result.stdout.strip().split("\n") if pid]
            return pids
    except FileNotFoundError:
        # 如果 lsof 不可用，尝试使用 netstat
        try:
            result = subprocess.run(
                ["netstat", "-tlnp"],
                capture_output=True,
                text=True
            )
            lines = result.stdout.split("\n")
            for line in lines:
                if f":{port}" in line and "LISTEN" in line:
                    # 提取PID
                    parts = line.split()
                    if len(parts) >= 7:
                        try:
                            pid = int(parts[6].split("/")[0])
                            return [pid]
                        except (IndexError, ValueError):
                            pass
        except FileNotFoundError:
            pass
    
    return []


def kill_process(pid: int) -> bool:
    """终止进程"""
    try:
        # 先尝试优雅终止
        subprocess.run(["kill", "-15", str(pid)], capture_output=True)
        # 等待进程退出
        import time
        time.sleep(1)
        
        # 检查进程是否还在
        try:
            os.kill(pid, 0)  # 检查进程是否存在
        except OSError:
            return True  # 进程已退出
        
        # 如果进程还在，强制终止
        subprocess.run(["kill", "-9", str(pid)], capture_output=True)
        time.sleep(1)
        
        try:
            os.kill(pid, 0)
            return False  # 进程仍然存在
        except OSError:
            return True  # 进程已退出
            
    except Exception as e:
        print(f"终止进程 {pid} 失败: {e}")
        return False


def cleanup_port(port: int) -> bool:
    """清理指定端口"""
    pids = get_pid_using_port(port)
    
    if not pids:
        print(f"端口 {port} 未被占用，无需清理")
        return True
    
    print(f"发现 {len(pids)} 个进程占用端口 {port}: {pids}")
    
    all_success = True
    for pid in pids:
        print(f"正在终止进程 {pid}...")
        if kill_process(pid):
            print(f"进程 {pid} 已成功终止")
        else:
            print(f"无法终止进程 {pid}")
            all_success = False
    
    # 再次检查端口是否已释放
    remaining_pids = get_pid_using_port(port)
    if remaining_pids:
        print(f"警告: 端口 {port} 仍被进程占用: {remaining_pids}")
        return False
    
    print(f"端口 {port} 已成功清理")
    return True


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python cleanup_ports.py <端口号>")
        print("示例: python cleanup_ports.py 8000")
        print("     python cleanup_ports.py 8000 8080")
        sys.exit(1)
    
    ports = [int(arg) for arg in sys.argv[1:]]
    
    print("=" * 50)
    print("端口清理工具")
    print("=" * 50)
    
    all_success = True
    for port in ports:
        if not cleanup_port(port):
            all_success = False
        print()
    
    if all_success:
        print("所有端口清理完成！")
        sys.exit(0)
    else:
        print("部分端口清理失败")
        sys.exit(1)


if __name__ == "__main__":
    main()

