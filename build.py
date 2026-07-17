import subprocess, sys, os, shutil

def main():
    base = os.path.dirname(os.path.abspath(__file__))
    main_script    = os.path.join(base, "wuwa_overlay_v5.py")
    updater_script = os.path.join(base, "wuwa_updater.py")
    version_file   = os.path.join(base, "version.txt")

    if not os.path.exists(version_file):
        print("[빌드] version.txt 없음 → 생성 필요")

    try:
        import PyInstaller
    except ImportError:
        print("[빌드] PyInstaller 설치 중...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    try:
        import keyboard
    except ImportError:
        print("[빌드] keyboard 설치 중...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "keyboard"])


    print("[빌드] 빌드 시작...")

    icon_file = os.path.join(base, "app.ico")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "ddaljalky",
        "--hidden-import", "tkinter",
        "--hidden-import", "winrt.windows.media.ocr",
        "--hidden-import", "winrt.windows.graphics.imaging",
        "--hidden-import", "winrt.windows.storage.streams",
        "--hidden-import", "winrt.windows.foundation",
        "--hidden-import", "winrt.windows.foundation.collections",

        "--add-data", f"{updater_script};.",
        "--add-data", f"{version_file};.",
        "--clean",
    ]

    if os.path.exists(icon_file):
        cmd += ["--icon", icon_file]
        cmd += ["--add-data", f"{icon_file};."]

    cmd.append(main_script)

    result = subprocess.run(cmd, cwd=base)

    if result.returncode == 0:
        exe_path = os.path.join(base, "dist", "ddaljalky.exe")
        print(f"\n✅ 빌드 성공!")
        print(f"   실행파일: {exe_path}")
        print(f"\n※ 첫 실행 시 자동으로 가이드데이터를 %appdata%에 다운로드합니다.")
        print(f"   (삭제할때는 안에 ddaljalky 폴더 지워주시면 됩니다.)")
    else:
        print("\n❌ 빌드 실패. 위 오류 메시지 확인하세요.")

if __name__ == "__main__":
    main()
