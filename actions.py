import subprocess
import pyautogui
import threading
import os

class ActionExecutor:
    def __init__(self):
        # Prevent pyautogui from failing if it can't find a display (common in some linux envs)
        pyautogui.FAILSAFE = True
        self.manual_window_id = None

    def list_all_windows(self):
        """Returns a list of all window names and their IDs."""
        try:
            # Get all window IDs
            res = subprocess.run('xdotool search --all --name "."', shell=True, capture_output=True, text=True)
            if res.returncode != 0:
                print("No windows found or xdotool search failed.")
                return []
            
            window_ids = res.stdout.splitlines()
            windows = []
            for wid in window_ids:
                name_res = subprocess.run(f'xdotool getwindowname {wid}', shell=True, capture_output=True, text=True)
                name = name_res.stdout.strip()
                if name and name != "Camcuts Overlay": # Ignore self
                    windows.append((wid, name))
            return windows
        except Exception as e:
            print(f"Error listing windows: {e}")
            return []

    def pick_target_window(self):
        """Allows the user to manually click on a window to select it as the target."""
        print("Please click on the window you want to control...")
        try:
            # xdotool selectwindow lets the user click on a window
            res = subprocess.run("xdotool selectwindow", shell=True, capture_output=True, text=True)
            if res.returncode == 0:
                self.manual_window_id = res.stdout.strip()
                print(f"Manual target window set to: {self.manual_window_id}")
            else:
                print("Window selection cancelled or failed.")
        except Exception as e:
            print(f"Error selecting window: {e}")

    def execute(self, action_type: str, command: str):
        """Execute an action in a separate thread to avoid blocking."""
        thread = threading.Thread(target=self._run_action, args=(action_type, command))
        thread.daemon = True
        thread.start()

    def _run_action(self, action_type: str, command: str):
        try:
            if action_type == "terminal":
                print(f"Executing terminal command: {command}")
                subprocess.run(command, shell=True, check=True)
            elif action_type == "keystroke":
                print(f"Triggering targeted keystroke: {command}")
                
                xdotool_base = f"key --clearmodifiers"
                
                # Use manual target if set
                if self.manual_window_id:
                    # Method 1: Send directly to window (often fails in browsers but stealthy)
                    subprocess.run(f"xdotool key --window {self.manual_window_id} --clearmodifiers {command}", shell=True)
                    # Method 2: Focus and send (Required for most browsers)
                    subprocess.run(f"xdotool windowfocus {self.manual_window_id} {xdotool_base} {command}", shell=True)
                    print(f"Sent {command} to manual target {self.manual_window_id}")
                    return

                # Try to find a media window
                # Using regex for case-insensitivity and searching specifically for 
                # names that are likely to be the main browser window.
                targets = ["YouTube", "Chromium", "Google-chrome", "Firefox", "Brave"]
                success = False
                
                # Broad search first
                for target in targets:
                    # xdotool search is case-sensitive by default, but we can use flags
                    # or just try both common casing.
                    # We also filter out common "ghost" windows like clipboards.
                    cmd = f'xdotool search --name "{target}"'
                    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    
                    if res.stdout.strip():
                        wids = res.stdout.splitlines()
                        for wid in wids:
                            # Get name to verify it's not a clipboard or background helper
                            name_res = subprocess.run(f"xdotool getwindowname {wid}", shell=True, capture_output=True, text=True)
                            name = name_res.stdout.strip().lower()
                            
                            # Filter out common false positives
                            if any(x in name for x in ["clipboard", "guard window", "settings", "extension"]):
                                continue
                                
                            # If we made it here, this is likely our target!
                            subprocess.run(f"xdotool windowfocus {wid} {xdotool_base} {command}", shell=True)
                            print(f"Auto-focused and sent {command} to: {name} (window {wid})")
                            success = True
                            break
                    if success: break # Stop searching other targets if found
                
                if not success:
                    # Fallback to general active window
                    pyautogui.press(command)
            elif action_type == "type":
                print(f"Typing text: {command}")
                pyautogui.write(command)
            elif action_type == "openclaw":
                self._trigger_openclaw(command)
            else:
                print(f"Unknown action type: {action_type}")
        except Exception as e:
            print(f"Error executing action {action_type}: {e}")

    def _trigger_openclaw(self, command: str):
        # Implementation for OpenClaw
        # Since OpenClaw uses MCP, we could potentially use an MCP client here.
        # For now, we'll log it as a placeholder.
        print(f"OpenClaw Action Triggered: {command}")
        # Example: os.system(f"openclaw send '{command}'")
