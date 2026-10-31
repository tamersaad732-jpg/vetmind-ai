"""
VetMind AI - Daemon Deactivated Notice
This local background daemon has been retired because VetMind AI is now 
hosted directly on Vercel 24/7 (https://vetmind-ai.vercel.app/).
Local Cloudflare tunneling is no longer needed and has been disabled.
"""
import sys

def main():
    print("VetMind AI is hosted 24/7 on Vercel. Local daemon is permanently disabled.")
    sys.exit(0)

if __name__ == "__main__":
    main()
