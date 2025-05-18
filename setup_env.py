import os
import sys
import subprocess
import platform

def create_venv():
    """가상환경 생성 및 활성화"""
    print("가상환경을 생성하고 설정합니다...")
    
    # 운영체제 확인
    is_windows = platform.system() == "Windows"
    
    # 가상환경 생성
    if is_windows:
        subprocess.run([sys.executable, "-m", "venv", "venv"])
    else:
        subprocess.run([sys.executable, "-m", "venv", "venv"])
    
    # pip 업그레이드
    if is_windows:
        subprocess.run([".\\venv\\Scripts\\python", "-m", "pip", "install", "--upgrade", "pip"])
    else:
        subprocess.run(["./venv/bin/python", "-m", "pip", "install", "--upgrade", "pip"])
    
    # requirements.txt 설치
    if is_windows:
        subprocess.run([".\\venv\\Scripts\\pip", "install", "-r", "requirements.txt"])
    else:
        subprocess.run(["./venv/bin/pip", "install", "-r", "requirements.txt"])
    
    # PYTHONPATH 설정 파일 생성
    create_pythonpath_script(is_windows)
    
    print("\n설정이 완료되었습니다!")
    print("\n가상환경을 활성화하려면:")
    if is_windows:
        print("    .\\venv\\Scripts\\activate")
        print('    .\\set_pythonpath.bat')
    else:
        print("    source venv/bin/activate")
        print("    source ./set_pythonpath.sh")
    print("\n프로그램을 실행하려면:")
    print("    python -m posture_guardian.main")

def create_pythonpath_script(is_windows):
    """PYTHONPATH 설정 스크립트 생성"""
    current_dir = os.path.abspath(os.path.dirname(__file__))
    
    if is_windows:
        # Windows용 배치 파일 생성
        with open("set_pythonpath.bat", "w") as f:
            f.write(f'@echo off\nset PYTHONPATH={current_dir};%PYTHONPATH%\n')
    else:
        # Unix용 셸 스크립트 생성
        with open("set_pythonpath.sh", "w") as f:
            f.write(f'#!/bin/bash\nexport PYTHONPATH="{current_dir}:$PYTHONPATH"\n')
        # 실행 권한 부여
        os.chmod("set_pythonpath.sh", 0o755)

if __name__ == "__main__":
    create_venv() 