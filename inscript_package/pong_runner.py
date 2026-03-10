#!/usr/bin/env python3
"""
pong_runner.py  —  Terminal Pong for InScript
Requires: pip install windows-curses   (Windows only)

Controls:
  W / S  — Left paddle up / down
  O / L  — Right paddle up / down
  Q      — Quit
  R      — Restart after game over
"""

import curses, time, sys

W = 60; H = 20; PADDLE_H = 4; MAX_SCORE = 7

def new_state():
    return {
        "ball":  {"x": W/2, "y": H/2, "vx": 1.0, "vy": 0.7},
        "left":  {"y": (H-PADDLE_H)/2, "score": 0},
        "right": {"y": (H-PADDLE_H)/2, "score": 0},
        "winner": 0, "ticks": 0,
    }

def update(gs, lu, ld, ru, rd):
    if gs["winner"]: return
    gs["ticks"] += 1
    P = 1.0
    L, R, B = gs["left"], gs["right"], gs["ball"]
    if lu: L["y"] = max(0.0,          L["y"] - P)
    if ld: L["y"] = min(H-PADDLE_H,   L["y"] + P)
    if ru: R["y"] = max(0.0,          R["y"] - P)
    if rd: R["y"] = min(H-PADDLE_H,   R["y"] + P)
    spd = min(1.0 + gs["ticks"] * 0.003, 2.5)
    B["x"] += B["vx"] * spd
    B["y"] += B["vy"] * spd
    if B["y"] <= 0:     B["y"] = 0;     B["vy"] =  abs(B["vy"])
    if B["y"] >= H-1:   B["y"] = H-1;   B["vy"] = -abs(B["vy"])
    bx, by = int(B["x"]), int(B["y"])
    if bx <= 2:
        if int(L["y"]) <= by <= int(L["y"]) + PADDLE_H:
            B["vx"] = abs(B["vx"]); B["x"] = 3.0
            hit = (B["y"]-L["y"])/PADDLE_H - 0.5
            B["vy"] = max(-3.0, min(3.0, B["vy"] + hit*1.5))
            gs["ticks"] = 0
    if bx >= W-3:
        if int(R["y"]) <= by <= int(R["y"]) + PADDLE_H:
            B["vx"] = -abs(B["vx"]); B["x"] = float(W-4)
            hit = (B["y"]-R["y"])/PADDLE_H - 0.5
            B["vy"] = max(-3.0, min(3.0, B["vy"] + hit*1.5))
            gs["ticks"] = 0
    if B["x"] < 0:
        R["score"] += 1
        if R["score"] >= MAX_SCORE: gs["winner"] = 2
        else: B.update({"x":W/2,"y":H/2,"vx":-1.0,"vy":0.7}); gs["ticks"]=0
    if B["x"] >= W:
        L["score"] += 1
        if L["score"] >= MAX_SCORE: gs["winner"] = 1
        else: B.update({"x":W/2,"y":H/2,"vx":1.0,"vy":0.7}); gs["ticks"]=0

def draw(scr, gs):
    scr.erase()
    mh, mw = scr.getmaxyx()
    oy = max(0, (mh-H-6)//2);  ox = max(0, (mw-W-2)//2)
    B = gs["ball"]; L = gs["left"]; R = gs["right"]
    BOLD = curses.A_BOLD; DIM = curses.A_DIM
    C1=curses.color_pair(1); C2=curses.color_pair(2); C3=curses.color_pair(3)
    def put(r, c, s, attr=0):
        try: scr.addstr(oy+r, ox+c, s, attr)
        except curses.error: pass
    put(0, W//2-4, "[ PONG ]", BOLD)
    put(1, W//2-8, f" {L['score']}  —  {R['score']} ", BOLD)
    TOP = 2
    put(TOP,   0, "╔"+"═"*W+"╗")
    put(TOP+H+1,0,"╚"+"═"*W+"╝")
    for r in range(1, H+1):
        put(TOP+r, 0, "║"); put(TOP+r, W+1, "║")
        if r%2==0: put(TOP+r, W//2+1, "┆", DIM)
    for i in range(PADDLE_H):
        row = int(L["y"])+i
        if 0<=row<H: put(TOP+row+1, 2, "██", C1|BOLD)
    for i in range(PADDLE_H):
        row = int(R["y"])+i
        if 0<=row<H: put(TOP+row+1, W-1, "██", C2|BOLD)
    bx, by = int(B["x"]), int(B["y"])
    if 0<=bx<W and 0<=by<H: put(TOP+by+1, bx+1, "●", C3|BOLD)
    if gs["winner"]:
        name = "LEFT" if gs["winner"]==1 else "RIGHT"
        m1 = f"  ★  {name} WINS!  ★  "
        m2 = "  R = restart   Q = quit  "
        put(TOP+H//2,   W//2+1-len(m1)//2, m1, C3|BOLD|curses.A_BLINK)
        put(TOP+H//2+1, W//2+1-len(m2)//2, m2, DIM)
    put(TOP+H+2, 2, " W/S: Left   O/L: Right   Q: Quit   R: Restart ", DIM)
    scr.refresh()

def main(scr):
    curses.curs_set(0); curses.start_color(); curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN,   -1)
    curses.init_pair(2, curses.COLOR_YELLOW, -1)
    curses.init_pair(3, curses.COLOR_GREEN,  -1)
    scr.nodelay(True)
    gs = new_state(); held = set(); FRAME = 1/30; last = time.time()
    while True:
        try: k = scr.getch()
        except: k = -1
        if k == -1: held.clear()
        else:
            if k in (ord('q'), ord('Q')): break
            if k in (ord('r'), ord('R')) and gs["winner"]: gs = new_state()
            held.add(k)
        now = time.time()
        if now - last >= FRAME:
            update(gs,
                   ord('w') in held or ord('W') in held,
                   ord('s') in held or ord('S') in held,
                   ord('o') in held or ord('O') in held,
                   ord('l') in held or ord('L') in held)
            last = now
        draw(scr, gs)
        time.sleep(0.005)

if __name__ == "__main__":
    print("InScript Terminal Pong")
    print("W/S = Left paddle   O/L = Right paddle   Q = Quit   R = Restart")
    print("Maximise your terminal for best display.")
    print("\nPress Enter to start...")
    try: input()
    except (EOFError, KeyboardInterrupt): sys.exit(0)
    curses.wrapper(main)
    print("Thanks for playing!")
