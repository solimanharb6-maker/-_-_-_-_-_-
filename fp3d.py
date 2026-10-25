# -*- coding: utf-8 -*-
"""
fp3d.py - وضع 3D بمنظور الشخص الأول (Raycasting) للعبة "بيت الهمس".

الفكرة: نفس الخريطة (lv.grid) ونفس الأوبجكتس ونفس منطق اللعبة،
بس الرسم بيتحول من منظور علوي لمنظور اللاعب نفسه.

التحكم (كمبيوتر):  W/S قدّام/ورا  -  A/D يمين/شمال (جنب)  -  ← → أو الماوس: لف
                    V: تبديل بين 3D و 2D
التحكم (موبايل):   الجويستيك: فوق/تحت = حركة ، يمين/شمال = لف
"""
import math
import random

import pygame

G = {}            # دوال وثوابت من main.py (بتتحط بـ bind)
NL = 16           # عدد درجات الإضاءة
TW = TH = 64      # حجم تكستشر الحيطة
FOV_PLANE = 0.66  # طول الـ camera plane (حوالي 66 درجة)
K = 1.5           # معامل ارتفاع الحيطة على الشاشة
TURN_SPEED = 2.3  # راديان/ثانية بالأسهم
MOUSE_SENS = 0.0026   # حساسية الماوس الأساسية
SENS = 1.0            # مُعامل تحكم اللاعب ( [ و ] بيغيّروه ) وبيتحفظ في settings.json
MAX_MOUSE_STEP = 45   # أقصى حركة ماوس في الفريم الواحد (بيمنع القفزات)

import time
SHOW_PROF = False     # F3 بيظهر FPS وتوزيع الوقت
_state = {'tex': None, 'bg': {}, 'sprites': {}, 'grab': False, 'warm': 0,
          'colw': 4, 'ema': 0.016, 'last': 0.0, 'cnt': 0, 'prof': {}, 'cone': None}


ENV = {}


def bind(env):
    """بياخد globals() بتاعة main.py علشان نستخدم draw_text و glow وغيرهم من غير import دائري"""
    global ENV
    ENV = env                     # نسخة حيّة (MASTER بيتغيّر وإحنا شغالين)
    G.update(env)


# ------------------------------------------------------------------ تكستشر (6 أنماط + ديكورات)
STYLE_KEYS = [
    (('حمّام', 'حمام', 'مطبخ', 'غسيل'), 2),
    (('نوم', 'أطفال', 'ضيوف', 'أجداد', 'مرضى', 'المرضى'), 1),
    (('مكتب', 'مكتبة', 'كتب', 'سفرة', 'أنتريه', 'موسيقى', 'خياطة', 'مرسم', 'ساعة'), 3),
    (('بدروم', 'قبو', 'مخزن', 'مخبأ', 'علّية', 'العلية', 'خشب'), 4),
    (('مراية', 'الضوء', 'دُمى', 'دمى', 'ألعاب', 'صلاة', 'نجف'), 5),
]
_TEX_CACHE = {}


def _style_for(name, idx):
    nm = str(name)
    for keys, st in STYLE_KEYS:
        for k in keys:
            if k in nm:
                return st
    return (0, 5, 1, 3)[idx % 4]


def _noise(surf, rng, n, lo, hi):
    for _ in range(n):
        x, y = rng.randrange(TW), rng.randrange(TH)
        v = rng.randint(lo, hi)
        c = surf.get_at((x, y))
        surf.set_at((x, y), (max(0, min(255, c[0] + v)), max(0, min(255, c[1] + v)), max(0, min(255, c[2] + v))))


def _base(style):
    rng = random.Random(100 + style)
    b = pygame.Surface((TW, TH))
    if style == 1:                                              # أوض النوم: ورق ورد باهت
        b.fill((92, 62, 68))
        for x in range(0, TW, 10):
            pygame.draw.rect(b, (82, 53, 59), (x, 0, 5, TH))
        for y in range(6, TH - 12, 12):
            for x in range(5, TW, 10):
                pygame.draw.circle(b, (122, 88, 94), (x, y), 1)
        _noise(b, rng, 200, -10, 8)
        pygame.draw.rect(b, (70, 48, 48), (0, TH - 9, TW, 9))
        pygame.draw.rect(b, (112, 82, 84), (0, 0, TW, 3))
    elif style == 2:                                            # حمّام ومطبخ: سيراميك
        b.fill((128, 142, 132))
        for k in range(0, TW, 16):
            pygame.draw.line(b, (82, 94, 88), (k, 0), (k, TH))
            pygame.draw.line(b, (82, 94, 88), (0, k), (TW, k))
        for _ in range(7):
            x, y = rng.randrange(0, TW, 16), rng.randrange(0, TH, 16)
            pygame.draw.rect(b, (112, 126, 116), (x + 1, y + 1, 15, 15))
        for _ in range(5):
            pygame.draw.circle(b, (64, 70, 56), (rng.randrange(TW), rng.randrange(TH)), rng.randint(2, 5))
        _noise(b, rng, 160, -12, 8)
        pygame.draw.rect(b, (60, 70, 66), (0, TH - 5, TW, 5))
    elif style == 3:                                            # مكاتب ومكتبات: خشب
        b.fill((92, 62, 36))
        for x in range(0, TW, 8):
            pygame.draw.line(b, (56, 36, 20), (x, 0), (x, TH))
            for _ in range(3):
                gx = x + rng.randint(2, 6)
                gy = rng.randrange(TH)
                pygame.draw.line(b, (78, 52, 30), (gx, gy), (gx, gy + rng.randint(6, 18)))
        _noise(b, rng, 140, -10, 8)
        pygame.draw.rect(b, (66, 44, 26), (0, TH - 9, TW, 9))
        pygame.draw.rect(b, (112, 80, 46), (0, 0, TW, 4))
    elif style == 4:                                            # بدروم ومخازن: خرسانة
        b.fill((98, 100, 100))
        _noise(b, rng, 420, -22, 16)
        for _ in range(3):
            x, y = rng.randrange(8, TW - 8), rng.randrange(0, 20)
            for _k in range(6):
                nx, ny = x + rng.randint(-5, 5), y + rng.randint(5, 9)
                pygame.draw.line(b, (46, 46, 48), (x, y), (nx, ny))
                x, y = nx, ny
        for _ in range(3):
            pygame.draw.circle(b, (74, 78, 70), (rng.randrange(TW), rng.randrange(TH)), rng.randint(4, 8))
        pygame.draw.rect(b, (64, 66, 66), (0, TH - 7, TW, 7))
    elif style == 5:                                            # دهان أخضر بيتقشّر
        b.fill((56, 80, 66))
        for _ in range(9):
            pygame.draw.circle(b, (88, 106, 88), (rng.randrange(TW), rng.randrange(TH)), rng.randint(2, 6))
        for _ in range(6):
            pygame.draw.circle(b, (38, 56, 46), (rng.randrange(TW), rng.randrange(TH)), rng.randint(2, 5))
        for x in range(4, TW, 9):
            pygame.draw.line(b, (34, 50, 42), (x, 0), (x, rng.randint(10, 26)), 2)
        _noise(b, rng, 220, -12, 8)
        pygame.draw.rect(b, (40, 52, 44), (0, TH - 8, TW, 8))
    else:                                                       # ورق حيطة مخطّط (الصالة والممرات)
        b.fill((74, 54, 48))
        for x in range(0, TW, 8):
            pygame.draw.rect(b, (66, 47, 42), (x, 0, 4, TH))
        _noise(b, rng, 260, -14, 10)
        for _ in range(6):
            pygame.draw.circle(b, (52, 38, 34), (rng.randrange(TW), rng.randrange(TH - 16)), rng.randint(3, 7))
        pygame.draw.rect(b, (92, 68, 58), (0, TH - 9, TW, 9))
        pygame.draw.rect(b, (60, 44, 38), (0, TH - 10, TW, 1))
        pygame.draw.rect(b, (84, 62, 54), (0, 0, TW, 3))
    return b


