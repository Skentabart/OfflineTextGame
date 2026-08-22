# -*- coding: utf-8 -*-
import json
import re
import threading
import requests


class QwenClient:
    def __init__(self, base_url, model, default_max_tokens=120, request_timeout=20):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.default_max_tokens = default_max_tokens
        self.request_timeout = request_timeout
        self.lock = threading.Lock()

    def health(self):
        try:
            r = requests.get(f'{self.base_url}/health', timeout=3)
            return r.status_code in (200, 204)
        except requests.RequestException:
            return False

    def discover_model(self):
        r = requests.get(f'{self.base_url}/v1/models', timeout=5)
        r.raise_for_status()
        models = r.json().get('data', [])
        if models:
            self.model = models[0].get('id', self.model)
        return self.model

    @staticmethod
    def clean(text):
        if not text:
            return ''
        text = re.sub(r'<think>.*?</think>', '', str(text), flags=re.S | re.I)
        text = text.replace('```json', '').replace('```', '')
        return re.sub(r'\s+', ' ', text).strip()

    @staticmethod
    def extract(data):
        choices = data.get('choices') or []
        if not choices:
            return ''
        msg = choices[0].get('message') or {}
        return msg.get('content') or ''

    def chat(self, system, user, max_tokens=None, temperature=0.25, response_format=None, timeout=None):
        payload = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': system + '\n/no_think'},
                {'role': 'user', 'content': user}
            ],
            'max_tokens': max_tokens or self.default_max_tokens,
            'temperature': temperature,
            'top_p': 0.8,
            'top_k': 20,
            'repeat_penalty': 1.08,
            'stream': False,
            'chat_template_kwargs': {'enable_thinking': False}
        }
        if response_format is not None:
            payload['response_format'] = response_format

        wait = timeout or self.request_timeout
        with self.lock:
            try:
                r = requests.post(
                    f'{self.base_url}/v1/chat/completions',
                    json=payload,
                    timeout=wait
                )
                r.raise_for_status()
                return self.clean(self.extract(r.json()))
            except requests.RequestException as exc:
                # Structured output is optional. Retry once without it.
                if response_format is not None:
                    try:
                        payload.pop('response_format', None)
                        r = requests.post(
                            f'{self.base_url}/v1/chat/completions',
                            json=payload,
                            timeout=min(wait, 12)
                        )
                        r.raise_for_status()
                        return self.clean(self.extract(r.json()))
                    except requests.RequestException:
                        return ''
                return ''
            except Exception:
                return ''

    @staticmethod
    def parse_json(text):
        if not text:
            return None
        text = str(text).strip()
        try:
            return json.loads(text)
        except Exception:
            pass
        a = text.find('{')
        b = text.rfind('}')
        if a >= 0 and b > a:
            fragment = text[a:b + 1]
            try:
                return json.loads(fragment)
            except Exception:
                # Repair common trailing comma errors.
                fragment = re.sub(r',\s*([}\]])', r'\1', fragment)
                try:
                    return json.loads(fragment)
                except Exception:
                    return None
        return None
