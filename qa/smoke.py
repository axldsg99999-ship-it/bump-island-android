import subprocess,time,xml.etree.ElementTree as ET,re,json,os
import uiautomator2 as u2
from pathlib import Path
out=Path('qa-results');out.mkdir(exist_ok=True)
device=u2.connect()
def adb(*args,raw=False):
    return subprocess.check_output(['adb',*map(str,args)],text=not raw,timeout=30)
def dump(name):
    xml=device.dump_hierarchy();(out/(name+'.xml')).write_text(xml,encoding='utf-8')
    time.sleep(.8) # Let the WebView paint after the accessibility update.
    (out/(name+'.png')).write_bytes(adb('exec-out','screencap','-p',raw=True))
    return ET.fromstring(xml)
def click_text(text,tree,scrolls=0):
    for n in tree.iter('node'):
        if text in (n.attrib.get('text','')+' '+n.attrib.get('content-desc','')):
            box=list(map(int,re.findall(r'\d+',n.attrib['bounds'])));x=(box[0]+box[2])//2;y=(box[1]+box[3])//2
            width,height=device.window_size()
            if not (0<x<width and 0<y<height):
                assert scrolls<6,'Cannot scroll to '+text
                device.swipe(width*.5,height*.78,width*.5,height*.35,duration=.35);time.sleep(.4)
                return click_text(text,ET.fromstring(device.dump_hierarchy()),scrolls+1)
            print(f'Tap {text}: {x},{y}',flush=True)
            # Give WebView a real contact interval. Zero-duration emulator
            # injection can lose the first tap after a cold launch.
            device.touch.down(x,y);time.sleep(.12);device.touch.up(x,y);return True
    return False
def wait_text(text,name,seconds=45):
    start=time.time()
    while time.time()-start<seconds:
        tree=dump(name)
        # Fresh emulators show Android's first fullscreen explanation. Only
        # dismiss known system overlays; never hide a game crash/ANR.
        nodes=list(tree.iter('node'))
        if any('正在靠岸' in n.attrib.get('text','') for n in nodes):
            time.sleep(2);continue
        if any(n.attrib.get('resource-id')=='android:id/immersive_cling_title' for n in nodes):
            assert click_text('Got it',tree);time.sleep(2);continue
        if any("Pixel Launcher isn't responding" in n.attrib.get('text','') for n in nodes):
            assert click_text('Close app',tree);time.sleep(2);continue
        # Android's activity entrance scales the accessibility coordinates.
        # Wait for the full-size WebView before using bounds to inject input.
        webviews=[n for n in nodes if n.attrib.get('text')=='碰碰岛 · BUMP ISLAND']
        if webviews and webviews[0].attrib.get('bounds')!='[0,0][720,1560]':
            time.sleep(1);continue
        if any(text in (n.attrib.get('text','')+' '+n.attrib.get('content-desc','')) for n in tree.iter('node')):
            print('Verified UI: '+name,flush=True);return tree
        time.sleep(3)
    raise AssertionError('UI text not found: '+text)
print(adb('install','-r','bump-island-8.8.0.apk'),flush=True)
adb('shell','am','start','-W','-n','com.bumpisland.game/.MainActivity')
tree=wait_text('开始闯关','00-old-home');assert click_text('开始闯关',tree)
tree=wait_text('出发，第一碰','00-old-guide');assert click_text('出发，第一碰',tree)
wait_text('施展','00-old-battle')
adb('shell','am','force-stop','com.bumpisland.game')
print(adb('install','-r',os.environ.get('ISLAND_APK','bump-island-8.9.0.apk')),flush=True)
adb('shell','svc','wifi','disable');adb('shell','svc','data','disable')
print(adb('shell','am','start','-W','-n','com.bumpisland.game/.MainActivity'),flush=True)
tree=wait_text('开始闯关','01-home')
assert click_text('调整阵容',tree)
tree=wait_text('烈焰冲刺','10-crew')
for key,name,skill in [('fox','阿焰','烈焰冲刺'),('turtle','岩岩','磐石护甲'),('rabbit','露娜','月光治愈'),('robot','波波','惊雷震荡'),('penguin','小蓝','冰霜冲击'),('bear','布鲁','巨力一击')]:
    assert click_text('查看'+name,tree)
    tree=wait_text(skill,'30-character-'+key)