def _decal(b, kind):
    if kind == 1:                                               # صورة بإطار (عينيها بتلمع)
        pygame.draw.rect(b, (36, 24, 16), (14, 8, 36, 34))
        pygame.draw.rect(b, (128, 100, 52), (14, 8, 36, 34), 2)
        pygame.draw.rect(b, (14, 12, 14), (18, 12, 28, 26))
        pygame.draw.circle(b, (74, 68, 70), (32, 23), 7)
        pygame.draw.ellipse(b, (74, 68, 70), (21, 29, 22, 12))
        b.set_at((29, 22), (230, 220, 160))
        b.set_at((35, 22), (230, 220, 160))
    elif kind == 2:                                             # شباك على ليل
        pygame.draw.rect(b, (62, 46, 34), (12, 6, 40, 38))
        pygame.draw.rect(b, (20, 30, 58), (17, 11, 30, 28))
        pygame.draw.circle(b, (205, 215, 240), (38, 19), 4)
        pygame.draw.line(b, (62, 46, 34), (32, 11), (32, 39), 2)
        pygame.draw.line(b, (62, 46, 34), (17, 25), (47, 25), 2)
    elif kind == 3:                                             # بصمة إيد حمرا
        pygame.draw.ellipse(b, (118, 10, 10), (22, 24, 16, 16))
        for fx_, top in ((23, 12), (28, 9), (33, 9), (38, 13)):
            pygame.draw.line(b, (118, 10, 10), (fx_, 26), (fx_ - 1, top), 3)
        pygame.draw.line(b, (118, 10, 10), (22, 34), (15, 29), 3)
        for dx_ in (26, 32, 37):
            pygame.draw.line(b, (96, 8, 8), (dx_, 40), (dx_, 52), 2)
    elif kind == 4:                                             # خربشة
        for k in range(5):
            pygame.draw.line(b, (18, 8, 8), (14 + k * 7, 8), (22 + k * 7, 40), 2)
            pygame.draw.line(b, (110, 20, 20), (15 + k * 7, 8), (23 + k * 7, 40), 1)


def _wall_tex(style, decal):
    key = (style, decal)
    t = _TEX_CACHE.get(key)
    if t is None:
        base = _base(style)
        if decal:
            _decal(base, decal)
        t = []
        for i in range(NL):
            s2 = base.copy()
            f = int(255 * i / (NL - 1))
            s2.fill((f, f, f), special_flags=pygame.BLEND_MULT)
            t.append(s2)
        _TEX_CACHE[key] = t
    return t


def _decal_of(mx, my, level):
    v = ((mx * 73856093) ^ (my * 19349663) ^ (level * 83492791)) & 0xFFFF
    v %= 100
    return 0 if v < 78 else 1 + (v - 78) // 6


def _roomstyle(lv):
    rs = getattr(lv, '_fp_style', None)
    if rs is None:
        rs = {}
        for i, (nm, (x, y, w, h), _c) in enumerate(lv.rooms):
            st = _style_for(nm, i)
            for ty in range(y, y + h):
                for tx in range(x, x + w):
                    rs[(tx, ty)] = st
        lv._fp_style = rs
    return rs


def _tex():
    return None


