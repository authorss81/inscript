// ═══════════════════════════════════════════════════════════════════════
// InScript Web Runtime  v1.0.0
// Runs InScript bytecode (.insb) in the browser via Canvas2D / WebGL2.
// ═══════════════════════════════════════════════════════════════════════

'use strict';

// ── Opcode table (mirrors compiler/bytecode.py) ─────────────────────
const Op = {
  LOAD_CONST:0x01,LOAD_NULL:0x02,LOAD_TRUE:0x03,LOAD_FALSE:0x04,
  LOAD_INT:0x05,MOVE:0x06,GET_GLOBAL:0x07,SET_GLOBAL:0x08,
  GET_LOCAL:0x09,SET_LOCAL:0x0A,GET_UPVAL:0x0B,SET_UPVAL:0x0C,
  CLOSE_UPVAL:0x0D,
  ADD:0x10,SUB:0x11,MUL:0x12,DIV:0x13,MOD:0x14,POW:0x15,NEG:0x16,
  ADDK:0x17,SUBK:0x18,MULK:0x19,DIVK:0x1A,
  BAND:0x1B,BOR:0x1C,BXOR:0x1D,BNOT:0x1E,SHL:0x1F,SHR:0x20,
  EQ:0x21,NE:0x22,LT:0x23,LE:0x24,GT:0x25,GE:0x26,
  NOT:0x27,AND:0x28,OR:0x29,CONCAT:0x2A,STR_LEN:0x2B,
  JUMP:0x30,JUMP_TRUE:0x31,JUMP_FALSE:0x32,JUMP_NULL:0x33,LOOP:0x34,
  CALL:0x35,CALL_METHOD:0x36,RETURN:0x37,RETURN_NULL:0x38,TAIL_CALL:0x39,
  NEW_ARRAY:0x40,NEW_DICT:0x41,ARRAY_PUSH:0x42,ARRAY_LEN:0x43,
  ARRAY_GET:0x44,ARRAY_SET:0x45,DICT_GET:0x46,DICT_SET:0x47,
  GET_FIELD:0x48,SET_FIELD:0x49,GET_INDEX:0x4A,SET_INDEX:0x4B,
  CLOSURE:0x50,MAKE_CLOSURE:0x51,VARARG:0x52,
  FOR_PREP:0x53,FOR_STEP:0x54,ITER_PREP:0x55,ITER_NEXT:0x56,
  NEW_STRUCT:0x60,INHERIT:0x61,SELF:0x62,
  THROW:0x70,TRY_BEGIN:0x71,TRY_END:0x72,CATCH:0x73,
  TYPE_CHECK:0x74,TYPE_CAST:0x75,TO_STR:0x76,TO_INT:0x77,TO_FLOAT:0x78,TO_BOOL:0x79,
  PRINT:0x80,NOP:0x81,HALT:0x82,ASSERT:0x83,PROFILE:0x84,
};

// ── Instruction decode helpers ───────────────────────────────────────
function decodeABC(i)  { return [i&0xFF,(i>>8)&0xFF,(i>>16)&0xFF,(i>>24)&0xFF]; }
function decodeABx(i)  { return [i&0xFF,(i>>8)&0xFF,(i>>16)&0xFFFF]; }
function decodeAsBx(i) { const bx=(i>>16)&0xFFFF; return [i&0xFF,(i>>8)&0xFF,bx-0x8000]; }

