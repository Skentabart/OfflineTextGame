# -*- coding: utf-8 -*-
import time


class SpeechRecognizer:
    def __init__(self, model_name='small', device='cpu', compute_type='int8',
                 cpu_threads=8, rate=16000, max_seconds=6.0, silence_seconds=.65):
        self.model_name = model_name
        self.device = 'cpu'  # Whisper is forced to CPU.
        self.compute_type = compute_type
        self.cpu_threads = cpu_threads
        self.rate = rate
        self.max_seconds = max_seconds
        self.silence_seconds = silence_seconds
        self.pre_record_delay = 0.35
        self.min_speech_seconds = 0.22
        self.model = None

    def load(self):
        from faster_whisper import WhisperModel
        self.model = WhisperModel(
            self.model_name,
            device='cpu',
            compute_type=self.compute_type,
            cpu_threads=self.cpu_threads,
            num_workers=1,
        )
        return True

    def listen(self, printer=print):
        if self.model is None:
            return None

        try:
            import numpy as np
            import sounddevice as sd
        except Exception as exc:
            printer('Ошибка аудио: ' + str(exc))
            return None

        chunks = []
        started_at = time.monotonic()
        speech_started = False
        silence_started = None
        threshold = 0.012
        block = 1600

        # Даём динамику микрофона стабилизироваться после TTS.
        time.sleep(self.pre_record_delay)
        printer('Говорите...')

        def callback(indata, frames, time_info, status):
            nonlocal speech_started, silence_started
            data = indata[:, 0].copy()
            chunks.append(data)
            rms = float(np.sqrt(np.mean(data * data) + 1e-12))
            now = time.monotonic()
            if rms > threshold:
                speech_started = True
                silence_started = None
            elif speech_started and silence_started is None:
                silence_started = now

        try:
            with sd.InputStream(
                samplerate=self.rate,
                channels=1,
                dtype='float32',
                blocksize=block,
                callback=callback,
            ):
                while time.monotonic() - started_at < self.max_seconds:
                    time.sleep(.05)
                    if (
                        speech_started
                        and silence_started is not None
                        and time.monotonic() - silence_started >= self.silence_seconds
                    ):
                        break
        except KeyboardInterrupt:
            return '__INTERRUPT__'
        except Exception as exc:
            printer('Ошибка микрофона: ' + str(exc))
            return None

        if not chunks or not speech_started:
            printer('Речь не распознана.')
            return None

        if time.monotonic() - started_at < self.min_speech_seconds:
            printer('Речь не распознана.')
            return None

        audio = np.concatenate(chunks)

        try:
            segments, _ = self.model.transcribe(
                audio,
                language='ru',
                task='transcribe',
                beam_size=1,
                best_of=1,
                temperature=0,
                vad_filter=True,
                vad_parameters={'min_silence_duration_ms': 220},
                condition_on_previous_text=False,
                without_timestamps=True,
            )

            # Не используем generator-expression: проверяем каждую
            # итерацию отдельно и корректно обрабатываем Ctrl+C.
            parts = []
            try:
                for segment in segments:
                    value = (segment.text or '').strip()
                    if value:
                        parts.append(value)
            except KeyboardInterrupt:
                return '__INTERRUPT__'

            text = ' '.join(parts).strip()

            if not text:
                printer('Речь не распознана.')
                return None

            printer('Распознано: ' + text)
            return text

        except KeyboardInterrupt:
            return '__INTERRUPT__'
        except Exception as exc:
            printer('Ошибка Whisper: ' + str(exc))
            return None
