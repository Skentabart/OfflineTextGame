# -*- coding: utf-8 -*-
import re
class Narrator:
    def clean(self,text):
        if not text:return ''
        text = re.sub(r'<think>.*?</think>','',str(text),flags=re.S|re.I)
        text = re.sub(r'[\u2600-\u27BF\U0001F300-\U0001FAFF]', '', text)
        text = text.replace('▌','')
        text = re.sub(r'^(Ответ|Результат|Рассказчик)\s*:\s*','',text,flags=re.I)
        return text.strip()