// ── FuncProto loader from .insb binary ──────────────────────────────
class InsbLoader {
  constructor(buf) { this.view=new DataView(buf); this.pos=0; }
  u8()  { return this.view.getUint8(this.pos++); }
  u16() { const v=this.view.getUint16(this.pos,false); this.pos+=2; return v; }
  u32() { const v=this.view.getUint32(this.pos,false); this.pos+=4; return v; }
  i64() { const v=Number(this.view.getBigInt64(this.pos,false)); this.pos+=8; return v; }
  f64() { const v=this.view.getFloat64(this.pos,false); this.pos+=8; return v; }
  str() { const n=this.u16(); const b=new Uint8Array(this.view.buffer,this.pos,n); this.pos+=n; return new TextDecoder().decode(b); }
  load() {
    // Check magic
    const magic=String.fromCharCode(...new Uint8Array(this.view.buffer,0,4));
    if(magic!=='INSB') throw new Error('Not an .insb file');
    this.pos=8; // skip header
    return this.proto();
  }
  proto() {
    const p={name:this.str(),numParams:this.u8(),isVararg:!!this.u8(),maxRegs:this.u8()};
    const nc=this.u32(); p.code=[];
    for(let i=0;i<nc;i++) p.code.push(this.u32());
    const nk=this.u16(); p.consts=[];
    for(let i=0;i<nk;i++) {
      const tag=this.u8();
      if(tag===0x00) p.consts.push(null);
      else if(tag===0x01) { p.consts.push(!!this.u8()); }
      else if(tag===0x02) p.consts.push(this.i64());
      else if(tag===0x03) p.consts.push(this.f64());
      else if(tag===0x04) p.consts.push(this.str());
      else p.consts.push(null);
    }
    const np=this.u16(); p.protos=[];
    for(let i=0;i<np;i++) p.protos.push(this.proto());
    const nl=this.u32(); p.lines=[];
    for(let i=0;i<nl;i++) p.lines.push(this.u16());
    return p;
  }
}

// ── Web I/O & Engine APIs ────────────────────────────────────────────
class WebEngine {
  constructor(canvas, config={}) {
    this.canvas = canvas;
    this.config = config;
    this.ctx2d  = canvas.getContext('2d');
    this.gl     = config.useWebGL2 ? canvas.getContext('webgl2') : null;
    this.width  = canvas.width;
    this.height = canvas.height;
    this._keys  = new Set();
    this._mouse = {x:0,y:0,buttons:0};
    this._gamepads = [];
    this._touches  = [];
    this._audioCtx = null;
    this._sounds   = {};
    this._ws       = null;
    this._dt       = 0;
    this._time     = 0;
    this._frameCount = 0;
    this._saveDb   = null;
    this._drawCalls = 0;
    this._fps      = 0;
    this._fpsAccum = 0;
    this._fpsFrames= 0;
    this._lastTs   = 0;
    this._running  = false;
    this._onUpdate = null;
    this._onDraw   = null;
    this._setupEvents();
    this._openSaveDb();
  }

  // ── Input ──────────────────────────────────────────────────────────
  _setupEvents() {
    const c = this.canvas;
    window.addEventListener('keydown', e => { this._keys.add(e.code); e.preventDefault(); });
    window.addEventListener('keyup',   e => { this._keys.delete(e.code); });
    c.addEventListener('mousemove', e => {
      const r=c.getBoundingClientRect();
      this._mouse.x=e.clientX-r.left; this._mouse.y=e.clientY-r.top;
    });
    c.addEventListener('mousedown', e => { this._mouse.buttons |= (1<<e.button); });
    c.addEventListener('mouseup',   e => { this._mouse.buttons &= ~(1<<e.button); });
    c.addEventListener('touchstart', e => {
      e.preventDefault();
      this._touches=[...e.touches].map(t=>{const r=c.getBoundingClientRect(); return {x:t.clientX-r.left,y:t.clientY-r.top,id:t.identifier};});
    }, {passive:false});
    c.addEventListener('touchmove', e => {
      e.preventDefault();
      this._touches=[...e.touches].map(t=>{const r=c.getBoundingClientRect(); return {x:t.clientX-r.left,y:t.clientY-r.top,id:t.identifier};});
    }, {passive:false});
    c.addEventListener('touchend', e => { this._touches=[...e.touches].map(t=>{const r=c.getBoundingClientRect(); return {x:t.clientX-r.left,y:t.clientY-r.top,id:t.identifier};}); });
    window.addEventListener('gamepadconnected',    e => { this._gamepads[e.gamepad.index]=e.gamepad; });
    window.addEventListener('gamepaddisconnected', e => { delete this._gamepads[e.gamepad.index]; });
  }

