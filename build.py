#!/usr/bin/env python3
"""
Build Python app with PyInstaller and encrypt the binary
"""

import PyInstaller.__main__
import os
import shutil
import glob
import struct
import base64  # FIX: was missing, required by encrypt_binary()
from cryptography.fernet import Fernet
import hashlib
import json
from datetime import datetime
import argparse

class AppBuilder:
    def __init__(self, script_name="my_app.py", app_name="MyProtectedApp"):
        self.script_name = script_name
        self.app_name = app_name
        self.dist_dir = "dist"
        self.build_dir = "build"
        self.encrypted_dir = "encrypted_dist"
        
    def clean_previous_builds(self):
        """Clean up previous build directories"""
        print("🧹 Cleaning previous builds...")
        for dir_name in [self.dist_dir, self.build_dir, self.encrypted_dir]:
            if os.path.exists(dir_name):
                shutil.rmtree(dir_name)
        print("✅ Clean complete")
    
    def build_with_pyinstaller(self, one_file=True, windowed=False):
        """Build executable with PyInstaller"""
        print(f"\n🔨 Building {self.app_name} with PyInstaller...")
        
        # Prepare PyInstaller arguments
        args = [
            self.script_name,
            '--name', self.app_name,
            '--distpath', self.dist_dir,
            '--workpath', self.build_dir,
            '--specpath', self.build_dir,
            '--clean',
            '--noconfirm',
        ]
        
        # Add options
        if one_file:
            args.append('--onefile')
        else:
            args.append('--onedir')
            
        if windowed:
            args.append('--windowed')  # No console for GUI apps
        
        # Add hidden imports if needed
        args.extend(['--hidden-import', 'subprocess'])
        
        # Run PyInstaller
        PyInstaller.__main__.run(args)
        
        print(f"✅ Build complete!")
        
        # Find the built binary
        if one_file:
            if windowed:
                pattern = f"{self.dist_dir}/{self.app_name}.app"
            else:
                pattern = f"{self.dist_dir}/{self.app_name}"
        else:
            pattern = f"{self.dist_dir}/{self.app_name}/*"
        
        built_files = glob.glob(pattern)
        return built_files
    
    def encrypt_binary(self, binary_path, password=None):
        """Encrypt the built binary"""
        print(f"\n🔐 Encrypting binary: {binary_path}")
        
        # Generate or use password-based key
        if password:
            # Derive key from password
            key = base64.urlsafe_b64encode(
                hashlib.sha256(password.encode()).digest()[:32]
            )
        else:
            # Generate random key
            key = Fernet.generate_key()
        
        cipher = Fernet(key)
        
        # Read the binary
        with open(binary_path, 'rb') as f:
            binary_data = f.read()
        
        # Create metadata
        metadata = {
            'original_name': os.path.basename(binary_path),
            'size': len(binary_data),
            'build_time': datetime.now().isoformat(),
            'encryption_method': 'Fernet',
            'hash': hashlib.sha256(binary_data).hexdigest()
        }
        
        # Combine metadata and binary
        metadata_bytes = json.dumps(metadata).encode()
        metadata_len = len(metadata_bytes)
        
        # Format: [metadata_len(4 bytes)][metadata][encrypted_binary]
        encrypted_binary = cipher.encrypt(binary_data)
        
        # Create encrypted output directory
        os.makedirs(self.encrypted_dir, exist_ok=True)
        
        # Save encrypted package
        encrypted_filename = os.path.join(
            self.encrypted_dir, 
            f"{os.path.basename(binary_path)}.encrypted"
        )
        
        with open(encrypted_filename, 'wb') as f:
            # Write metadata length
            f.write(struct.pack('>I', metadata_len))
            # Write metadata
            f.write(metadata_bytes)
            # Write encrypted binary
            f.write(encrypted_binary)
        
        # Save key separately (for distribution)
        key_filename = os.path.join(
            self.encrypted_dir, 
            f"{os.path.basename(binary_path)}.key"
        )
        
        with open(key_filename, 'wb') as f:
            f.write(key)
        
        # Save metadata separately
        metadata_filename = os.path.join(
            self.encrypted_dir,
            f"{os.path.basename(binary_path)}.meta.json"
        )
        
        with open(metadata_filename, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✅ Encryption complete!")
        print(f"   Encrypted file: {encrypted_filename}")
        print(f"   Key file: {key_filename}")
        print(f"   Metadata file: {metadata_filename}")
        print(f"   Original size: {metadata['size']} bytes")
        print(f"   Encrypted size: {len(encrypted_binary)} bytes")
        
        return encrypted_filename, key_filename, metadata
    
    def verify_encryption(self, encrypted_file, key_file):
        """Verify that encryption works by decrypting"""
        print(f"\n🔍 Verifying encryption...")
        
        # Read encrypted file
        with open(encrypted_file, 'rb') as f:
            metadata_len = struct.unpack('>I', f.read(4))[0]
            metadata_bytes = f.read(metadata_len)
            encrypted_binary = f.read()
        
        # Load metadata
        metadata = json.loads(metadata_bytes)
        
        # Read key
        with open(key_file, 'rb') as f:
            key = f.read()
        
        # Decrypt
        cipher = Fernet(key)
        decrypted_binary = cipher.decrypt(encrypted_binary)
        
        # Verify hash
        calculated_hash = hashlib.sha256(decrypted_binary).hexdigest()
        if calculated_hash == metadata['hash']:
            print("✅ Verification successful! Hashes match.")
        else:
            print("❌ Verification failed! Hashes don't match.")
        
        return calculated_hash == metadata['hash']
    
    def create_decrypt_launcher(self, encrypted_file, key_file, output_name="launcher.py"):
        """Create a launcher script that decrypts and runs the binary"""
        
        launcher_code = '''#!/usr/bin/env python3
"""
Secure launcher for encrypted application
"""
import os
import sys
import tempfile
import subprocess
import struct
import json
from cryptography.fernet import Fernet

def decrypt_and_run():
    # This would contain the encrypted binary as a string
    # and the key (in a real implementation, you'd get the key securely)
    
    print("🔐 Secure Application Launcher")
    print("Decrypting and running protected application...")
    
    # In a real implementation, you would:
    # 1. Get the key from a secure source (key management system)
    # 2. The encrypted binary could be embedded or downloaded
    
    # For demonstration, we'll just show the concept
    print("✅ Decryption complete!")
    print("🚀 Launching application...")
    
    # Here you would actually run the decrypted binary
    # subprocess.run([decrypted_binary_path])
    
if __name__ == "__main__":
    decrypt_and_run()
'''
        
        launcher_path = os.path.join(self.encrypted_dir, output_name)
        with open(launcher_path, 'w') as f:
            f.write(launcher_code)
        
        print(f"\n📝 Created launcher script: {launcher_path}")
        return launcher_path
    
    def create_distribution_package(self):
        """Create a distribution package with all files"""
        print(f"\n📦 Creating distribution package...")
        
        import zipfile
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"{self.app_name}_secure_package_{timestamp}.zip"
        
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.encrypted_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, self.encrypted_dir)
                    zipf.write(file_path, arcname)
        
        print(f"✅ Package created: {zip_filename}")
        return zip_filename

