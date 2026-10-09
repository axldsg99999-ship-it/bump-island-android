import subprocess,time,xml.etree.ElementTree as ET,re,json,os
import uiautomator2 as u2
from pathlib import Path
out=Path('qa-results');out.mkdir(exist_ok=True)
device=u2.connect()
def adb(*args,raw=False):
    return subprocess.check_output(['adb',*map(str,args)],text=not raw,timeout=30)
def dump(name):
    xml=device.dump_hierarchy();(out/(name+'.xml')).write_text(xml,encoding='utf-8')
    (out/(name+'.png')).write_bytes(adb('exec-out','screencap','-p',raw=True))
    return ET.fromstring(xml)
def click_text(text,tree):
    for n in tree.iter('node'):
        if text in (n.attrib.get('text','')+' '+n.attrib.get('content-desc','')):
            box=list(map(int,re.findall(r'\d+',n.attrib['bounds'])));device.click((box[0]+box[2])//2,(box[1]+box[3])//2);return True
    return False
def wait_text(text,name,seconds=45):
    start=time.time()
    while time.time()-start<seconds:
        tree=dump(name)
        # Fresh emulators show Android's first fullscreen explanation. Only
        # dismiss known system overlays; never hide a game crash/ANR.
        nodes=list(tree.iter('node'))
        if any(n.attrib.get('resource-id')=='android:id/immersive_cling_title' for n in nodes):
            assert click_text('Got it',tree);time.sleep(2);continue
        if any("Pixel Launcher isn't responding" in n.attrib.get('text','') for n in nodes):
            assert click_text('Close app',tree);time.sleep(2);continue
        if any(text in (n.attrib.get('text','')+' '+n.attrib.get('content-desc','')) for n in tree.iter('node')):
            print('Verified UI: '+name,flush=True);return tree
        time.sleep(3)
    raise AssertionError('UI text not found: '+text)
print(adb('install','-r',os.environ.get('ISLAND_APK','bump-island-2.0.0.apk')),flush=True)
adb('shell','svc','wifi','disable');adb('shell','svc','data','disable')
print(adb('shell','am','start','-W','-n','com.bumpisland.game/.MainActivity'),flush=True)
tree=wait_text('开始冒险','01-home')
assert click_text('开始冒险',tree)
tree=wait_text('出发，第一碰','02-guide');assert click_text('出发，第一碰',tree)
tree=wait_text('激活技能','03-battle')
assert click_text('激活技能',tree)
errors=[]
try:tree=wait_text('已激活','04-skill',seconds=15)
except AssertionError as e:errors.append(str(e))
# Drag the first blue hero upward in arena coordinates, then inspect next-turn evidence.
device.swipe(200,913,207,1100,duration=.55)
try:tree=wait_text('回合冷却','05-after-shot',seconds=15)
except AssertionError as e:errors.append(str(e))
adb('shell','input','keyevent','4');tree=wait_text('继续冒险','06-back-pauses')
assert click_text('继续冒险',tree)
adb('shell','input','keyevent','3');time.sleep(2);adb('shell','am','start','-W','-n','com.bumpisland.game/.MainActivity');tree=wait_text('继续冒险','07-background-pauses')
assert click_text('返回岛屿',tree)
wait_text('开始冒险','08-home-again')
adb('shell','am','force-stop','com.bumpisland.game');adb('shell','am','start','-W','-n','com.bumpisland.game/.MainActivity');wait_text('开始冒险','09-cold-restart')
logs=adb('logcat','-d');assert 'FATAL EXCEPTION' not in '\n'.join(l for l in logs.splitlines() if 'com.bumpisland' in l or 'FATAL EXCEPTION' in l)
(out/'result.json').write_text(json.dumps({'ok':not errors,'errors':errors,'android':adb('shell','getprop','ro.build.version.release').strip(),'offline':True,'installation':True,'home':True,'battle':True,'skill':not errors,'backButton':True,'coldRestart':True},indent=2))
assert not errors,errors
print('Android installation and offline smoke passed',flush=True)