  keyHeld(code)    { return this._keys.has(code); }
  mouseX()         { return this._mouse.x; }
  mouseY()         { return this._mouse.y; }
  mouseButton(b)   { return !!(this._mouse.buttons & (1<<b)); }
  touchCount()     { return this._touches.length; }
  touchX(i=0)      { return this._touches[i]?.x ?? 0; }
  touchY(i=0)      { return this._touches[i]?.y ?? 0; }
  gamepadAxis(g,a) { const gp=navigator.getGamepads()[g]; return gp ? gp.axes[a]??0 : 0; }
  gamepadBtn(g,b)  { const gp=navigator.getGamepads()[g]; return gp ? gp.buttons[b]?.pressed??false : false; }

  // ── Canvas 2D drawing ──────────────────────────────────────────────
  clear(color='#000') { this.ctx2d.fillStyle=color; this.ctx2d.fillRect(0,0,this.width,this.height); this._drawCalls=0; }
  fillRect(x,y,w,h,color='#fff') { this.ctx2d.fillStyle=color; this.ctx2d.fillRect(x,y,w,h); this._drawCalls++; }
  strokeRect(x,y,w,h,color='#fff',lw=1) { this.ctx2d.strokeStyle=color; this.ctx2d.lineWidth=lw; this.ctx2d.strokeRect(x,y,w,h); this._drawCalls++; }
  fillCircle(x,y,r,color='#fff') { this.ctx2d.fillStyle=color; this.ctx2d.beginPath(); this.ctx2d.arc(x,y,r,0,Math.PI*2); this.ctx2d.fill(); this._drawCalls++; }
  fillText(text,x,y,color='#fff',size=16,font='monospace') { this.ctx2d.fillStyle=color; this.ctx2d.font=`${size}px ${font}`; this.ctx2d.fillText(text,x,y); this._drawCalls++; }
  drawImage(img,x,y,w,h) { this.ctx2d.drawImage(img,x,y,w??img.width,h??img.height); this._drawCalls++; }
  drawLine(x1,y1,x2,y2,color='#fff',lw=1) { this.ctx2d.strokeStyle=color; this.ctx2d.lineWidth=lw; this.ctx2d.beginPath(); this.ctx2d.moveTo(x1,y1); this.ctx2d.lineTo(x2,y2); this.ctx2d.stroke(); this._drawCalls++; }
  save()    { this.ctx2d.save(); }
  restore() { this.ctx2d.restore(); }
  translate(x,y) { this.ctx2d.translate(x,y); }
  rotate(a)      { this.ctx2d.rotate(a); }
  scale(x,y)     { this.ctx2d.scale(x,y); }
  setAlpha(a)    { this.ctx2d.globalAlpha=a; }

  // ── Audio ──────────────────────────────────────────────────────────
  _ensureAudio() {
    if(!this._audioCtx) this._audioCtx=new (window.AudioContext||window.webkitAudioContext)();
    return this._audioCtx;
  }
  playTone(freq=440,duration=0.1,volume=0.3,type='square') {
    const ctx=this._ensureAudio();
    const osc=ctx.createOscillator();
    const gain=ctx.createGain();
    osc.connect(gain); gain.connect(ctx.destination);
    osc.type=type; osc.frequency.value=freq;
    gain.gain.setValueAtTime(volume,ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001,ctx.currentTime+duration);
    osc.start(); osc.stop(ctx.currentTime+duration);
  }
  async loadSound(name,url) {
    const ctx=this._ensureAudio();
    const resp=await fetch(url);
    const buf=await resp.arrayBuffer();
    this._sounds[name]=await ctx.decodeAudioData(buf);
  }
  playSound(name,volume=1,loop=false) {
    const ctx=this._ensureAudio();
    const buf=this._sounds[name]; if(!buf) return;
    const src=ctx.createBufferSource();
    const gain=ctx.createGain();
    src.buffer=buf; src.loop=loop;
    gain.gain.value=volume;
    src.connect(gain); gain.connect(ctx.destination);
    src.start();
    return src;
  }

