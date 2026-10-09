import subprocess,time,xml.etree.ElementTree as ET,re,json
from pathlib import Path
out=Path('qa-results');out.mkdir(exist_ok=True)
def adb(*args,raw=False):
    return subprocess.check_output(['adb',*map(str,args)],text=not raw)
def dump(name):
    adb('shell','uiautomator','dump','/sdcard/window.xml')
    xml=adb('shell','cat','/sdcard/window.xml');(out/(name+'.xml')).write_text(xml,encoding='utf-8')
    (out/(name+'.png')).write_bytes(adb('exec-out','screencap','-p',raw=True))
    return ET.fromstring(xml)
def click_text(text,tree):
    for n in tree.iter('node'):
        if text in (n.attrib.get('text','')+' '+n.attrib.get('content-desc','')):
            box=list(map(int,re.findall(r'\d+',n.attrib['bounds'])));adb('shell','input','tap',(box[0]+box[2])//2,(box[1]+box[3])//2);return True
    return False
def wait_text(text,name,seconds=45):
    start=time.time()
    while time.time()-start<seconds:
        tree=dump(name)
        if any(text in (n.attrib.get('text','')+' '+n.attrib.get('content-desc','')) for n in tree.iter('node')):return tree
        time.sleep(3)
    raise AssertionError('UI text not found: '+text)
print(adb('install','-r','bump-island-2.0.0.apk'),flush=True)
adb('shell','svc','wifi','disable');adb('shell','svc','data','disable')
print(adb('shell','am','start','-W','-n','com.bumpisland.game/.MainActivity'),flush=True)
tree=wait_text('开始冒险','01-home')
assert click_text('开始冒险',tree)
time.sleep(3);tree=dump('02-guide');click_text('出发',tree)
tree=wait_text('激活技能','03-battle')
assert click_text('激活技能',tree)
time.sleep(1);tree=dump('04-skill');assert any('已激活' in n.attrib.get('text','') for n in tree.iter('node'))
# Drag the first blue hero upward in arena coordinates, then inspect next-turn evidence.
adb('shell','input','swipe','300','1370','310','1650','550');time.sleep(10)
tree=dump('05-after-shot')
adb('shell','input','keyevent','4');tree=wait_text('继续冒险','06-back-pauses')
adb('shell','input','keyevent','3');time.sleep(2);adb('shell','am','start','-W','-n','com.bumpisland.game/.MainActivity');tree=wait_text('继续冒险','07-background-pauses')
assert click_text('返回岛屿',tree)
wait_text('开始冒险','08-home-again')
adb('shell','am','force-stop','com.bumpisland.game');adb('shell','am','start','-W','-n','com.bumpisland.game/.MainActivity');wait_text('开始冒险','09-cold-restart')
logs=adb('logcat','-d');assert 'FATAL EXCEPTION' not in '\n'.join(l for l in logs.splitlines() if 'com.bumpisland' in l or 'FATAL EXCEPTION' in l)
(out/'result.json').write_text(json.dumps({'ok':True,'android':adb('shell','getprop','ro.build.version.release').strip(),'offline':True,'installation':True,'home':True,'battle':True,'skill':True,'backButton':True,'coldRestart':True},indent=2))
print('Android installation and offline smoke passed',flush=True)
