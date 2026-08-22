# -*- coding: utf-8 -*-
import json, os, subprocess, signal, time, re, difflib
from pathlib import Path
from engine.game import GameEngine
from ai import QwenClient, RoomGenerator, InteractionAI, Narrator, EnemyGenerator, EventGenerator, ActionInterpreter
from voice import SpeechRecognizer, SpeechSynthesizer

BASE=Path(__file__).resolve().parent
CFG=json.loads((BASE/'config.json').read_text(encoding='utf-8'))

def detect_nvidia():
    try:
        r=subprocess.run(['nvidia-smi','--query-gpu=name','--format=csv,noheader'],capture_output=True,text=True,timeout=5,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        if r.returncode==0 and r.stdout.strip():return r.stdout.strip().splitlines()[0].strip()
    except Exception:pass
    return None

def choose_mode():
    gpu=detect_nvidia(); print('1. GPU\n2. CPU\n3. AUTO\n')
    if gpu:print('Обнаружена NVIDIA:',gpu)
    while True:
        c=input('Выберите режим [1]: ').strip() or '1'
        if c=='1':return ('gpu',gpu or 'не определена')
        if c=='2':return ('cpu',gpu or 'не определена')
        if c=='3':return ('gpu',gpu) if gpu else ('cpu','не определена')

def start_server(mode):
    exe=BASE/CFG['llama_server']; model=BASE/CFG['model']; ngl='999' if mode=='gpu' else '0'
    cmd=[str(exe),'-m',str(model),'-c',str(CFG['context']),'-t',str(CFG['cpu_threads']),'-ngl',ngl,'--jinja','--reasoning-budget','0','--host',CFG['server_host'],'--port',str(CFG['server_port'])]
    print('\nЗапуск llama-server:\n'+' '.join(f'"{x}"' if ' ' in x else x for x in cmd)+'\n')
    flags=subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    return subprocess.Popen(cmd,cwd=str(BASE),stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=flags)

def wait_server(proc,url):
    print('Ожидание загрузки Qwen...'); start=time.time()
    while time.time()-start<60:
        if proc.poll() is not None:raise RuntimeError(f'llama-server exited {proc.returncode}')
        try:
            r=__import__('requests').get(url+'/health',timeout=2)
            if r.status_code in (200,204):print('llama-server отвечает.');return
        except Exception:pass
        time.sleep(.4)
    raise TimeoutError('Qwen не запустилась.')

def stop(proc):
    if not proc:return
    try:
        if proc.poll() is None:
            proc.terminate(); proc.wait(timeout=3)
    except Exception:
        try:proc.kill()
        except Exception:pass

def _normalize_echo(text):
    t = str(text or '').lower().replace('ё', 'е')
    t = re.sub(r"[^а-яa-z0-9 ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _echo_tokens(text):
    stop = {
        'ты','вы','и','а','в','во','на','по','к','с','со','из','за','для',
        'это','эта','этот','этой','тебе','тебя','твой','твоя','твое','твои',
        'же','уже','очень','просто','здесь','там','вот','как','что','то'
    }
    return {x for x in _normalize_echo(text).split() if len(x) >= 3 and x not in stop}


def _similar_echo(text, spoken_history):
    if not text or not spoken_history:
        return False
    a = _normalize_echo(text)
    if len(a) < 4:
        return True
    at = _echo_tokens(a)
    for spoken in spoken_history[-8:]:
        b = _normalize_echo(spoken)
        if not b:
            continue
        if a in b or b in a:
            return True
        bt = _echo_tokens(b)
        if at and bt:
            overlap = len(at & bt) / max(1, min(len(at), len(bt)))
            if overlap >= 0.50 and len(at) >= 3:
                return True
        ratio = difflib.SequenceMatcher(None, a, b).ratio()
        if ratio >= 0.58:
            return True
    return False


def _looks_like_narration(text, spoken_history):
    t = _normalize_echo(text)
    if not t or len(t) < 3:
        return True
    markers = (
        'рассказчик','ты берешь','ты берёшь','ты направляешься','ты вставляешь',
        'ты оказываешься','ты подходишь','ты проходишь','замок щелкает','замок щёлкает',
        'дверь открывается','дверь открыта','воздух холодный','воздух влажный',
        'в помещении находится','в помещении находятся','здесь можно увидеть',
        'выходы север','выходы юг','выходы восток','выходы запад',
        'неизведанная область','заброшенная зона','подземный переход',
        'старая служебная комната','старая диспетчерская','игрок',
        'наносит урон','атакует тебя','получаешь','получил урон'
    )
    if any(m in t for m in markers):
        return True
    # Фраза из нескольких предложений почти всегда является эхом/описанием.
    if t.count(' ') >= 10 and _similar_echo(t, spoken_history):
        return True
    return False


def _looks_like_garbage_command(text):
    t=_normalize_echo(text)
    if not t:
        return True
    words=t.split()
    # Не отправляем в Qwen длинный обрывок описания комнаты.
    if len(words) >= 8 and not any(w in t for w in ('идти','пойти','взять','открыть','осмотреть','использовать','атаковать','бежать','убежать','спрятаться','сохранить','загрузить','инвентарь','помощь')):
        return True
    return False

def main():
    mode,gpu=choose_mode(); print('\nCONFIG\n'); print('Режим:',mode.upper()); print('GPU:',gpu); print('Model:',CFG['model']); print('Context:',CFG['context']); print('CPU threads:',CFG['cpu_threads'])
    proc=None;tts=None
    try:
        proc=start_server(mode);url=f"http://{CFG['server_host']}:{CFG['server_port']}";wait_server(proc,url)
        qwen=QwenClient(url,Path(CFG['model']).name,120);print('Проверка Qwen API...');qwen.discover_model();print('Qwen API готова.');print('AI готова.')
        tts=SpeechSynthesizer();tts.load();print('Голосовые ответы готовы.')
        print('\nЗагрузка локального Whisper...');stt=SpeechRecognizer(CFG['whisper_model'],CFG['whisper_device'],CFG['whisper_compute'],CFG['cpu_threads'],CFG['audio_rate'],CFG['audio_max_seconds'],CFG['audio_silence_seconds']);stt.load();print('Whisper теперь работает на CPU.')
        game=GameEngine(CFG,qwen,RoomGenerator(),InteractionAI(),Narrator())
        print('\n'+'='*52);print('OFFLINE GAME AI V30');print('='*52);print('\nQwen загружена.\nWhisper: CPU / int8\nГолосовые ответы готовы.\nМодульный игровой движок готов.\nДинамические события готовы.\nБоевая система готова.\nСистема угроз и ловушек готова.\n')
        print('Ты приходишь в себя на полу заброшенной станции.')
        print('За разбитыми окнами льётся холодный дождь.')
        print(game.describe_current())
        voice=False
        spoken_history=[]
        echo_cooldown_until=0.0
        while True:
            if voice:
                try:
                    if tts:
                        tts.wait(timeout=10)
                    # Небольшая защита от хвоста акустического эха.
                    remaining = echo_cooldown_until - time.monotonic()
                    if remaining > 0:
                        time.sleep(min(remaining, 2.5))
                    text=stt.listen(print)
                except KeyboardInterrupt:
                    print('Остановка по запросу пользователя.');break
                if text=='__INTERRUPT__':print('Остановка по запросу пользователя.');break
                if not text:continue
                if _similar_echo(text,spoken_history) or _looks_like_narration(text,spoken_history) or _looks_like_garbage_command(text):
                    print('Речь не распознана.')
                    continue
                n=text.lower().strip().replace('ё','е')
                if n in ('выйти','вернуться','текстовый режим','выключить голос'):
                    voice=False;print('Голосовой режим выключен.');continue
            else:
                text=input('\n>>> ').strip()
                if text=='/exit':break
                if text=='/voice':voice=True;print('\nГОЛОСОВОЙ РЕЖИМ\nГоворите команды естественным языком.\n');continue
                if text=='/inventory':print(game.inventory.text());continue
                if text=='/map':print(game.describe_current());continue
                if text=='/status':print('Здоровье:',game.world.data['health']);print('Координаты:',game.world.location);print('Шум:',game.world.data.get('noise',0));print('Угрозы:',game.threats.status());continue
                if text=='/memory':print('\n'.join(game.memory.recent()));continue
                if text.startswith('/save'):
                    from engine.save import save
                    slot=text.split(maxsplit=1)[1] if len(text.split(maxsplit=1))>1 else '1';save(game.world.to_dict(),BASE/'saves'/f'save_{slot}.json');print('Сохранено.');continue
                if text.startswith('/load'):
                    from engine.save import load
                    slot=text.split(maxsplit=1)[1] if len(text.split(maxsplit=1))>1 else '1';game.world.from_dict(load(BASE/'saves'/f'save_{slot}.json'));print('Загружено.');continue
            try:result=game.command(text)
            except KeyboardInterrupt:print('\nОстановка по запросу пользователя.');break
            except Exception as exc:result='Не удалось выполнить действие: '+str(exc)
            if result=='__EXIT__':break
            print('\nРассказчик:\n'+result)
            if voice:
                spoken_history.append(result)
                spoken_history=spoken_history[-8:]
                # После начала TTS запрещаем микрофону реагировать на хвост озвучки.
                echo_cooldown_until=time.monotonic()+0.9
                if tts: tts.speak(result,wait=True)
        print('\nВыход из игры...')
    finally:
        if tts:
            try:tts.close()
            except Exception:pass
        stop(proc);print('\nИгра завершена.')

if __name__=='__main__':main()