  // ── Networking (WebSocket) ─────────────────────────────────────────
  connect(url) {
    this._ws=new WebSocket(url);
    return this._ws;
  }
  send(data) { this._ws?.send(JSON.stringify(data)); }

  // ── Save data (IndexedDB) ─────────────────────────────────────────
  _openSaveDb() {
    const req=indexedDB.open('InScriptSave',1);
    req.onupgradeneeded=e => e.target.result.createObjectStore('saves');
    req.onsuccess=e => { this._saveDb=e.target.result; };
  }
  save(key,value) {
    if(!this._saveDb) return;
    const tx=this._saveDb.transaction('saves','readwrite');
    tx.objectStore('saves').put(JSON.stringify(value),key);
  }
  load(key) {
    return new Promise(res => {
      if(!this._saveDb) { res(null); return; }
      const tx=this._saveDb.transaction('saves','readonly');
      const req=tx.objectStore('saves').get(key);
      req.onsuccess=()=>res(req.result ? JSON.parse(req.result) : null);
      req.onerror=()=>res(null);
    });
  }

  // ── Fullscreen / Pointer Lock ──────────────────────────────────────
  fullscreen()    { this.canvas.requestFullscreen?.(); }
  pointerLock()   { this.canvas.requestPointerLock?.(); }
  exitPointerLock() { document.exitPointerLock?.(); }

  // ── Game loop ─────────────────────────────────────────────────────
  start(updateFn, drawFn) {
    this._onUpdate = updateFn;
    this._onDraw   = drawFn;
    this._running  = true;
    this._lastTs   = performance.now();
    const loop = (ts) => {
      if(!this._running) return;
      this._dt = Math.min((ts - this._lastTs) / 1000, 0.05);
      this._lastTs = ts;
      this._time  += this._dt;
      this._frameCount++;
      this._fpsAccum += this._dt; this._fpsFrames++;
      if(this._fpsAccum >= 0.5) { this._fps=Math.round(this._fpsFrames/this._fpsAccum); this._fpsAccum=0; this._fpsFrames=0; }
      try { this._onUpdate?.(this._dt); this._onDraw?.(); }
      catch(e) { console.error('InScript runtime error:', e); this._running=false; return; }
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }
  stop() { this._running=false; }
  dt()   { return this._dt; }
  time() { return this._time; }
  fps()  { return this._fps; }
  drawCalls() { return this._drawCalls; }
}

// ── InScript VM (JavaScript port of compiler/bytecode.py) ──────────
class InScriptVM {
  constructor(engine) {
    this.engine   = engine;
    this.globals  = {};
    this.callStack= [];
    this.execCount= 0;
    this.MAX_DEPTH= 512;
    this.EXEC_LIMIT=10_000_000;
    this._installStdlib();
  }