def _bg(floor_c, w, h):
    """خلفية السقف والأرضية (متدرّجة) - بتتخزّن حسب لون الأرضية"""
    key = (floor_c[0] // 10, floor_c[1] // 10, floor_c[2] // 10, w, h)
    s = _state['bg'].get(key)
    if s is None:
        if len(_state['bg']) > 24:
            _state['bg'].clear()
        H2 = h // 2
        s = pygame.Surface((w, h))
        for y in range(0, H2, 2):                               # سقف
            t = y / H2
            v = 0.35 + 0.65 * (1 - t)
            pygame.draw.rect(s, (int(20 * v), int(15 * v), int(19 * v)), (0, y, w, 2))
        for y in range(H2, h, 2):                               # أرضية
            t = (y - H2) / (h - H2)
            v = 0.10 + 0.62 * t
            pygame.draw.rect(s, (int(floor_c[0] * v), int(floor_c[1] * v), int(floor_c[2] * v)), (0, y, w, 2))
        _state['bg'][key] = s
    return s


# ------------------------------------------------------------------ الإدخال
def move_input(game, k, dt):
    """بيرجّع اتجاه الحركة في إحداثيات العالم (dx, dy) ويلف الكاميرا. بيحدّث game.fx / game.fy"""
    fx, fy = game.fx, game.fy
    last = getattr(game, '_fp_last', None)
    if last is None or abs(last[0] - fx) > 1e-6 or abs(last[1] - fy) > 1e-6:
        game.ang = math.atan2(fy, fx)                           # حد غيّر الاتجاه من بره (بداية مرحلة مثلًا)
    ang = game.ang

    if game.state != 'play' or game.chat_open or game.dlg:
        game._fp_last = (game.fx, game.fy)
        game._mdx = 0
        return 0.0, 0.0

    turn = (k[pygame.K_RIGHT] - k[pygame.K_LEFT]) * TURN_SPEED * dt
    fwd = k[pygame.K_w] - k[pygame.K_s] + k[pygame.K_UP] - k[pygame.K_DOWN]
    strafe = k[pygame.K_d] - k[pygame.K_a]
    jx, jy = game.joy
    if jx or jy:                                                # جويستيك اللمس
        turn += jx * TURN_SPEED * dt
        fwd = -jy
        strafe = 0
    if _state['warm'] > 0:
        _state['warm'] -= 1
        game._mdx = 0
    mx = getattr(game, '_mdx', 0)
    game._mdx = 0
    if _state['grab'] and mx:
        mx = max(-MAX_MOUSE_STEP, min(MAX_MOUSE_STEP, mx))
        turn += mx * MOUSE_SENS * SENS
    game.ang = ang = (ang + turn) % (2 * math.pi)
    game.fx, game.fy = math.cos(ang), math.sin(ang)
    game._fp_last = (game.fx, game.fy)
    fwd = max(-1, min(1, fwd))
    # الجنب (يمين) = الاتجاه مدوّر 90 درجة مع عقارب الساعة
    dx = game.fx * fwd - game.fy * strafe
    dy = game.fy * fwd + game.fx * strafe
    return dx, dy


def on_motion(game, e):
    """بيجمّع حركة الماوس الفعلية (rel) - بنتجاهل أول كام فريم بعد قفل الماوس"""
    if _state['grab'] and _state['warm'] <= 0:
        game._mdx = getattr(game, '_mdx', 0) + e.rel[0]


def change_sens(game, mult):
    global SENS
    SENS = max(0.25, min(4.0, SENS * mult))
    return SENS


def mouse_sync(game):
    """الماوس بيتقفل جوه النافذة وهو مخفي وإحنا بنلعب 3D، وبيتحرر في القوايم"""
    want = bool(game.fp and game.state == 'play' and not G.get('TOUCH') and not game.dlg and not game.chat_open)
    if want != _state['grab']:
        _state['grab'] = want
        try:
            pygame.event.set_grab(want)
            pygame.mouse.set_visible(not want)
            pygame.mouse.get_rel()
        except Exception:
            pass
        _state['warm'] = 6
        game._mdx = 0


def release_mouse():
    if _state['grab']:
        _state['grab'] = False
        try:
            pygame.event.set_grab(False)
            pygame.mouse.set_visible(True)
        except Exception:
            pass


# ------------------------------------------------------------------ صوت متجسّم (يمين/شمال/ورا)
DIRECTIONAL = ('creak', 'whisper', 'step', 'knock', 'breath', 'cry', 'laugh', 'slam', 'musicbox')


def play_at(game, name, vol, wx, wy):
    """بيشغّل الصوت من مكان في العالم: شمال/يمين حسب اتجاه نظرك، وبيضعف مع البعد"""
    try:
        if not ENV.get('AUDIO'):
            return False
        snd = ENV['SND'].get(name)
        if snd is None:
            return False
        T = G['T']
        rx, ry = wx - game.px, wy - game.py
        d = math.hypot(rx, ry) or 1.0
        lat = (rx * -game.fy + ry * game.fx) / d                 # +1 يمين ، -1 شمال
        v = vol * ENV['MASTER'] / (1.0 + ((d / T) / 8.0) ** 2)
        a = (lat + 1.0) * math.pi / 4.0
        l, r = math.cos(a) * 1.4, math.sin(a) * 1.4
        snd.set_volume(1.0)
        ch = snd.play()
        if ch is None:
            return False
        ch.set_volume(min(1.0, l * v), min(1.0, r * v))
        return True
    except Exception:
        return False


def play_ambient(game, kind, vol):
    """الأصوات العشوائية بتيجي من ورا أو من جنبك (مش من النص) - بترجّع True لو اتشغّلت"""
    if not game.fp or kind not in DIRECTIONAL:
        return False
    T = G['T']
    a = game.ang + random.choice((1, -1)) * random.uniform(1.1, 3.0)
    dist = random.uniform(4, 9) * T
    x, y = game.px + math.cos(a) * dist, game.py + math.sin(a) * dist
    ok = play_at(game, kind, vol, x, y)
    if ok:
        game._amb_src = (x, y, game.t)
    return ok


def director_update(game, dt):
    """مخرج الرعب: ظل بيتحرّك لما مش بتبص عليه + رعشة ضوء بتحصل كل شوية"""
    if game.state != 'play' or game.js_t > 0 or game.dlg:
        return
    T = G['T']
    d = getattr(game, '_dir', None)
    if d is None or d.get('lv') != id(game.lv):
        d = game._dir = dict(lv=id(game.lv), sh=None, cd=random.uniform(18, 35), flick=0.0,
                             fcd=random.uniform(20, 40))
    if d['flick'] > 0:
        d['flick'] -= dt
    d['fcd'] -= dt
    if d['fcd'] <= 0:                                             # الأنوار بترتعش
        d['fcd'] = random.uniform(28, 60)
        d['flick'] = random.uniform(0.6, 1.4)
        play_ambient(game, 'creak', 0.5)
    sh = d['sh']
    if sh is None:
        d['cd'] -= dt
        if d['cd'] <= 0 and game.fear < 96:
            d['cd'] = random.uniform(30, 55) if game.level >= 2 else random.uniform(45, 80)
            ox, oy = game.px / T, game.py / T
            for _ in range(8):
                a = game.ang + random.uniform(-0.4, 0.4)
                wall, _h = cast(game.lv.grid, game.lv.W, game.lv.H, {}, ox, oy, math.cos(a), math.sin(a))
                if wall is not None and wall[0] >= 6.0:
                    dd = min(wall[0] - 1.0, 10.0)
                    d['sh'] = dict(x=(ox + math.cos(a) * dd) * T, y=(oy + math.sin(a) * dd) * T, life=0.0,
                                   look=0.0, mk=random.randrange(max(1, G['nmon']())))
                    break
        return
    sh['life'] += dt
    rx, ry = sh['x'] - game.px, sh['y'] - game.py
    dist = math.hypot(rx, ry)
    rel = math.atan2(ry, rx) - game.ang
    rel = (rel + math.pi) % (2 * math.pi) - math.pi
    in_view = abs(rel) < 0.6
    if in_view and game.flash_ok() and abs(rel) < 0.3 and dist < 12 * T:
        sh['look'] += dt
    if not in_view and dist > 3 * T:                              # بيقرّب لما تدّيله ضهرك
        k = 1.5 * T * dt / max(dist, 1.0)
        sh['x'] -= rx * k
        sh['y'] -= ry * k
    if sh['look'] > 0.5 or sh['life'] > 9 or dist < 3 * T:
        play_at(game, random.choice(('hiss', 'scream')), 0.5, sh['x'], sh['y'])
        game.glitch_t = max(game.glitch_t, 0.15)
        game.shake = max(game.shake, 0.15)
        game.fear = game.fear + 4
        d['sh'] = None


# ------------------------------------------------------------------ Raycasting
def cast(grid, W, H, objg, ox, oy, rdx, rdy, maxd=48.0):
    """DDA: بيرجّع (الحيطة, [ضربات الأثاث]).
    الحيطة = (dist, side, wallx, mx, my) أو None.
    ضربة الأثاث = (dist_دخول, side, wallx, obj, dist_خروج)"""
    mx, my = int(ox), int(oy)
    ddx = 1e30 if rdx == 0 else abs(1.0 / rdx)
    ddy = 1e30 if rdy == 0 else abs(1.0 / rdy)
    if rdx < 0:
        stx, sdx = -1, (ox - mx) * ddx
    else:
        stx, sdx = 1, (mx + 1.0 - ox) * ddx
    if rdy < 0:
        sty, sdy = -1, (oy - my) * ddy
    else:
        sty, sdy = 1, (my + 1.0 - oy) * ddy
    hits = []
    cur = None
    while True:
        if sdx < sdy:
            dist = sdx
            sdx += ddx
            mx += stx
            side = 0
        else:
            dist = sdy
            sdy += ddy
            my += sty
            side = 1
        if dist > maxd:
            if cur is not None:
                hits.append((cur[0], cur[1], cur[2], cur[3], dist))
            return None, hits
        if side == 0:
            wx = oy + dist * rdy
        else:
            wx = ox + dist * rdx
        wx -= math.floor(wx)
        wall = mx < 0 or my < 0 or mx >= W or my >= H or grid[my][mx] == 1
        o = None if wall else objg.get((mx, my))
        if cur is not None and o is not cur[3]:
            hits.append((cur[0], cur[1], cur[2], cur[3], dist))
            cur = None
        if wall:
            return (dist, side, wx, mx, my), hits
        if o is not None and cur is None:
            cur = (dist, side, wx, o)


# ارتفاع الأثاث (نسبة من ارتفاع الحيطة)
HEIGHTS = [('سرير', 0.34), ('دولاب', 0.92), ('كومودينو', 0.36), ('مكتب', 0.42), ('رف', 0.95),
           ('كنب', 0.40), ('ترابيز', 0.36), ('صندوق', 0.28), ('تلاج', 0.78), ('خزان', 0.62),
           ('بيانو', 0.50), ('هز', 0.42), ('دُرج', 0.42), ('درج', 0.42), ('مراي', 0.90),
           ('صورة', 0.88), ('دُمي', 0.45), ('دمي', 0.45)]


def obj_height(o):
    if o.kind in ('door', 'exit'):
        return 1.0
    nm = str(o.name)
    for key, h in HEIGHTS:
        if key in nm:
            return h
    return 0.55


def _q(r, lo=6, hi=120):
    """بيقرّب نصف قطر الـ glow لمضاعفات 6 وبحد أقصى - علشان الكاش يشتغل"""
    return max(lo, min(hi, int(r) // 6 * 6))


def _shade(c, b):
    return (min(255, int(c[0] * b)), min(255, int(c[1] * b)), min(255, int(c[2] * b)))


# ------------------------------------------------------------------ الرسم
def _camera(game):
    """بيرجّع (x, y, زاوية) بالـ pixels - بيدعم التفرّج على صاحبك لما تموت"""
    if game.state == 'lose' and game.net_on:
        sl = game.spec_list()
        if sl:
            p = sl[game.spec_i % len(sl)]
            cx, cy = game.cam_pos()
            return cx, cy, math.atan2(p['fy'], p['fx']) if (p['fx'] or p['fy']) else game.ang
    return game.px, game.py, game.ang


def _light_fn(game, px_t, py_t, candles):
    """بيرجّع دالة بتحسب السطوع حسب البعد وزاوية الكشاف والشموع"""
    tv = 1.0 - 0.35 * max(0.0, (game.fear - 45) / 55)
    flash = game.flash_ok()
    m = tv
    px_, py_ = game.px, game.py
    near_g = any(g['a'] > 0.3 and math.hypot(g['x'] - px_, g['y'] - py_) < 230 for g in game.ghosts)
    if flash and (game.battery < 20 or game.fear > 70 or near_g):
        m = tv * random.choice([1, 1, 1, 0.85, 0.55])
    amb = 0.035
    dr = getattr(game, '_dir', None)
    fl = random.choice((0.12, 0.35, 0.8, 1.0)) if (dr and dr.get('flick', 0) > 0) else 1.0

    def f(real_d, cam_x, hx, hy):
        b = (amb + 0.50 * tv / (1.0 + (real_d / 1.9) ** 2)) * fl
        if flash:
            fall = max(0.0, 1.0 - real_d / 11.0)
            b += 1.05 * m * fl * fall ** 1.3 * math.exp(-(cam_x * 1.55) ** 2)
        for (cx, cy) in candles:
            dc = math.hypot(hx - cx, hy - cy)
            if dc < 9:
                b += 0.85 / (1.0 + (dc / 2.0) ** 2)
        return b if b < 1.0 else 1.0

    return f


def draw_world(game, s):
    lv = game.lv
    SW, SH, T = G['SW'], G['SH'], G['T']
    t_start = time.perf_counter()
    base = 6 if G.get('ANDROID') else 4
    # ضبط تلقائي: لو الجهاز بطيء بنقلّل عدد الأعمدة، ولو سريع بنرجّعها
    if _state['last']:
        gap = t_start - _state['last']
        if gap < 0.25:
            _state['ema'] += (gap - _state['ema']) * 0.08
    _state['last'] = t_start
    _state['cnt'] += 1
    if _state['cnt'] % 45 == 0:
        if _state['ema'] > 0.026 and _state['colw'] < 12:
            _state['colw'] += 2
        elif _state['ema'] < 0.0175 and _state['colw'] > base:
            _state['colw'] -= 2
    colw = max(base, _state['colw'])
    while SW % colw:
        colw += 1
    n = SW // colw
    mouse_sync(game)

    px_, py_, ang = _camera(game)
    ox, oy = px_ / T, py_ / T
    dirx, diry = math.cos(ang), math.sin(ang)
    plx, ply = -diry * FOV_PLANE, dirx * FOV_PLANE

    # --- إزاحة الأفق: اهتزاز + مشي
    shy = 0
    if game.shake > 0:
        shy = random.randint(-7, 7)
    elif game.fear > 75:
        shy = random.randint(-2, 2)
    bob = math.sin(game.t * 10.5) * 2.5 if game.moving and game.state == 'play' else 0.0
    hor = SH // 2 + int(bob) + shy
    view = SH

    # --- سقف وأرضية
    tx0, ty0 = int(ox), int(oy)
    fc = (60, 46, 40)
    if 0 <= ty0 < lv.H and 0 <= tx0 < lv.W:
        fc = lv.floorc[ty0][tx0]
        if lv.grid[ty0][tx0] == 1:
            fc = (60, 46, 40)
    fc = tuple(min(255, c * 2 + 20) for c in fc)
    bgs = _bg(fc, SW, SH + 60)
    s.blit(bgs, (0, hor - (SH + 60) // 2))

    # --- شبكة الأوبجكتس (الأثاث والأبواب)
    objg = {}
    for o in game.objs:
        if o.kind == 'door' and not o.solid:
            continue
        if not (o.solid or o.kind in ('door', 'exit')):
            continue
        r = o.rect
        for j in range(r.top // T, (r.bottom - 1) // T + 1):
            for i in range(r.left // T, (r.right - 1) // T + 1):
                objg[(i, j)] = o

    candles = [(tx + 0.5, ty + 0.5) for ci, (tx, ty) in enumerate(lv.candles)
               if ci not in game.out_c and game.blackout <= 0
               and abs(tx - ox) < 14 and abs(ty - oy) < 14]
    lightf = _light_fn(game, ox, oy, candles)

    rstyle = _roomstyle(lv)
    lvl_no = game.level
    zbuf = [1e9] * n
    grid, W, H = lv.grid, lv.W, lv.H
    f_line = SH * K
    sqrt = math.sqrt

    for i in range(n):
        cam = 2.0 * i / n - 1.0
        rdx, rdy = dirx + plx * cam, diry + ply * cam
        wall, hits = cast(grid, W, H, objg, ox, oy, rdx, rdy)
        rl = sqrt(rdx * rdx + rdy * rdy)
        x = i * colw
        if wall is not None:
            dist, side, wx, mx, my = wall
            zbuf[i] = dist
            line_h = int(f_line / max(dist, 0.05))
            top = hor - line_h // 2
            b = lightf(dist * rl, cam, ox + rdx * dist, oy + rdy * dist)
            if side == 1:
                b *= 0.78
            lvl = int(b * (NL - 1))
            txi = int(wx * TW)
            if (side == 0 and rdx > 0) or (side == 1 and rdy < 0):
                txi = TW - 1 - txi
            txi = max(0, min(TW - 1, txi))
            if side == 0:                                         # الخلية اللي قبل الحيطة = الأوضة اللي بنبص منها
                pc = (mx - (1 if rdx > 0 else -1), my)
            else:
                pc = (mx, my - (1 if rdy > 0 else -1))
            texs = _wall_tex(rstyle.get(pc, 0), _decal_of(mx, my, lvl_no))
            _blit_col(s, texs[lvl], txi, x, colw, top, line_h, view)
        else:
            zbuf[i] = 1e9
        # --- الأثاث من الأبعد للأقرب
        for dist, side, wx, o, dout in reversed(hits):
            if wall is not None:
                if dist >= wall[0]:
                    continue
                dout = min(dout, wall[0])
            hf = obj_height(o)
            if hf < 0.5:                                          # السطح العلوي للصندوق (علشان يبان مصمّت)
                yf = hor + int(f_line / max(dout, 0.05) * (0.5 - hf))
                yn = hor + int(f_line / max(dist, 0.05) * (0.5 - hf))
                ya, yz = max(yf, -50), min(yn, SH + 50)
                if yz > ya:
                    dm = (dist + dout) * 0.5
                    bt = lightf(dm * rl, cam, ox + rdx * dm, oy + rdy * dm)
                    pygame.draw.rect(s, _shade(o.color, 0.45 + 1.2 * bt), (x, ya, colw, yz - ya))
            line_h = int(f_line / max(dist, 0.05))
            bottom = hor + line_h // 2
            ttop = bottom - int(line_h * hf)
            b = lightf(dist * rl, cam, ox + rdx * dist, oy + rdy * dist)
            if side == 1:
                b *= 0.8
            col = _shade(o.color, 0.35 + 1.0 * b)
            ytop = max(ttop, -50)
            yb = min(bottom, SH + 50)
            if yb > ytop:
                pygame.draw.rect(s, col, (x, ytop, colw, yb - ytop))
                if o.kind in ('door', 'exit'):
                    if 0.1 < wx < 0.9:                            # ألواح الباب
                        pc = _shade(o.color, 0.55 + 0.9 * b)
                        pygame.draw.rect(s, pc, (x, ytop + line_h // 10, colw, int(line_h * 0.34)))
                        pygame.draw.rect(s, pc, (x, ytop + int(line_h * 0.52), colw, int(line_h * 0.34)))
                    if 0.78 < wx < 0.86:                          # الأكرة
                        pygame.draw.rect(s, _shade((220, 190, 60), 0.3 + b),
                                         (x, hor - line_h // 40 - 2, colw, max(3, line_h // 18)))
                else:
                    pygame.draw.rect(s, _shade(o.color, 0.6 + 1.2 * b), (x, ytop, colw, 2))   # حرف علوي أفتح
            if hf >= 0.9 and dist < zbuf[i]:
                zbuf[i] = dist

    t_cols = time.perf_counter()
    _floor_light(game, s, hor, SW, SH)
    _draw_sprites(game, s, ox, oy, dirx, diry, plx, ply, hor, zbuf, colw, n, lightf, f_line)
    t_spr = time.perf_counter()
    _overlays(game, s)
    if SHOW_PROF:
        t_end = time.perf_counter()
        draw_text = G['draw_text']
        fps = 1.0 / max(_state['ema'], 1e-4)
        draw_text(s, "FPS %d | أعمدة %d (عرض %dpx) | حيطان %.1fms | سبرايت %.1fms | واجهة %.1fms"
                  % (fps, n, colw, (t_cols - t_start) * 1000, (t_spr - t_cols) * 1000, (t_end - t_spr) * 1000),
                  16, (120, 255, 120), 12, SH - 74, 'l')


def _floor_light(game, s, hor, SW, SH):
    """بقعة ضوء الكشاف على الأرض (بتتبني مرة واحدة)"""
    if not game.flash_ok():
        return
    cone = _state['cone']
    if cone is None or cone.get_width() != SW:
        ch = SH // 2
        cone = pygame.Surface((SW, ch), pygame.SRCALPHA)
        for i in range(40, 0, -1):
            k = i / 40.0
            a = int(70 * (1 - k) ** 1.4)
            pygame.draw.ellipse(cone, (255, 235, 170, a), (SW // 2 - int(SW * 0.30 * k), int(ch * 0.15),
                                                           int(SW * 0.60 * k), int(ch * 1.1 * k)))
        _state['cone'] = cone
    s.blit(cone, (0, hor + int(SH * 0.02)))


def _blit_col(s, tex, txi, x, colw, top, h, view):
    if h <= 0:
        return
    if top >= view or top + h <= 0:
        return
    if h > view * 1.5:                                            # قريب جدًا: نرسم الجزء الظاهر بس من التكستشر
        a = int(max(0, -top) * TH / h)                            # أول صف ظاهر في التكستشر
        b = int((min(view, top + h) - top) * TH / h) + 2          # آخر صف ظاهر (+ هامش)
        a = max(0, min(TH - 1, a))
        b = max(a + 1, min(TH, b))
        sub = tex.subsurface((txi, a, 1, b - a))
        y0 = top + int(a * h / TH)
        hh = max(1, top + int(b * h / TH) - y0)
        s.blit(pygame.transform.scale(sub, (colw, hh)), (x, y0))
    else:
        sub = tex.subsurface((txi, 0, 1, TH))
        s.blit(pygame.transform.scale(sub, (colw, h)), (x, top))


# ------------------------------------------------------------------ Sprites (وحوش، لاعبين، عيون، شموع)
def _fig(pid):
    """شكل بسيط للاعب التاني (ظل ملوّن)"""
    f = _state['sprites'].get(('p', pid))
    if f is None:
        col = G['PEER_COLS'][pid % 8]
        f = pygame.Surface((60, 150), pygame.SRCALPHA)
        body = tuple(int(c * 0.55) for c in col)
        pygame.draw.ellipse(f, body, (10, 44, 40, 100))
        pygame.draw.circle(f, tuple(min(255, int(c * 0.8)) for c in col), (30, 26), 20)
        pygame.draw.circle(f, (10, 10, 10), (23, 24), 3)
        pygame.draw.circle(f, (10, 10, 10), (37, 24), 3)
        _state['sprites'][('p', pid)] = f
    return f


def _draw_sprite_img(s, img, sx, ty, hor, f_line, hf, zbuf, colw, n, alpha, bright, lift=0.0, aspect=None):
    """بيرسم سبرايت (صورة) في العمق ty عند عمود الشاشة sx. hf = الارتفاع كنسبة من الحيطة"""
    SW, SH = G['SW'], G['SH']
    h = int(f_line / ty * hf)
    if h < 4:
        return None
    h = min(h, int(SH * 1.5))
    iw, ih = img.get_size()
    w = max(2, int(h * (aspect or iw / ih)))
    sc = pygame.transform.scale(img, (w, h))
    if bright < 0.999:
        v = max(0, min(255, int(255 * bright)))
        sc.fill((v, v, v, 255), special_flags=pygame.BLEND_RGBA_MULT)
    if alpha < 255:
        sc.set_alpha(alpha)
    floor_y = hor + int(f_line / ty * 0.5) - int(lift * f_line / ty)
    y0 = floor_y - h
    x0 = int(sx - w / 2)
    c0 = max(0, x0 // colw)
    c1 = min(n - 1, (x0 + w) // colw)
    run = None
    for c in range(c0, c1 + 1):
        vis = zbuf[c] > ty
        if vis and run is None:
            run = c
        if (not vis or c == c1) and run is not None:
            end = c if vis else c - 1
            xa = run * colw
            wa = (end - run + 1) * colw
            src_x = xa - x0
            if src_x < 0:
                wa += src_x
                xa -= src_x
                src_x = 0
            wa = min(wa, w - src_x)
            if wa > 0:
                s.blit(sc, (xa, y0), (src_x, 0, wa, h))
            run = None
    return x0 + w // 2, y0, w, h


def _project(ox, oy, dirx, diry, plx, ply, x, y, n, colw):
    rx, ry = x - ox, y - oy
    det = plx * diry - dirx * ply
    if abs(det) < 1e-9:
        return None
    inv = 1.0 / det
    tx = inv * (diry * rx - dirx * ry)
    ty = inv * (-ply * rx + plx * ry)
    if ty < 0.12:
        return None
    sx = (n * colw / 2.0) * (1.0 + tx / ty)
    return sx, ty


def _draw_sprites(game, s, ox, oy, dirx, diry, plx, ply, hor, zbuf, colw, n, lightf, f_line):
    T = G['T']
    SW, SH = G['SW'], G['SH']
    mon_of, glow, draw_text = G['mon_of'], G['glow'], G['draw_text']
    lv = game.lv
    items = []                                                      # (عمق, نوع, بيانات)

    def add(x, y, kind, data):
        p = _project(ox, oy, dirx, diry, plx, ply, x / T, y / T, n, colw)
        if p:
            items.append((p[1], p[0], kind, data))

    for g in game.ghosts:
        add(g['x'], g['y'], 'ghost', (g.get('mk', 0), max(0.0, g['a']) * 200, g))
    if game.app:
        add(game.app[0], game.app[1], 'ghost', (game.app[3] if len(game.app) > 3 else 0, 225, None))
    for e in game.eyes:
        if (game.t * 0.9 + e['ph']) % 4 < 0.14:
            continue
        add(e['x'], e['y'], 'eyes', e)
    plist = list(game.peers.values())
    if game.mimic:
        mm = game.mimic
        plist.append(dict(id=mm['pid'], x=mm['x'], y=mm['y'], fx=mm['fx'], fy=mm['fy'], lv=game.level, fake=True))
    for p in plist:
        if p['lv'] != game.level:
            continue
        for gx, gy, ga, gk in p.get('gh', []):
            add(gx, gy, 'ghost', (gk, ga * 160, None))
        add(p['x'], p['y'], 'peer', p)
    for ci, (tx, ty) in enumerate(lv.candles):
        if ci in game.out_c or game.blackout > 0:
            continue
        add(tx * T + T / 2, ty * T + T / 2, 'candle', ci)
    dr = getattr(game, '_dir', None)
    if dr and dr.get('sh'):
        add(dr['sh']['x'], dr['sh']['y'], 'shadow', dr['sh'])
    for o in game.objs:                                             # أوراق الحكاية اللي لسه ما اتقرتش
        if o.kind == 'note' and o.id not in game.done:
            add(o.rect.centerx, o.rect.centery, 'paper', o)
    for o in game.objs:                                             # حاجات ينفع تتاخد/تتفتش (مش صلبة)
        if o.can and not o.solid and o.kind in ('battery', 'note', 'special'):
            add(o.rect.centerx, o.rect.centery, 'item', o)

    items.sort(key=lambda it: -it[0])                               # من الأبعد للأقرب
    for ty, sx, kind, data in items:
        c = int(sx // colw)
        if kind == 'ghost':
            mk, alpha, g = data
            if g is not None and g.get('scare_t', 0.0) > 0:        # بيرتعش من الكشاف
                sx += random.randint(-5, 5)
            img = mon_of(mk)['img']
            b = max(0.25, lightf(ty, sx / SW * 2 - 1, 1e6, 1e6) * 1.6)
            r = _draw_sprite_img(s, img, sx, ty, hor, f_line, 0.92, zbuf, colw, n, int(alpha), min(1.0, b))
            if g is not None and g.get('say') and g['a'] > 0.3 and r:
                draw_text(s, str(g['say'][0]).replace("{name}", game.name()), 24, (220, 30, 30), r[0], max(40, r[1] - 18), 'c')
        elif kind == 'eyes':
            e = data
            if 0 <= c < n and zbuf[c] > ty:
                a = min(1.0, e['t'] * 1.5)
                ey = hor - int(f_line / ty * 0.12)
                sz = max(5, int(f_line / ty * 0.09))
                for off in (-1, 1):
                    ex = int(sx + off * sz * 1.5)
                    glow(s, ex, ey, _q(sz + 8), (255, 30, 20), (80, 140, 200)[min(2, int(a * 3))])
                    pygame.draw.ellipse(s, (255, 200, 190), (ex - 3, ey - 2, 6, 4))
        elif kind == 'peer':
            p = data
            dead = p['id'] in game.dead_ids
            b = max(0.3, lightf(ty, sx / SW * 2 - 1, 1e6, 1e6) * 1.8)
            r = _draw_sprite_img(s, _fig(p['id']), sx, ty, hor, f_line, 0.28 if dead else 0.62, zbuf, colw, n,
                                 255, min(1.0, b))
            if r and not dead:
                draw_text(s, game.pname(p['id']), 16, G['PEER_COLS'][p['id'] % 8], r[0], max(40, r[1] - 18), 'c')
        elif kind == 'shadow':
            sh = data
            a = int(min(1.0, sh['life'] / 0.8) * 215)
            r = _draw_sprite_img(s, mon_of(sh['mk'])['img'], sx, ty, hor, f_line, 0.95, zbuf, colw, n, a, 0.05)
            if r and 0 <= c < n and zbuf[c] > ty:
                for off in (-0.11, 0.11):
                    glow(s, int(r[0] + off * r[2]), int(r[1] + 0.2 * r[3]), 18, (255, 20, 10), 200)
        elif kind == 'paper':
            o = data
            if 0 <= c < n and zbuf[c] > ty and ty < 11:
                L = f_line / ty
                py_ = hor + int(L * 0.5) - int(L * (obj_height(o) + 0.12))
                a = (70 + int(40 * math.sin(game.t * 3 + o.rect.x))) // 20 * 20
                glow(s, int(sx), py_, _q(L * 0.10, 12, 36), (255, 235, 150), a)
                pygame.draw.rect(s, (245, 235, 200), (int(sx) - 3, py_ - 2, 6, 4))
        elif kind == 'candle':
            if 0 <= c < n and zbuf[c] > ty:
                fy_ = hor + int(f_line / ty * 0.5) - int(f_line / ty * 0.34)
                sz = max(3, int(f_line / ty * 0.05))
                pygame.draw.rect(s, (230, 225, 200), (int(sx) - sz // 2, fy_, sz, sz * 3))
                glow(s, int(sx), fy_ - sz, _q(sz * 5 + 14), (255, 190, 60), 190)
        elif kind == 'item':
            if 0 <= c < n and zbuf[c] > ty:
                fy_ = hor + int(f_line / ty * 0.5) - int(f_line / ty * 0.25)
                a = (90 + int(60 * math.sin(game.t * 3 + sx))) // 30 * 30
                glow(s, int(sx), fy_, _q(f_line / ty * 0.12, 12), (255, 230, 140), a)


# ------------------------------------------------------------------ تأثيرات فوق الشاشة (نفس اللي في 2D)
def _overlays(game, s):
    SW, SH = G['SW'], G['SH']
    A, glow, draw_text, draw_ghost = G['A'], G['glow'], G['draw_text'], G['draw_ghost']

    src = getattr(game, '_amb_src', None)
    if src and game.t - src[2] < 1.6:                              # من أي ناحية جه الصوت
        T = G['T']
        rx, ry = src[0] - game.px, src[1] - game.py
        dd = math.hypot(rx, ry) or 1.0
        lat = (rx * -game.fy + ry * game.fx) / dd
        fwd = (rx * game.fx + ry * game.fy) / dd
        fade = 1.0 - (game.t - src[2]) / 1.6
        al = (40, 70, 100, 130)[min(3, int(fade * 4))]
        if fwd < -0.35 and abs(lat) < 0.55:
            glow(s, SW // 2, SH - 10, 150, (170, 20, 20), al)
        else:
            glow(s, 10 if lat < 0 else SW - 10, SH // 2, 150, (170, 20, 20), al)
    if game.dash:
        game.draw_dash(s)
    if game.hall:
        _t, kind, hx, hy, word = game.hall
        if kind == 'ghost':
            draw_ghost(s, hx, hy + 90, 150, game.t, int(hx) % max(1, G['nmon']() - 1))
        elif kind == 'word':
            draw_text(s, word, 64, (200, 10, 10), hx, hy, 'c')
        else:
            for off in (-14, 14):
                glow(s, hx + off, hy, 14, (255, 30, 20), 200)
    if game.say:
        draw_text(s, game.say[0], 52, (200, 20, 20), SW // 2 + random.randint(-4, 4),
                  SH // 2 - 130 + random.randint(-4, 4), 'c')
    if game.pulse > 0.03 and game.state == 'play':
        pv = A.get('pulse')
        if pv is None:
            pv = A['pulse'] = pygame.Surface((SW, SH))
            pv.fill((150, 0, 0))
        pv.set_alpha(int(80 * game.pulse))
        s.blit(pv, (0, 0))
    if game.fear > 5:
        pulse = 1.0 + (0.12 * math.sin(game.t * (4 + game.fear / 15)) if game.fear > 40 else 0.0)
        A['vig'].set_alpha(min(255, int(255 * min(1, game.fear / 100) * pulse)))
        s.blit(A['vig'], (0, 0))
    if game.fear > 60 and game.state == 'play':
        rr = random.Random(int(game.t * 5))
        for _ in range(int((game.fear - 55) / 8) + 1):
            x = rr.choice((rr.randint(0, 90), rr.randint(SW - 90, SW)))
            y = rr.randint(0, SH - 120)
            pygame.draw.line(s, (130 + rr.randint(0, 70), 8, 8), (x, y),
                             (x + rr.randint(-30, 30), y + rr.randint(40, 110)), rr.randint(1, 3))
    if game.glitch_t > 0:
        game.glitch(s)
    game.draw_hud(s)
    game.draw_minimap(s)
    if game.show_map:
        game.draw_map(s)
    if game.net_on:
        game.draw_chat(s)
    if game.state == 'play' and not G.get('TOUCH'):
        draw_text(s, "V: 2D/3D   N: خريطة صغيرة   [ ]: حساسية الماوس", 16, (120, 120, 120), SW - 16, SH - 52, 'r')
