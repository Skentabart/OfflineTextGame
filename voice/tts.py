# -*- coding: utf-8 -*-
import queue
import threading
import re
import time


class SpeechSynthesizer:
    def __init__(self):
        self.q = queue.Queue()
        self.stop_event = threading.Event()
        self.speaking = threading.Event()
        self.thread = None
        self.voice = None
        self.pythoncom = None
        self.ready = False
        self.worker_alive = False
        self.error = None

    def load(self):
        self.thread = threading.Thread(target=self._worker, name='TTS-Worker', daemon=True)
        self.thread.start()
        started = time.monotonic()
        while not self.ready and self.thread.is_alive():
            if time.monotonic() - started > 5:
                break
            time.sleep(.03)
        return self.ready

    def _worker(self):
        self.worker_alive = True
        try:
            import pythoncom
            import win32com.client
            pythoncom.CoInitialize()
            self.pythoncom = pythoncom
            self.voice = win32com.client.Dispatch('SAPI.SpVoice')
            self.voice.Rate = 0
            self.voice.Volume = 100
            try:
                voices = self.voice.GetVoices()
                for i in range(voices.Count):
                    token = voices.Item(i)
                    description = str(token.GetDescription(0)).lower()
                    if 'russian' in description or 'рус' in description:
                        self.voice.Voice = token
                        break
            except Exception:
                pass
            self.ready = True
        except Exception as exc:
            self.error = exc
            self.ready = False

        while not self.stop_event.is_set():
            try:
                text = self.q.get(timeout=.1)
            except queue.Empty:
                continue

            if text is None:
                self.q.task_done()
                break

            self.speaking.set()
            try:
                text = re.sub(r'\s+', ' ', str(text)).strip()
                if text and self.voice:
                    self.voice.Speak(text, 0)
            except Exception as exc:
                self.error = exc
            finally:
                self.speaking.clear()
                self.q.task_done()

        self.worker_alive = False
        try:
            if self.voice:
                self.voice.Speak('', 2)
        except Exception:
            pass
        try:
            if self.pythoncom:
                self.pythoncom.CoUninitialize()
        except Exception:
            pass

    def speak(self, text, wait=False):
        if not text or not self.ready or not self.worker_alive or self.stop_event.is_set():
            return False
        try:
            self.q.put_nowait(str(text))
        except Exception:
            return False
        if wait:
            return self.wait(timeout=8)
        return True

    def wait(self, timeout=8):
        deadline = time.monotonic() + max(.1, timeout)
        while time.monotonic() < deadline:
            if not self.worker_alive:
                return False
            if self.q.unfinished_tasks == 0 and not self.speaking.is_set():
                return True
            time.sleep(.02)
        return False

    def close(self):
        self.stop_event.set()
        while True:
            try:
                self.q.get_nowait()
                self.q.task_done()
            except queue.Empty:
                break
        try:
            self.q.put_nowait(None)
        except Exception:
            pass
        if self.thread and self.thread.is_alive():
            try:
                self.thread.join(timeout=1.0)
            except Exception:
                pass
        self.ready = False