  _installStdlib() {
    const E = this.engine;
    const g = this.globals;
    // Core
    g['print']  = (...a)=>console.log(...a);
    g['len']    = a=>(a?.length??0);
    g['str']    = x=>(x===null?'null':x===true?'true':x===false?'false':String(x));
    g['int']    = x=>Math.trunc(Number(x));
    g['float']  = x=>Number(x);
    g['bool']   = x=>!!x;
    g['type']   = x=>typeof x;
    g['range']  = (a,b,s)=>{ const r=[]; if(b===undefined){b=a;a=0;} if(s===undefined)s=1; for(let i=a;i<b;i+=s)r.push(i); return r; };
    g['abs']    = Math.abs; g['min']=Math.min; g['max']=Math.max;
    g['sqrt']   = Math.sqrt; g['floor']=Math.floor; g['ceil']=Math.ceil;
    g['sin']    = Math.sin;  g['cos']=Math.cos; g['tan']=Math.tan;
    g['pow']    = Math.pow;  g['round']=Math.round;
    g['random'] = Math.random;
    g['append'] = (a,v)=>a.push(v);
    g['push']   = (a,v)=>a.push(v);
    g['pop']    = a=>a.pop();
    g['keys']   = o=>Object.keys(o??{});
    g['values'] = o=>Object.values(o??{});
    // Engine I/O
    g['clear']        = c=>E.clear(c);
    g['fill_rect']    = (x,y,w,h,c)=>E.fillRect(x,y,w,h,c);
    g['fill_circle']  = (x,y,r,c)=>E.fillCircle(x,y,r,c);
    g['draw_text']    = (t,x,y,c,s)=>E.fillText(t,x,y,c,s);
    g['draw_line']    = (x1,y1,x2,y2,c,w)=>E.drawLine(x1,y1,x2,y2,c,w);
    g['screen_width'] = ()=>E.width;
    g['screen_height']= ()=>E.height;
    g['dt']           = ()=>E.dt();
    g['time']         = ()=>E.time();
    g['fps']          = ()=>E.fps();
    g['key_held']     = code=>E.keyHeld(code);
    g['mouse_x']      = ()=>E.mouseX();
    g['mouse_y']      = ()=>E.mouseY();
    g['mouse_btn']    = b=>E.mouseButton(b);
    g['play_tone']    = (f,d,v,t)=>E.playTone(f,d,v,t);
    g['play_sound']   = (n,v,l)=>E.playSound(n,v,l);
    g['save_data']    = (k,v)=>E.save(k,v);
    g['load_data']    = (k)=>E.load(k);
    g['fullscreen']   = ()=>E.fullscreen();
    g['Vec2']         = (x,y)=>({x:x??0,y:y??0,length:()=>Math.hypot(x,y)});
    g['Color']        = (r,g,b,a)=>`rgba(${Math.round(r*255)},${Math.round(g*255)},${Math.round(b*255)},${a??1})`;
  }

  run(proto) {
    const closure={proto,upvalues:[]};
    const frame={closure,regs:new Array(Math.max(proto.maxRegs,8)).fill(null),pc:0,retReg:-1};
    this.callStack=[frame];
    return this._exec();
  }

