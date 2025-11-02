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

# --- Helper: Detect file extension from code ---
def detect_extension(code):
    if "<html>" in code or "<body>" in code:
        return "html"
    elif "import " in code or "def " in code:
        return "py"
    elif "class " in code and "public static void main" in code:
        return "java"
    elif "function " in code or "console.log" in code:
        return "js"
    elif re.search(r"\{[\s\S]*\}", code) and not "<html>" in code:
        return "css"
    else:
        return "txt"

# --- 🆕 Smart code generation with auto-detection ---
def generate_code(prompt_text):
    """Ask Llama to generate complete multi-language code when needed."""
    code_prompt = f"""
The user said: "{prompt_text}"

Your task:
- Generate the full working code.
- If it's a web project, include HTML, CSS, and JavaScript in one file.
- If it's a backend or script, write full code with imports.
- If it's multi-file, combine everything in one file logically.
- Output ONLY code, no explanation, no markdown fences.
"""
    try:
        response = ollama.chat(model="llama3.2", messages=[{"role": "user", "content": code_prompt}])
        code = response.get("message", {}).get("content", "").strip()
        print("💻 Generated Code:\n", code[:500], "...\n")
        return code
    except Exception as e:
        print("⚠️ Code generation error:", e)
        return None

# --- 🆕 Enhanced intent extraction (more flexible) ---
def parse_intent_locally(text):
    prompt = f"""
You are an intent extraction assistant.
Analyze this command and return ONLY valid JSON.

Supported intents:
- open_app(app)
- close_app(app)
- screenshot()
- volume_up()
- volume_down()
- type(text)
- run_command(cmd)
- write_code(description)

User said: "{text}"

If the user is asking to create, write, design, or build something, use:
{{"intent": "write_code", "params": {{"description": "<full user request>"}}}}

Return ONLY valid JSON.
"""
    response = ollama.chat(model="llama3.2", messages=[{"role": "user", "content": prompt}])
    content = response.get('message', {}).get('content', '').strip()
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if not json_match:
        return {"intent": "unknown", "params": {}}

    try:
        data = json.loads(json_match.group())
        # 🩵 Fix: wrap 'description' in params if missing
        if data.get("intent") == "write_code" and "params" not in data:
            desc = data.get("description") or text
            data = {"intent": "write_code", "params": {"description": desc}}
        return data
    except:
        return {"intent": "unknown", "params": {}}


# --- Open App ---
def open_app(app_name):
    if not app_name:
        speak("I didn’t catch the app name.")
        return
    app_name = app_name.lower()
    try:
        if SYSTEM == "windows":
            subprocess.run(f'start {app_name}', shell=True)
        elif SYSTEM == "darwin":
            subprocess.Popen(["open", "-a", app_name])
        else:
            subprocess.Popen([app_name])
        speak(f"Opening {app_name}")
    except Exception as e:
        print("⚠️ Could not open app:", e)
        speak(f"Sorry, I couldn’t open {app_name}.")

# --- 🆕 Save code to file and open ---
def save_code_to_file(code, description):
    ext = detect_extension(code)
    safe_name = re.sub(r'[^a-zA-Z0-9]', '_', description.strip().lower())[:30]
    filename = f"{safe_name}_{int(time.time())}.{ext}"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"✅ Code saved as {filename}")

    # Open in VS Code if installed, otherwise Notepad
    if os.path.exists("C:\\Users\\Public\\Desktop\\Visual Studio Code.lnk") or \
       os.path.exists("C:\\Program Files\\Microsoft VS Code\\Code.exe"):
        subprocess.run(f'code {filename}', shell=True)
        speak(f"Code saved and opened in VS Code.")
    else:
        os.system(f"notepad {filename}")
        speak(f"Code saved and opened in Notepad.")

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
        text = params.get("text", "")
        pyautogui.write(text)
        speak("Typed your text.")

    elif intent == "run_command":
        cmd = params.get("cmd")
        if cmd:
            subprocess.run(cmd, shell=True)
            speak(f"Running command {cmd}")

    elif intent == "write_code":  # 🆕 Now fully featured
        description = params.get("description", "")
        if not description:
            speak("Please tell me what code to write.")
            return
        speak(f"Generating code for {description}")
        code = generate_code(description)
        if code:
            save_code_to_file(code, description)
        else:
            speak("Sorry, I couldn't generate the code right now.")

    else:
        speak("I didn't understand that intent.")

# --- Listen Function ---
def listen_once():
    with mic as source:
        r.adjust_for_ambient_noise(source, duration=0.5)
        print("🎙️ Listening...")
        audio = r.listen(source, phrase_time_limit=8)
        text = r.recognize_google(audio)
        print("Heard:", text)
        return text

# --- Main Loop ---
if __name__ == "__main__":
    speak("Voice coding assistant ready.")
    while True:
        try:
            text = listen_once()
            if not text:
                continue
            if "goodbye" in text.lower() or "exit" in text.lower():
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
