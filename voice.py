import json, subprocess, platform, re, os, time
import speech_recognition as sr
import pyttsx3
import pyautogui
import ollama

# --- Setup ---
r = sr.Recognizer()
engine = pyttsx3.init()
mic = sr.Microphone()
SYSTEM = platform.system().lower()

# --- Speak Function ---
def speak(text):
    print(f"🗣️ {text}")
    engine.say(text)
    engine.runAndWait()

# --- Robust JSON Parsing ---
def parse_intent_locally(text):
    prompt = f"""
You are an intent extraction assistant.
Given a user command, return ONLY a JSON object.

Supported intents:
- open_app(app)
- close_app(app)
- screenshot()
- volume_up()
- volume_down()
- type(text)
- run_command(cmd)

User command: "{text}"
Output ONLY valid JSON (no explanation).
Example:
{{"intent": "open_app", "params": {{"app": "chrome"}}}}
"""
    response = ollama.chat(model="llama3.2", messages=[{"role": "user", "content": prompt}])
    content = response.get('message', {}).get('content', '').strip()

    # Extract valid JSON even if extra text appears
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if not json_match:
        print("⚠️ Raw model output (no JSON found):", content)
        return {"intent": "unknown", "params": {}}

    try:
        return json.loads(json_match.group())
    except json.JSONDecodeError:
        print("⚠️ JSON decode failed. Raw output:", content)
        return {"intent": "unknown", "params": {}}

# --- Smarter Open App Function ---
def open_app(app_name):
    if not app_name:
        speak("I didn’t catch the app name.")
        return

    app_name = app_name.lower()
    print(f"🟢 Attempting to open {app_name}...")

    try:
        if SYSTEM == "windows":
            # Try the start command (works for Chrome, Notepad, Edge, etc.)
            subprocess.run(f'start {app_name}', shell=True)
            speak(f"Opening {app_name}")
            return
        elif SYSTEM == "darwin":  # macOS
            subprocess.Popen(["open", "-a", app_name])
            speak(f"Opening {app_name}")
            return
        else:  # Linux
            subprocess.Popen([app_name])
            speak(f"Opening {app_name}")
            return
    except Exception as e:
        print(f"⚠️ Start command failed: {e}")

    # Fallback: Search manually for the .exe in common folders
    if SYSTEM == "windows":
        search_dirs = [
            r"C:\Program Files",
            r"C:\Program Files (x86)",
            os.path.expanduser(r"~\AppData\Local\Programs")
        ]
        for root_dir in search_dirs:
            for root, dirs, files in os.walk(root_dir):
                for file in files:
                    if app_name in file.lower() and file.endswith(".exe"):
                        app_path = os.path.join(root, file)
                        subprocess.Popen(app_path)
                        speak(f"Opening {app_name}")
                        return
    speak(f"Sorry, I couldn’t find {app_name} on your system.")

# --- Execute Intent ---
def execute_intent(intent_json):
    intent = intent_json.get("intent")
    params = intent_json.get("params", {})

    if intent == "open_app":
        open_app(params.get("app"))
    elif intent == "close_app":
        app = params.get("app")
        if SYSTEM == "windows" and app:
            subprocess.run(f"taskkill /f /im {app}.exe", shell=True)
            speak(f"Closed {app}")
        else:
            speak("Close app not supported on this OS yet.")
    elif intent == "screenshot":
        fname = f"screenshot_{int(time.time())}.png"
        pyautogui.screenshot(fname)
        speak("Screenshot taken.")
    elif intent == "volume_up":
        for _ in range(5):
            pyautogui.press("volumeup")
        speak("Volume increased.")
    elif intent == "volume_down":
        for _ in range(5):
            pyautogui.press("volumedown")
        speak("Volume decreased.")
    elif intent == "type":
        pyautogui.write(params.get("text", ""))
        speak("Typed it.")
    elif intent == "run_command":
        cmd = params.get("cmd")
        if cmd:
            subprocess.run(cmd, shell=True)
            speak(f"Running command {cmd}")
    else:
        speak("I didn't understand that intent.")

# --- Listen Function ---
def listen_once():
    with mic as source:
        r.adjust_for_ambient_noise(source, duration=0.5)
        print("🎙️ Listening...")
        audio = r.listen(source, phrase_time_limit=6)
        text = r.recognize_google(audio)
        print("Heard:", text)
        return text

# --- Main Loop ---
if __name__ == "__main__":
    speak("Voice control is ready.")
    while True:
        try:
            text = listen_once()
            if "goodbye" in text.lower():
                speak("Goodbye.")
                break
            intent_json = parse_intent_locally(text)
            print("Intent:", intent_json)
            execute_intent(intent_json)
        except KeyboardInterrupt:
            speak("Goodbye.")
            break
        except Exception as e:
            print("❌ Error:", e)
            speak("Something went wrong.")
