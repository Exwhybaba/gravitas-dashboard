#!/usr/bin/env python
"""
Build script to create Gravitas_Power_app standalone executable
Bundles app.py with assets folder using PyInstaller
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def build_executable():
    """Build the Gravitas Power App executable"""
    
    script_dir = Path(__file__).parent
    spec_file = script_dir / "Gravitas_Power_app.spec"
    
    print("=" * 70)
    print("🔨 Building Gravitas Power App Standalone Executable")
    print("=" * 70)
    
    # Verify assets folder exists
    assets_dir = script_dir / "assets"
    if not assets_dir.exists():
        print("❌ ERROR: Assets folder not found at:", assets_dir)
        return False
    
    print(f"✓ Assets folder found: {assets_dir}")
    
    # Verify spec file
    if not spec_file.exists():
        print(f"❌ ERROR: Spec file not found at: {spec_file}")
        return False
    
    print(f"✓ Spec file found: {spec_file}")
    
    # Clean previous build artifacts
    print("\n📦 Cleaning previous build artifacts...")
    for folder in ["build", "dist"]:
        folder_path = script_dir / folder
        if folder_path.exists():
            shutil.rmtree(folder_path)
            print(f"  ✓ Removed {folder}/")
    
    # Build the executable
    print("\n🔧 Building executable with PyInstaller...")
    print("   (This may take 2-5 minutes...)\n")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "PyInstaller", str(spec_file)],
            cwd=str(script_dir),
            capture_output=False,
            text=True
        )
        
        if result.returncode != 0:
            print("\n❌ Build failed!")
            return False
            
    except Exception as e:
        print(f"\n❌ Error during build: {e}")
        return False
    
    # Verify the executable was created
    exe_path = script_dir / "dist" / "Gravitas_Power_app" / "Gravitas_Power_app.exe"
    
    if exe_path.exists():
        exe_size_mb = exe_path.stat().st_size / (1024 * 1024)
        print("\n" + "=" * 70)
        print("✅ BUILD SUCCESSFUL!")
        print("=" * 70)
        print(f"📍 Executable Location: {exe_path}")
        print(f"📊 Executable Size: {exe_size_mb:.1f} MB")
        print(f"📂 Full Package Location: {script_dir / 'dist' / 'Gravitas_Power_app'}")
        print("\n🚀 To run the application:")
        print(f"   1. Navigate to: {script_dir / 'dist' / 'Gravitas_Power_app'}")
        print(f"   2. Double-click: Gravitas_Power_app.exe")
        print(f"\n   Or run from PowerShell:")
        print(f"   .\\dist\\Gravitas_Power_app\\Gravitas_Power_app.exe")
        print("\n📋 Files included:")
        print("   ✓ app.py (bundled)")
        print("   ✓ assets/ folder (logos, images, CSS, JavaScript)")
        print("   ✓ All Python dependencies")
        print("   ✓ Flask server")
        print("=" * 70)
        return True
    else:
        print("\n❌ Executable not found after build!")
        print(f"   Expected: {exe_path}")
        return False

if __name__ == "__main__":
    success = build_executable()
    sys.exit(0 if success else 1)