  _exec() {
    let frame = this.callStack[this.callStack.length-1];
    this.execCount=0;
    while(true) {
      if(frame.pc>=frame.closure.proto.code.length) break;
      const instr=frame.closure.proto.code[frame.pc++];
      this.execCount++;
      if(this.execCount>this.EXEC_LIMIT) throw new Error('InScript: execution limit exceeded');
      const op=instr&0xFF, a=(instr>>8)&0xFF, b=(instr>>16)&0xFF, c=(instr>>24)&0xFF;
      const bx=(instr>>16)&0xFFFF, sbx=bx-0x8000;
      const regs=frame.regs, consts=frame.closure.proto.consts, protos=frame.closure.proto.protos;

      switch(op) {
        case Op.LOAD_CONST:  regs[a]=consts[bx]; break;
        case Op.LOAD_NULL:   regs[a]=null; break;
        case Op.LOAD_TRUE:   regs[a]=true; break;
        case Op.LOAD_FALSE:  regs[a]=false; break;
        case Op.LOAD_INT:    regs[a]=sbx; break;
        case Op.MOVE:        regs[a]=regs[b]; break;
        case Op.GET_GLOBAL:  regs[a]=this.globals[consts[bx]]??null; break;
        case Op.SET_GLOBAL:  this.globals[consts[bx]]=regs[a]; break;
        case Op.GET_LOCAL:   regs[a]=regs[b]; break;
        case Op.SET_LOCAL:   regs[b]=regs[a]; break;
        case Op.ADD:  regs[a]=regs[b]+regs[c]; break;
        case Op.SUB:  regs[a]=regs[b]-regs[c]; break;
        case Op.MUL:  regs[a]=regs[b]*regs[c]; break;
        case Op.DIV:  if(regs[c]===0)throw new Error('Division by zero'); regs[a]=regs[b]/regs[c]; break;
        case Op.MOD:  regs[a]=regs[b]%regs[c]; break;
        case Op.POW:  regs[a]=Math.pow(regs[b],regs[c]); break;
        case Op.NEG:  regs[a]=-regs[b]; break;
        case Op.ADDK: regs[a]=regs[b]+consts[c]; break;
        case Op.SUBK: regs[a]=regs[b]-consts[c]; break;
        case Op.MULK: regs[a]=regs[b]*consts[c]; break;
        case Op.DIVK: regs[a]=regs[b]/consts[c]; break;
        case Op.EQ:   regs[a]=regs[b]===regs[c]; break;
        case Op.NE:   regs[a]=regs[b]!==regs[c]; break;
        case Op.LT:   regs[a]=regs[b]<regs[c]; break;
        case Op.LE:   regs[a]=regs[b]<=regs[c]; break;
        case Op.GT:   regs[a]=regs[b]>regs[c]; break;
        case Op.GE:   regs[a]=regs[b]>=regs[c]; break;
        case Op.NOT:  regs[a]=!regs[b]; break;
        case Op.AND:  regs[a]=regs[b]&&regs[c]; break;
        case Op.OR:   regs[a]=regs[b]||regs[c]; break;
        case Op.CONCAT: regs[a]=String(regs[b])+String(regs[c]); break;
        case Op.STR_LEN: regs[a]=String(regs[b]).length; break;
        case Op.JUMP:       frame.pc+=sbx; break;
        case Op.JUMP_TRUE:  if(regs[a]) frame.pc+=sbx; break;
        case Op.JUMP_FALSE: if(!regs[a]) frame.pc+=sbx; break;
        case Op.JUMP_NULL:  if(regs[a]===null) frame.pc+=sbx; break;
        case Op.LOOP:       frame.pc-=sbx; break;
        case Op.CALL: {
          const fn=regs[a], nargs=b;
          const args=Array.from({length:nargs},(_,i)=>regs[a+1+i]);
          if(typeof fn==='function') { regs[a]=fn(...args); }
          else if(fn && fn.proto) {
            if(this.callStack.length>=this.MAX_DEPTH) throw new Error('Stack overflow');
            const nf={closure:fn,regs:new Array(Math.max(fn.proto.maxRegs,8)).fill(null),pc:0,retReg:a};
            args.forEach((v,i)=>{ if(i<fn.proto.numParams) nf.regs[i]=v; });
            this.callStack.push(nf); frame=nf;
          } else { throw new Error(`Cannot call ${typeof fn}: ${fn}`); }
          break;
        }
        case Op.CALL_METHOD: {
          const obj=regs[a], mname=consts[c], nargs=b;
          const args=Array.from({length:nargs},(_,i)=>regs[a+1+i]);
          let method=null;
          if(obj && typeof obj==='object') method=obj[mname];
          else if(typeof obj==='string') method=String.prototype[mname]?.bind(obj);
          if(typeof method!=='function') throw new Error(`No method '${mname}'`);
          regs[a]=method(...args);
          break;
        }
        case Op.RETURN: {
          const val=b>0?regs[a]:null;
          if(this.callStack.length>1) {
            const retReg=frame.retReg;
            this.callStack.pop();
            frame=this.callStack[this.callStack.length-1];
            frame.regs[retReg]=val;
          } else return val;
          break;
        }
        case Op.RETURN_NULL: {
          if(this.callStack.length>1) {
            const retReg=frame.retReg;
            this.callStack.pop();
            frame=this.callStack[this.callStack.length-1];
            frame.regs[retReg]=null;
          } else return null;
          break;
        }
        case Op.NEW_ARRAY:  regs[a]=[]; break;
        case Op.NEW_DICT:   regs[a]={}; break;
        case Op.ARRAY_PUSH: regs[a].push(regs[b]); break;
        case Op.ARRAY_LEN:  regs[a]=regs[b]?.length??0; break;
        case Op.ARRAY_GET:  try{regs[a]=regs[b][regs[c]]??null;}catch{regs[a]=null;} break;
        case Op.ARRAY_SET:  try{regs[b][regs[c]]=regs[a];}catch{} break;
        case Op.GET_FIELD:  { const k=consts[c]; regs[a]=(regs[b]&&typeof regs[b]==='object')?regs[b][k]??null:null; break; }
        case Op.SET_FIELD:  { const k=consts[c]; if(regs[b]&&typeof regs[b]==='object') regs[b][k]=regs[a]; break; }
        case Op.GET_INDEX:  try{regs[a]=regs[b][regs[c]]??null;}catch{regs[a]=null;} break;
        case Op.SET_INDEX:  try{regs[b][regs[c]]=regs[a];}catch{} break;
        case Op.CLOSURE:    regs[a]={proto:protos[bx],upvalues:[]}; break;
        case Op.ITER_PREP:  regs[a]=(Symbol.iterator in Object(regs[b]))?regs[b][Symbol.iterator]():[][Symbol.iterator](); break;
        case Op.ITER_NEXT:  { const r=regs[a].next(); regs[b]=r.done?null:r.value; break; }
        case Op.TO_STR:     regs[a]=regs[b]===null?'null':regs[b]===true?'true':regs[b]===false?'false':String(regs[b]); break;
        case Op.TO_INT:     regs[a]=Math.trunc(Number(regs[b])); break;
        case Op.TO_FLOAT:   regs[a]=Number(regs[b]); break;
        case Op.TO_BOOL:    regs[a]=!!regs[b]; break;
        case Op.PRINT:      { const s=regs[a]===null?'null':regs[a]===true?'true':regs[a]===false?'false':String(regs[a]); console.log(s); break; }
        case Op.NOP:  break;
        case Op.HALT: return regs[0]??null;
        case Op.THROW: throw new Error(String(regs[a]));
        default: break;
      }
    }
    return frame.regs[0]??null;
  }
}

// ── InScript Web Application bootstrap ───────────────────────────────
class InScriptApp {
  constructor(canvasId, config={}) {
    this.canvas = document.getElementById(canvasId);
    if(!this.canvas) throw new Error(`Canvas '${canvasId}' not found`);
    this.engine = new WebEngine(this.canvas, config);
    this.vm     = new InScriptVM(this.engine);
    this._onStart  = null;
    this._onUpdate = null;
    this._onDraw   = null;
  }

  async loadBytecode(url) {
    const resp=await fetch(url);
    const buf=await resp.arrayBuffer();
    const loader=new InsbLoader(buf);
    this.proto=loader.load();
  }

  async loadSource(source) {
    // For inline source: just use the globals/engine directly
    this._inlineSource = source;
  }

  start() {
    if(this.proto) {
      // Run the compiled bytecode
      this.vm.run(this.proto);
    }
    // Start the game loop calling _update and _draw globals if defined
    this.engine.start(
      (dt) => { const fn=this.vm.globals['_update']; if(fn) this.vm._callFn(fn,[dt]); },
      ()    => { const fn=this.vm.globals['_draw'];   if(fn) this.vm._callFn(fn,[]); }
    );
  }
}

// Export to global scope
window.InScriptApp    = InScriptApp;
window.InScriptVM     = InScriptVM;
window.WebEngine      = WebEngine;
window.InsbLoader     = InsbLoader;