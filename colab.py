import os
import subprocess
import time
import sys
import threading

# Check if running in Colab
try:
    from google.colab import userdata
    IN_COLAB = True
except ImportError:
    IN_COLAB = False

def install_system_deps():
    """Ensures Node.js v20 and ffmpeg are installed."""
    print("⚙️ Checking system dependencies...")
    
    # Check Node version
    try:
        node_ver = subprocess.check_output(["node", "-v"]).decode().strip()
        if not node_ver.startswith("v20"):
            print(f"   Node version is {node_ver}. Upgrading to v20...")
            subprocess.run("curl -fsSL https://deb.nodesource.com/setup_20.x | bash -", shell=True, check=True)
            subprocess.run("apt-get install -y nodejs ffmpeg", shell=True, check=True)
        else:
            print(f"   ✅ Node {node_ver} is ready.")
    except (FileNotFoundError, subprocess.CalledProcessError):
         print("   Node not found. Installing v20...")
         subprocess.run("curl -fsSL https://deb.nodesource.com/setup_20.x | bash -", shell=True, check=True)
         subprocess.run("apt-get install -y nodejs ffmpeg", shell=True, check=True)

    # Install Python deps
    print("🐍 Installing Python dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
    
    # Install Frontend deps
    print("⚛️ Installing Dashboard dependencies...")
    subprocess.run(["npm", "install", "--silent"], cwd="dashboard", check=True)
    
    # Install Localtunnel
    print("🚇 Installing Localtunnel...")
    try:
        subprocess.run("npm install -g localtunnel", shell=True, check=True)
    except subprocess.CalledProcessError:
        print("❌ Failed to install localtunnel.")

def main():
    # --- 1. CREDENTIALS SETUP (FIXED) ---
    print("🔑 Setting up Credentials...")
    gemini_key = None
    
    if IN_COLAB:
        try:
            gemini_key = userdata.get('Gemini')
        except Exception:
            print("   ⚠️ Secret 'Gemini' not found in Colab Secrets.")
    else:
        gemini_key = os.environ.get("GEMINI_API_KEY")

    if gemini_key:
        os.environ["GEMINI_API_KEY"] = gemini_key
        print("   ✅ GEMINI_API_KEY detected and loaded into environment.")
    else:
        print("   ❌ GEMINI_API_KEY not found. You will need to enter it in the Dashboard.")

    # --- 2. INSTALL DEPS ---
    install_system_deps()

    # --- 3. START BACKEND ---
    print("🚀 Starting Backend...")
    # Popen inherits the current process environment (which now includes GEMINI_API_KEY)
    backend_log = open("backend.log", "w")
    backend_proc = subprocess.Popen(
        ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"],
        stdout=backend_log, stderr=subprocess.STDOUT
    )

    # --- 4. START FRONTEND ---
    print("🎨 Starting Dashboard...")
    frontend_log = open("frontend.log", "w")
    frontend_proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd="dashboard",
        stdout=frontend_log, stderr=subprocess.STDOUT
    )

    # --- 5. GET TUNNEL PASSWORD (IP) ---
    print("🔐 Fetching Tunnel Password...")
    try:
        public_ip = subprocess.check_output(["curl", "-s", "ipv4.icanhazip.com"]).decode().strip()
    except Exception:
        public_ip = "Unknown (Run '!curl ipv4.icanhazip.com' manually)"

    # --- 6. START TUNNEL ---
    print("🔗 Starting Tunnel...")
    
    def run_tunnel():
        p = subprocess.Popen(
            ["lt", "--port", "5173"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        for line in p.stdout:
            print(f"\n👉 \033[92m{line.strip()}\033[0m") # Green URL
            print(f"🔑 Tunnel Password: \033[1m{public_ip}\033[0m") # Bold IP
            print("   (Copy this IP and paste it into the tunnel page if asked)\n")

    threading.Thread(target=run_tunnel, daemon=True).start()

    print("\n" + "="*50)
    print(f"✅ OpenShorts is running!")
    print(f"⏳ Waiting for tunnel URL to appear above...")
    print("="*50 + "\n")

    try:
        while True:
            time.sleep(10)
            if backend_proc.poll() is not None:
                print("❌ Backend died. Check backend.log")
                break
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        backend_proc.terminate()
        frontend_proc.terminate()

if __name__ == "__main__":
    main()
