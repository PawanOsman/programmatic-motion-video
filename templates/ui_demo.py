"""UI walkthrough: a desktop web app demonstrated step by step. A pointer clicks, a modal opens, a name
is typed, a card loads in, a teammate is invited, a project is published; the camera frames each
action and a caption names the step. About 22 s with a light soundtrack.

Run:   python ui_demo.py sheet   |   python ui_demo.py render ui_demo.mp4
The app is drawn on a 1920x1080 stage; other frame sizes (MV_SIZE=1080x1920) fit the stage.
Swap the placeholder app for the real product's screens, names and copy.
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'engine'))  # repo layout

import fx
import icons
import layout
import media
import mv
import sfx
import ui
from mv import *

CONFIG = dict(
    app='Acme Projects', url='app.acme.example', primary='#2563EB',
    projects=[('Brand refresh', '12 files · edited 2h ago'), ('Q3 campaign', '8 files · edited yesterday'),
              ('Onboarding', '21 files · edited Mon')],
    new_project='Spring launch',
    invitee='sara@acme.example',
    steps=['Create a project', 'Invite your team', 'Publish it'],
    outro='Done in under a minute.',
)
C = CONFIG
W, H = mv.env_size((1920, 1080))
FPS = mv.env_fps(30)
L = layout.Frame(W, H)
TH = ui.LIGHT.with_(accent=C['primary'], accent2=C['primary'])

# ---- stage layout (1920x1080 coordinates) ----
WIN = (80, 60, 1840, 1020)
SIDEBAR_W = 290
MAIN_X0 = WIN[0] + SIDEBAR_W + 40
NEW_BTN = (1560, 232, 1800, 292)
INVITE_BTN = (1392, 138, 1540, 190)
GRID = layout.grid((MAIN_X0, 320, 1800, 990), 3, 2, 30)
MODAL = (660, 300, 1260, 700)
MODAL_BUTTONS = (('Cancel', 'secondary'), ('Create', 'primary'))
POP = (1180, 206, 1640, 380)          # invite popover
TOGGLE = (GRID[3][2] - 110, GRID[3][3] - 52)

# ---- timeline (seconds, one source of truth for picture and sound) ----
T = dict(step1=0.6, click_new=2.2, type_at=3.2, cps=14)
T['create'] = type_end(C['new_project'], T['type_at'], T['cps']) + 0.7
T['loaded'] = T['create'] + 1.3
T['step2'] = T['loaded'] + 1.4
T['click_invite'] = T['step2'] + 1.3
T['type2'] = T['click_invite'] + 0.6
T['sent'] = type_end(C['invitee'], T['type2'], 18) + 0.5
T['step3'] = T['sent'] + 1.6
T['click_toggle'] = T['step3'] + 1.4
T['outro'] = T['click_toggle'] + 2.4
T['end'] = T['outro'] + 2.6
MB = ui.modal_buttons(MODAL, TH, MODAL_BUTTONS)


def mid(r):
    return (r[0] + r[2]) / 2, (r[1] + r[3]) / 2


class Walkthrough(Scene):
    def __init__(self):
        super().__init__(T['end'])
        base = min(W / 1920, H / 1080) * L.pick(0.97, 1.0, 1.0)
        self.cam = Camera(1.0, 960, 540, [
            (T['click_new'] + 0.2, T['click_new'] + 1.1, 1.45, 960, 520),        # into the modal
            (T['create'] + 0.1, T['create'] + 1.0, 1.25, 900, 700),             # to the new card
            (T['step2'] + 0.3, T['step2'] + 1.2, 1.55, 1380, 330),              # to the invite area
            (T['step3'] + 0.2, T['step3'] + 1.1, 1.4, 700, 760),                # back to the card
            (T['outro'], T['outro'] + 1.2, 0.92, 960, 560)], screen=(W / 2, H / 2), base=base)
        cx_new, cy_new = mid(NEW_BTN)
        cx_c, cy_c = mid(MB[1])
        self.ptr = Pointer([(0.8, 1500, 900), (T['click_new'] - 0.1, cx_new, cy_new), (T['type_at'], cx_new - 40, cy_new + 260),
                            (T['create'] - 0.5, cx_c - 60, cy_c + 20), (T['create'] - 0.05, cx_c, cy_c),
                            (T['step2'] + 0.5, 1200, 620), (T['click_invite'] - 0.05, *mid(INVITE_BTN)),
                            (T['sent'] + 0.4, 1320, 470), (T['click_toggle'] - 0.05, TOGGLE[0] + 30, TOGGLE[1]),
                            (T['outro'] + 0.6, TOGGLE[0] + 160, TOGGLE[1] + 120)],
                           clicks=(T['click_new'], T['create'], T['click_invite'], T['click_toggle']), show=(0.8, T['end'] - 0.3),
                           ring=C['primary'])

    def app(self, c, u):
        area = ui.window(c, WIN, TH, url=C['url'])
        x0, y0, x1, y1 = area
        ui.sidebar(c, (x0, y0, x0 + SIDEBAR_W, y1), TH, [('folder', 'Projects'), ('users', 'Team'), ('chart-line', 'Analytics'),
                                                        ('settings', 'Settings')], active=0, title=C['app'])
        ui.text_field(c, (MAIN_X0, 138, MAIN_X0 + 420, 190), TH, placeholder='Search projects', icon='search', size=21)
        invite_p = self.ptr.pressed(u, T['click_invite'])
        ui.button(c, INVITE_BTN, 'Invite', TH, 'secondary', press=invite_p, icon='user-plus', size=21)
        team = [('LA', '#0EA5E9'), ('KO', '#22C55E'), ('RM', '#F59E0B')]
        joined = presence(u, T['sent'] + 0.15, None, 0.4, ease_in=out_back)
        for i, (ini, col) in enumerate(team + ([('SJ', '#EC4899')] if joined > 0 else [])):
            k = joined if i == 3 else 1.0
            with Layer(c, clamp(k * 2), scale=max(0.01, k), pivot=(1600 + i * 44, 164)):
                ui.avatar(c, 1600 + i * 44, 164, 22, TH, ini, col=col, ring='#FFFFFF')
        ui.label(c, 'Projects', MAIN_X0, 262, TH, 40, 750)
        ui.button(c, NEW_BTN, 'New project', TH, icon='plus', press=self.ptr.pressed(u, T['click_new']), size=22)
        for i, (name, meta) in enumerate(C['projects']):
            self.project_card(c, u, GRID[i], name, meta, i, 1.0)
        # the new project: a loading skeleton, then the real card
        if u >= T['create'] + 0.25:
            r = GRID[3]
            p = presence(u, T['create'] + 0.25, None, 0.4)
            if u < T['loaded']:
                with Layer(c, p):
                    ui.card(c, r, TH)
                    ui.skeleton(c, (r[0] + 18, r[1] + 18, r[2] - 18, r[1] + 190), u, TH)
                    ui.skeleton(c, (r[0] + 22, r[1] + 214, r[0] + 260, r[1] + 240), u, TH)
                    ui.skeleton(c, (r[0] + 22, r[1] + 256, r[0] + 200, r[1] + 276), u, TH)
            else:
                self.project_card(c, u, r, C['new_project'], 'Just now', 3, presence(u, T['loaded'], None, 0.35), new=True)

    def project_card(self, c, u, r, name, meta, i, a, new=False):
        x0, y0, x1, y1 = r
        with Layer(c, a, bounds=(x0 - 90, y0 - 90, x1 + 90, y1 + 120)):
            ui.card(c, r, TH)
            img = media.placeholder(440, 190, seed=i + 1)
            with Clip(c, (x0 + 14, y0 + 14, x1 - 14, y0 + 190), r=12):
                cover(c, img, x0 + 14, y0 + 14, x1 - 14, y0 + 190)
            ui.label(c, name, x0 + 24, y0 + 228, TH, 26, 680)
            ui.label(c, meta, x0 + 24, y0 + 266, TH, 19, 450, TH.muted)
            if new:
                on = seg(u, T['click_toggle'], T['click_toggle'] + 0.25)
                ui.toggle(c, TOGGLE[0], TOGGLE[1], on, TH, size=34)
                ui.label(c, 'Public', TOGGLE[0] - 16, TOGGLE[1], TH, 19, 550, TH.muted, align='right')
                live = presence(u, T['click_toggle'] + 0.2, None, 0.35, ease_in=out_back)
                if live > 0:
                    with Layer(c, clamp(live * 2), scale=live, pivot=(x1 - 60, y0 + 40)):
                        ui.badge(c, x1 - 26, y0 + 40, 'Live', TH, fill=TH.success, align='right', size=18, dot=False)

    def draw(self, c, u):
        fx.gradient(c, (0, 0, W, H), ['#DCE7FF', '#F4F0FF'], angle=35)
        fx.grid(c, W, H, u, step=L.u(48), col='#1E3A8A', a=0.06, kind='dots')
        c.save()
        self.cam.apply(c, u)
        with Layer(c, presence(u, 0.0, None, 0.5), scale=0.97 + 0.03 * out_cubic(seg(u, 0, 0.6)), pivot=(960, 540)):
            self.app(c, u)
            # modal: create project
            mp = presence(u, T['click_new'] + 0.1, T['create'] + 0.25, 0.35, 0.25)

            def form(cc, r):
                val = typed(C['new_project'], u, T['type_at'], T['cps'])
                ui.label(cc, 'Name', r[0], r[1] + 12, TH, 20, 600, TH.muted)
                ui.text_field(cc, (r[0], r[1] + 36, r[2], r[1] + 104), TH, val, 'Project name', focus=1.0, t=u,
                              typing=typing(C['new_project'], u, T['type_at'], T['cps']), size=24)
            ui.modal(c, (-2000, -2000, 4000, 3000), MODAL, TH, 'New project', '', MODAL_BUTTONS, mp,
                     press=(1, self.ptr.pressed(u, T['create'])), icon='folder-plus', content=form)
            # invite popover
            pp = presence(u, T['click_invite'] + 0.05, T['sent'] + 0.3, 0.3, 0.25)
            if pp > 0:
                with Layer(c, clamp(pp * 1.5), scale=(1, 0.9 + 0.1 * pp), pivot=(POP[2], POP[1])):
                    ui.card(c, POP, TH, radius=14, elevation=1.3)
                    ui.label(c, 'Invite by email', POP[0] + 26, POP[1] + 40, TH, 21, 650)
                    val = typed(C['invitee'], u, T['type2'], 18)
                    ui.text_field(c, (POP[0] + 24, POP[1] + 72, POP[2] - 24, POP[1] + 136), TH, val, 'name@company.com',
                                  focus=1.0, t=u, typing=typing(C['invitee'], u, T['type2'], 18), icon='mail', size=21)
            self.ptr.draw(c, u)
            fx.confetti(c, u, T['click_toggle'] + 0.2, TOGGLE[0] - 60, TOGGLE[1] - 20, n=90, power=1300, gravity=1400, size=12)
        c.restore()
        # notifications live in screen space, so they stay in view whatever the camera does
        tw = min(L.u(520), W - L.u(80))
        box = (W - L.u(40) - tw, L.u(40), W - L.u(40), L.u(136))
        ui.toast(c, box, TH, 'Project created', C['new_project'], p=presence(u, T['loaded'] + 0.2, T['loaded'] + 2.4))
        ui.toast(c, box, TH, 'Invite sent', C['invitee'], icon='send', col=TH.accent, p=presence(u, T['sent'] + 0.3, T['sent'] + 2.2))
        ui.toast(c, box, TH, 'Published', 'Your project is live', icon='globe',
                 p=presence(u, T['click_toggle'] + 0.4, T['outro'] + 0.8))
        self.caption(c, u)

    def caption(self, c, u):
        starts = [T['step1'], T['step2'], T['step3']]
        idx = max([i for i, s in enumerate(starts) if u >= s] or [0])
        a = presence(u, T['step1'], T['outro'] + 0.2, 0.4, 0.3)
        if a > 0:
            text_ = f"{idx + 1}  ·  {C['steps'][idx]}"
            f = mv.font('Inter', L.u(30), wght=650)
            w = mv.width(text_, f) + L.u(80)
            cx, cy = W / 2, H - L.u(70)
            swap = presence(u, starts[idx], None, 0.3)
            with Layer(c, a, dy=(1 - a) * L.u(30)):
                rrect(c, cx - w / 2, cy - L.u(34), cx + w / 2, cy + L.u(34), L.u(34), paint('#0F172A', 0.88))
                with Layer(c, swap, dy=(1 - swap) * L.u(12)):
                    mv.text(c, text_, cx, cy, f, '#FFFFFF', align='center')
        oa = presence(u, T['outro'] + 1.0, None, 0.5)
        if oa > 0:
            f = mv.font('Inter', L.u(50), wght=800)
            w = mv.width(C['outro'], f) + L.u(90)
            with Layer(c, oa, dy=(1 - oa) * L.u(30)):
                rrect(c, W / 2 - w / 2, H - L.u(128), W / 2 + w / 2, H - L.u(32), L.u(48), paint('#0F172A', 0.9))
                mv.text(c, C['outro'], W / 2, H - L.u(80), f, '#FFFFFF', align='center')


scene = Walkthrough()
tl = Timeline([scene], (W, H))
video = Video(tl, tl.duration, (W, H), FPS, background='#E8EEFF')


def soundtrack():
    m = sfx.Mixer(tl.duration)
    sfx.backing(m, bpm=100, key='C', mode='major', style='corporate', gain=0.6, fade_in=0.5, fade_out=2.5)
    for tc in (T['click_new'], T['create'], T['click_invite'], T['click_toggle']):
        m.add(sfx.click(), tc, 0.5)
    sfx.type_clicks(m, C['new_project'], T['type_at'], T['cps'], gain=0.2)
    sfx.type_clicks(m, C['invitee'], T['type2'], 18, gain=0.18)
    for t0 in (T['click_new'] + 0.2, T['create'] + 0.1, T['step2'] + 0.3, T['step3'] + 0.2, T['outro']):
        m.add(sfx.whoosh(0.5, 400, 3000), t0, 0.25)
    m.add(sfx.chime('success'), T['loaded'] + 0.2, 0.3, reverb=0.3)
    m.add(sfx.chime('notify'), T['sent'] + 0.3, 0.3, reverb=0.3)
    m.add(sfx.sparkle(), T['click_toggle'] + 0.2, 0.3, reverb=0.4)
    return m.master('ui_demo_audio.wav', lufs=-14)


if __name__ == '__main__':
    mv.cli(video, audio=soundtrack)