assert click_text('查看小蓝',tree)
tree=wait_text('冰霜冲击','11-penguin')
# Authored sixteen-frame ink animation preview.
assert click_text('试招',tree)
time.sleep(1);tree=dump('12-motion')
assert click_text('替换 阿焰',tree)
tree=wait_text('阵容已调整','13-assigned')
assert click_text('完成编队',tree)
tree=wait_text('开始闯关','14-new-team')
adb('shell','am','force-stop','com.bumpisland.game');adb('shell','am','start','-W','-n','com.bumpisland.game/.MainActivity')
tree=wait_text('查看小蓝','15-persisted-team')
assert click_text('调整阵容',tree)
tree=wait_text('选择伙伴','16-crew-again')
assert click_text('查看阿焰',tree)
tree=wait_text('烈焰冲刺','17-fox')
assert click_text('替换 小蓝',tree)
tree=wait_text('阵容已调整','18-restored')
assert click_text('完成编队',tree)
tree=wait_text('开始闯关','19-ready')
assert click_text('开始闯关',tree)
tree=wait_text('施展','03-battle')
assert not any('出发，第一碰' in n.attrib.get('text','') for n in tree.iter('node')), 'Upgrade lost tutorial progress'
assert click_text('施展',tree)
errors=[]
try:tree=wait_text('已蓄势','04-skill',seconds=25)
except AssertionError as e:errors.append(str(e))
# Drag the first blue hero upward in arena coordinates, then inspect next-turn evidence.
device.swipe(164,1050,154,1240,duration=.45)
time.sleep(2)
try:tree=wait_text('3 回合','05-after-shot',seconds=25)
except AssertionError as e:errors.append(str(e))
adb('shell','input','keyevent','4');tree=wait_text('继续冒险','06-back-pauses')
assert click_text('继续冒险',tree)
adb('shell','input','keyevent','3');time.sleep(2);adb('shell','am','start','-W','-n','com.bumpisland.game/.MainActivity');tree=wait_text('继续冒险','07-background-pauses')
assert click_text('返回岛屿',tree)
wait_text('开始闯关','08-home-again')
adb('shell','am','force-stop','com.bumpisland.game');adb('shell','am','start','-W','-n','com.bumpisland.game/.MainActivity');wait_text('开始闯关','09-cold-restart')
tree=wait_text('开始闯关','20-before-bestiary')
assert click_text('异兽录',tree)
tree=wait_text('墨跳','21-bestiary-offline')
assert click_text('关闭',tree)
tree=wait_text('开始闯关','22-after-bestiary')
assert click_text('背景音乐',tree)
tree=wait_text('背景音乐','23-music-disabled')
adb('shell','am','force-stop','com.bumpisland.game');adb('shell','am','start','-W','-n','com.bumpisland.game/.MainActivity')
tree=wait_text('背景音乐','24-music-persisted')
time.sleep(17)
disabled_log=adb('logcat','-d','-s','IslandAudio:I')
disabled_pid=adb('shell','pidof','com.bumpisland.game').strip()
disabled_states=[]
for line in disabled_log.splitlines():
    if 'IslandAudio:' not in line or not re.search(r'\s'+disabled_pid+r'\s',line):continue
    state=json.loads(line.split('IslandAudio:',1)[1].strip())
    if isinstance(state,str):state=json.loads(state)
    if isinstance(state,dict):disabled_states.append(state)
assert disabled_states and disabled_states[-1]['enabled'] is False and disabled_states[-1]['playing'] is False,disabled_states
(out/'music-disabled.json').write_text(json.dumps(disabled_states[-1],indent=2))
assert click_text('背景音乐',tree)
tree=wait_text('背景音乐','25-music-enabled')
assert click_text('设置',tree)
tree=wait_text('背景音乐','26-audio-settings')
assert click_text('关闭',tree)
wait_text('开始闯关','27-finished')
# Decoder evidence from the same signed APK, while offline. This is not a speaker test.
adb('shell','am','force-stop','com.bumpisland.game');adb('shell','am','start','-W','-n','com.bumpisland.game/.MainActivity')
wait_text('开始闯关','28-final-music')
time.sleep(17)
audio_log=adb('logcat','-d','-s','IslandAudio:I')
(out/'audio.txt').write_text(audio_log,encoding='utf-8')
audio_states=[]
current_pid=adb('shell','pidof','com.bumpisland.game').strip()
for line in audio_log.splitlines():
    if 'IslandAudio:' not in line or not re.search(r'\s'+current_pid+r'\s',line):continue
    try:
        state=json.loads(line.split('IslandAudio:',1)[1].strip())
        if isinstance(state,str):state=json.loads(state)
        if isinstance(state,dict):audio_states.append(state)
    except (ValueError,TypeError):pass
assert any(s.get('playing') and s.get('time',0)>0 and s.get('peak',0)>0 for s in audio_states),audio_log
logs=adb('logcat','-d');assert 'FATAL EXCEPTION' not in '\n'.join(l for l in logs.splitlines() if 'com.bumpisland' in l or 'FATAL EXCEPTION' in l)
# Clear only the disposable emulator app data to exercise the current first run.
adb('shell','pm','clear','com.bumpisland.game')
adb('shell','am','start','-W','-n','com.bumpisland.game/.MainActivity')
tree=wait_text('开始闯关','40-fresh-home');assert click_text('开始闯关',tree)
tree=wait_text('出发，第一碰','41-fresh-guide')
buttons=[n for n in tree.iter('node') if '出发，第一碰' in (n.attrib.get('text','')+' '+n.attrib.get('content-desc',''))]
assert buttons
box=list(map(int,re.findall(r'\d+',buttons[0].attrib['bounds'])));assert 0<=box[1]<box[3]<=1560,box
assert click_text('出发，第一碰',tree)
wait_text('施展','42-fresh-battle')
(out/'result.json').write_text(json.dumps({'ok':not errors,'errors':errors,'android':adb('shell','getprop','ro.build.version.release').strip(),'offline':True,'installation':True,'home':True,'battle':True,'skill':not errors,'backButton':True,'coldRestart':True,'crewReplacement':True,'crewPersistence':True,'inkCharacterPreview':True,'motionDemo':True,'bestiaryOffline':True,'musicTogglePersistence':True,'physicalAudioListening':False,'audioDecoderSignal':True,'firstRunGuideVisible':True,'upgradedFrom':'8.8.0','version':'8.9.0'},indent=2))
assert not errors,errors
print('Android installation and offline smoke passed',flush=True)
