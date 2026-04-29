# [FILE: ras_monitor/build.py]
"""
Build script for PyInstaller packaging.
Creates a standalone .exe executable for RAS Monitor.

Usage:
    python build.py

Output:
    dist/RAS Monitor/ - onedir bundle with all dependencies
"""

import os
import sys
import subprocess
from pathlib import Path


def main():
    """Run PyInstaller to build the executable."""
    
    # Get the project root directory
    project_root = Path(__file__).parent.absolute()
    
    # Paths
    main_script = project_root / "main.py"
    output_dir = project_root / "dist"
    build_dir = project_root / "build"
    spec_dir = project_root
    
    # Model files to include
    model_path = project_root / "ml" / "model.pth"
    scaler_path = project_root / "ml" / "scaler.pkl"
    
    # Check if model files exist
    if not model_path.exists():
        print("WARNING: model.pth not found in ml/ directory!")
        print("Please run 'python ml/train.py' first to train the model.")
        print("Continuing without model files...")
        include_ml_data = False
    else:
        include_ml_data = True
    
    if not scaler_path.exists():
        print("WARNING: scaler.pkl not found in ml/ directory!")
        print("Please run 'python ml/train.py' first to train the model.")
        include_ml_data = False
    
    # Build PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "RAS Monitor",
        "--onedir",  # Use onedir mode (recommended for PyTorch)
        "--windowed",  # No console window
        "--clean",  # Clean build cache
        f"--distpath={output_dir}",
        f"--workpath={build_dir}",
        f"--specpath={spec_dir}",
        "--hidden-import=torch",
        "--hidden-import=torch.nn",
        "--hidden-import=torch.nn.functional",
        "--hidden-import=PyQt6",
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtGui",
        "--hidden-import=PyQt6.QtWidgets",
        "--hidden-import=numpy",
        "--hidden-import=pandas",
        "--hidden-import=matplotlib",
        "--hidden-import=sklearn",
        "--collect-all=torch",
        "--collect-all=PyQt6",
    ]
    
    # Add data files for ML model
    if include_ml_data:
        # Format: source;destination
        ml_data = str(project_root / "ml" / "model.pth") + ";ml"
        scaler_data = str(project_root / "ml" / "scaler.pkl") + ";ml"
        cmd.extend([
            f"--add-data={ml_data}",
            f"--add-data={scaler_data}",
        ])
    
    # Add main script
    cmd.append(str(main_script))
    
    print("=" * 60)
    print("RAS Monitor - PyInstaller Build Script")
    print("=" * 60)
    print(f"\nProject root: {project_root}")
    print(f"Main script: {main_script}")
    print(f"Output directory: {output_dir}")
    print(f"Include ML models: {include_ml_data}")
    print("\nPyInstaller command:")
    print(" ".join(cmd))
    print("\n" + "=" * 60)
    print("Starting build process...")
    print("=" * 60 + "\n")
    
    # Run PyInstaller
    try:
        result = subprocess.run(
            cmd,
            cwd=project_root,
            check=True,
            capture_output=False
        )
        
        print("\n" + "=" * 60)
        print("BUILD COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"\nExecutable location: {output_dir / 'RAS Monitor'}")
        print(f"Main executable: {(output_dir / 'RAS Monitor' / 'RAS Monitor.exe') if os.name == 'nt' else (output_dir / 'RAS Monitor' / 'RAS Monitor')}")
        print("\nTo distribute:")
        print("1. Copy the entire 'RAS Monitor' folder from dist/")
        print("2. Include all DLLs and dependencies in the folder")
        print("3. End users can run RAS Monitor.exe directly")
        
    except subprocess.CalledProcessError as e:
        print("\n" + "=" * 60)
        print("BUILD FAILED!")
        print("=" * 60)
        print(f"Error code: {e.returncode}")
        print("\nCommon issues:")
        print("- Missing dependencies: run 'pip install -r requirements.txt'")
        print("- Model files missing: run 'python ml/train.py'")
        print("- Insufficient disk space")
        sys.exit(1)
    
    except FileNotFoundError:
        print("\n" + "=" * 60)
        print("BUILD FAILED!")
        print("=" * 60)
        print("PyInstaller not found. Install it with:")
        print("pip install pyinstaller")
        sys.exit(1)


if __name__ == "__main__":
    main()
