import subprocess, sys, os, shutil

def main():
    base = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(base, "wuwa_overlay_v4.py")
    json_file   = os.path.join(base, "wuwa_chars.json")

    # PyInstaller 없으면 설치
    try:
        import PyInstaller
    except ImportError:
        print("[빌드] PyInstaller 설치 중...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # keyboard 없으면 설치
    try:
        import keyboard
    except ImportError:
        print("[빌드] keyboard 설치 중...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "keyboard"])

    # wuwa_chars.json 없으면 빈 파일 생성
    if not os.path.exists(json_file):
        with open(json_file, "w", encoding="utf-8") as f:
            f.write("{}")
        print("[빌드] wuwa_chars.json 없음 → 빈 파일 생성")

    print("[빌드] 빌드 시작...")

    icon_file = os.path.join(base, "00085-3009505209.ico")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "명조오버레이",
        "--add-data", f"{json_file};.",
        "--hidden-import", "keyboard",
        "--hidden-import", "tkinter",
        "--clean",
    ]

    if os.path.exists(icon_file):
        cmd += ["--icon", icon_file]

    cmd.append(main_script)

    result = subprocess.run(cmd, cwd=base)

    if result.returncode == 0:
        exe_path = os.path.join(base, "dist", "명조오버레이.exe")
        print(f"\n✅ 빌드 성공!")
        print(f"   실행파일: {exe_path}")
        print(f"\n※ 실행 시 wuwa_chars.json을 exe와 같은 폴더에 두세요.")
        print(f"   (처음 실행하면 자동 생성되지만, 기존 데이터 유지하려면 복사)")
    else:
        print("\n❌ 빌드 실패. 위 오류 메시지 확인하세요.")

if __name__ == "__main__":
    main()
