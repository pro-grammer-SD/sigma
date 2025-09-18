import os
import ntplib
from datetime import datetime, timezone
from dotenv import load_dotenv
from io import BytesIO
import sounddevice as sd
from scipy.io.wavfile import write
from elevenlabs.client import ElevenLabs
from elevenlabs import play
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
import pyautogui
import screen_brightness_control as sbc
import re
from word2number import w2n
from google import genai

load_dotenv()

elevenlabs = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

voice_id = "JBFqnCBsd6RMkjVDRZzb"
sample_rate = 44100
duration = 5

devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume = interface.QueryInterface(IAudioEndpointVolume)

def speak(text):
    audio = elevenlabs.text_to_speech.convert(
        text=f"Rizzing up {text}, master!",
        voice_id=voice_id,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )
    play(audio)

def set_brightness_level(percent):
    percent = max(0, min(100, percent))
    sbc.set_brightness(percent)

def contains_all(words, text):
    return all(word in text for word in words)

def extract_number(text, keyword):
    match = re.search(fr"{keyword} to ([\w\s]+?)(?: percent|%)", text)
    if match:
        val = match.group(1).strip()
        try:
            return w2n.word_to_num(val)
        except:
            digits = re.findall(r"\d+", val)
            if digits:
                return int(digits[0])
    return None

def get_real_time():
    try:
        client = ntplib.NTPClient()
        response = client.request('pool.ntp.org', version=3)
        return datetime.fromtimestamp(response.tx_time, tz=timezone.utc)
    except:
        return datetime.now(timezone.utc)

screenshot_counter = 1
os.makedirs("sigma_screenshots", exist_ok=True)

while True:
    print("🎤 Recording...")
    recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
    sd.wait()
    print("✅ Recording finished")

    buffer = BytesIO()
    write(buffer, sample_rate, recording)
    buffer.seek(0)

    try:
        transcription = elevenlabs.speech_to_text.convert(
            file=buffer,
            model_id="scribe_v1",
            tag_audio_events=True,
            language_code="eng",
            diarize=True,
        )
        result = " ".join([w.text for w in transcription.words if w.type == "word"]).lower()
        print(result)

        if contains_all(["sigma", "turn", "up", "volume"], result):
            speak("turn up the volume")
            vol = volume.GetMasterVolumeLevelScalar()
            volume.SetMasterVolumeLevelScalar(min(vol + 0.1, 1.0), None)

        elif contains_all(["sigma", "turn", "down", "volume"], result):
            speak("turn down the volume")
            vol = volume.GetMasterVolumeLevelScalar()
            volume.SetMasterVolumeLevelScalar(max(vol - 0.1, 0.0), None)

        elif contains_all(["sigma", "mute"], result):
            speak("muting")
            volume.SetMute(1, None)

        elif contains_all(["sigma", "unmute"], result):
            speak("unmuting")
            volume.SetMute(0, None)

        elif contains_all(["sigma", "set", "volume", "to"], result):
            level = extract_number(result, "volume")
            if level is not None:
                level = max(0, min(level, 100))
                speak(f"set volume to {level} percent")
                volume.SetMasterVolumeLevelScalar(level / 100, None)

        elif contains_all(["sigma", "increase", "brightness"], result):
            speak("brightening")
            sbc.set_brightness(min(sbc.get_brightness()[0] + 10, 100))

        elif contains_all(["sigma", "decrease", "brightness"], result):
            speak("dimming")
            sbc.set_brightness(max(sbc.get_brightness()[0] - 10, 0))

        elif contains_all(["sigma", "brightness", "lowest"], result):
            speak("set brightness to lowest")
            sbc.set_brightness(0)

        elif contains_all(["sigma", "brightness", "highest"], result):
            speak("set brightness to highest")
            sbc.set_brightness(100)

        elif contains_all(["sigma", "set", "brightness", "to"], result):
            level = extract_number(result, "brightness")
            if level is not None:
                level = max(0, min(level, 100))
                speak(f"set brightness to {level} percent")
                set_brightness_level(level)

        elif contains_all(["sigma", "answer"], result):
            question = result.split("answer", 1)[1].strip()
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"A short answer on: {question}"
            )
            answer = response.text.strip()
            print(answer)
            speak(answer)

        elif contains_all(["sigma", "time"], result):
            now = get_real_time()
            current_time = now.strftime("%H:%M %p UTC")
            print(f"The time is {current_time}")
            speak(f"The time is {current_time}")

        elif contains_all(["sigma", "screenshot"], result):
            speak("taking screenshot")
            path = f"sigma_screenshots/screenshot_{screenshot_counter}.png"
            pyautogui.screenshot(path)
            screenshot_counter += 1
            
        elif contains_all(["sigma", "desktop"], result):
            speak("showing desktop")
            pyautogui.hotkey("win", "d")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        