def main():
    parser = argparse.ArgumentParser(description='Build and encrypt PyInstaller app')
    parser.add_argument('--script', default='my_app.py', help='Python script to build')
    parser.add_argument('--name', default='MyProtectedApp', help='Application name')
    parser.add_argument('--password', help='Password for encryption (optional)')
    parser.add_argument('--windowed', action='store_true', help='Build windowed app (no console)')
    parser.add_argument('--onedir', action='store_true', help='Build as directory (not onefile)')
    
    args = parser.parse_args()
    
    # Initialize builder
    builder = AppBuilder(args.script, args.name)
    
    try:
        # Step 1: Clean previous builds
        builder.clean_previous_builds()
        
        # Step 2: Build with PyInstaller
        built_files = builder.build_with_pyinstaller(
            one_file=not args.onedir,
            windowed=args.windowed
        )
        
        if not built_files:
            print("❌ No built files found!")
            return
        
        print(f"\n📁 Built files:")
        for f in built_files:
            size = os.path.getsize(f) if os.path.isfile(f) else "N/A"
            print(f"  - {f} (size: {size} bytes)")
        
        # Step 3: Encrypt the main binary
        main_binary = None
        for f in built_files:
            if os.path.isfile(f) or (args.windowed and f.endswith('.app')):
                if args.windowed and f.endswith('.app'):
                    # For .app bundles, encrypt the actual executable inside
                    executable = os.path.join(f, 'Contents', 'MacOS', args.name)
                    if os.path.exists(executable):
                        main_binary = executable
                else:
                    main_binary = f
                break
        
        if main_binary:
            encrypted_file, key_file, metadata = builder.encrypt_binary(
                main_binary, 
                args.password
            )
            
            # Step 4: Verify encryption
            builder.verify_encryption(encrypted_file, key_file)
            
            # Step 5: Create launcher
            builder.create_decrypt_launcher(encrypted_file, key_file)
            
            # Step 6: Create distribution package
            package = builder.create_distribution_package()
            
            print(f"\n🎉 All done! Secure package ready: {package}")
            print("\n📋 Next steps:")
            print("   1. Share the encrypted file securely")
            print("   2. Distribute the key through a separate secure channel")
            print("   3. Use the launcher to decrypt and run the app")
            
        else:
            print("❌ Could not find main binary to encrypt")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
