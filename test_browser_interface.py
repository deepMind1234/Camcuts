import subprocess
import time
import sys

def get_windows():
    """List all windows with IDs and names."""
    try:
        res = subprocess.run('xdotool search --all --name "."', shell=True, capture_output=True, text=True)
        if res.returncode != 0:
            return []
        
        window_ids = res.stdout.splitlines()
        windows = []
        for wid in window_ids:
            name_res = subprocess.run(f'xdotool getwindowname {wid}', shell=True, capture_output=True, text=True)
            name = name_res.stdout.strip()
            if name:
                windows.append((wid, name))
        return windows
    except Exception as e:
        print(f"Error: {e}")
        return []

def test_keystroke(window_id):
    """Attempt multiple methods to send 'k' to the window."""
    print(f"\n--- Testing Window ID: {window_id} ---")
    
    # Method 1: Background key send
    print(f"Method 1: Direct background send (xdotool key --window {window_id} k)")
    subprocess.run(f"xdotool key --window {window_id} --clearmodifiers k", shell=True)
    time.sleep(1)
    
    # Method 2: Focus and send
    print(f"Method 2: Window focus + key (xdotool windowfocus {window_id} key k)")
    subprocess.run(f"xdotool windowfocus {window_id} key --clearmodifiers k", shell=True)
    time.sleep(1)
    
    # Method 3: Window activate + key
    print(f"Method 3: Window activate + key (xdotool windowactivate {window_id} key k)")
    subprocess.run(f"xdotool windowactivate --sync {window_id} key --clearmodifiers k", shell=True)
    
    print("\nTest complete. Check if the video paused/played.")

if __name__ == "__main__":
    windows = get_windows()
    if not windows:
        print("No windows found. Ensure you are in an X11/Wayland environment.")
        sys.exit(1)
    
    print("Select a window to test (Type the number) or enter 'p' followed by PID:")
    for i, (wid, name) in enumerate(windows):
        print(f"[{i}] ID: {wid} | Name: {name}")
    
    try:
        raw_choice = input("\nChoice (e.g., '0' or 'p64637'): ").strip()
        if raw_choice.startswith('p'):
            pid = raw_choice[1:]
            print(f"Searching for windows associated with PID: {pid}")
            res = subprocess.run(f"xdotool search --pid {pid}", shell=True, capture_output=True, text=True)
            wids = res.stdout.splitlines()
            if not wids:
                print(f"No windows found for PID {pid}")
            else:
                for wid in wids:
                    test_keystroke(wid)
        else:
            choice = int(raw_choice)
            if 0 <= choice < len(windows):
                wid = windows[choice][0]
                test_keystroke(wid)
            else:
                print("Invalid choice.")
    except Exception as e:
        print(f"Error: {e}")
