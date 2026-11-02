// Range Profile Structure backtester (port of the Lipi indicator logic, drawings removed)
window.RPS = (function () {
  function resample(bars, minutes) {
    const out = [];
    const ms = minutes * 60000;
    let cur = null;
    for (const b of bars) {
      const k = Math.floor(b.t / ms) * ms;
      if (!cur || cur.t !== k) {
        if (cur) out.push(cur);
        cur = { t: k, o: b.o, h: b.h, l: b.l, c: b.c, v: b.v };
      } else {
        cur.h = Math.max(cur.h, b.h);
        cur.l = Math.min(cur.l, b.l);
        cur.c = b.c;
        cur.v += b.v;
      }
    }
    if (cur) out.push(cur);
    return out;
  }

  function atrRma(bars, len) {
    const out = new Array(bars.length).fill(NaN);
    let sum = 0, prev = NaN;
    for (let i = 0; i < bars.length; i++) {
      const b = bars[i];
      const tr = i === 0 ? b.h - b.l : Math.max(b.h - b.l, Math.abs(b.h - bars[i - 1].c), Math.abs(b.l - bars[i - 1].c));
      if (i < len) {
        sum += tr;
        if (i === len - 1) { prev = sum / len; out[i] = prev; }
      } else {
        prev = (prev * (len - 1) + tr) / len;
        out[i] = prev;
      }
    }
    return out;
  }

  // Detection: returns signal events
  function detect(bars, p) {
    const L = p.swingLen, atr = atrRma(bars, p.atrLen);
    const sp = [], sb = [], ss = [];
    const events = [];
    let active = false, top = NaN, bot = NaN, left = 0, opened = 0, hT = 0, lT = 0;
    let upC = 0, dnC = 0, cooldown = 0, devDir = 0, devExt = NaN, devBar = 0, rangeId = 0;
    const minEvents = Math.max(p.minTouches * 2, p.minRotations + 1);
    for (let i = 0; i < bars.length; i++) {
      const b = bars[i];
      let hasPh = false, hasPl = false, ph = 0, pl = 0;
      if (i >= L * 2) {
        const ch = bars[i - L].h, cl = bars[i - L].l;
        let isH = true, isL = true;
        for (let k = 1; k <= L; k++) {
          if (bars[i - L - k].h >= ch) isH = false;
          if (bars[i - L + k].h > ch) isH = false;
          if (bars[i - L - k].l <= cl) isL = false;
          if (bars[i - L + k].l < cl) isL = false;
        }
        if (isH) { hasPh = true; ph = ch; }
        if (isL) { hasPl = true; pl = cl; }
      }
      const addSwing = (price, bi, side) => {
        if (sp.length > 0 && ss[0] === side) {
          const rep = side === 1 ? price >= sp[0] : price <= sp[0];
          if (rep) { sp[0] = price; sb[0] = bi; }
        } else { sp.unshift(price); sb.unshift(bi); ss.unshift(side); }
        while (sp.length > p.swingMemory) { sp.pop(); sb.pop(); ss.pop(); }
      };
      if (hasPh) addSwing(ph, i - L, 1);
      if (hasPl) addSwing(pl, i - L, -1);
      if (cooldown > 0) cooldown -= 1;
      const a = atr[i];
      if (!active && cooldown <= 0 && !isNaN(a)) {
        const n = sp.length, tol = a * p.clusterATR;
        let found = false, bT = 0, bB = 0, bL = 0, bH = 0, bLo = 0;
        if (n >= minEvents && a > 0) {
          for (let count = minEvents; count <= n; count++) {
            let hs = 0, ls = 0, hmin = 0, hmax = 0, lmin = 0, lmax = 0, hc = 0, lc = 0, oldest = i, newest = 0;
            for (let j = 0; j < count; j++) {
              const pr = sp[j], bi = sb[j];
              oldest = Math.min(oldest, bi); newest = Math.max(newest, bi);
              if (ss[j] === 1) { hs += pr; hc++; hmin = hc === 1 ? pr : Math.min(hmin, pr); hmax = hc === 1 ? pr : Math.max(hmax, pr); }
              else { ls += pr; lc++; lmin = lc === 1 ? pr : Math.min(lmin, pr); lmax = lc === 1 ? pr : Math.max(lmax, pr); }
            }
            if (hc >= p.minTouches && lc >= p.minTouches) {
              const t = hs / hc, bo = ls / lc, w = t - bo;
              const stable = hmax - hmin <= tol * 2 && lmax - lmin <= tol * 2;
              const wOK = w >= a * p.minWidthATR && w <= a * Math.max(p.maxWidthATR, p.minWidthATR);
              const spanOK = newest - oldest >= p.minRangeBars;
              const rotOK = count - 1 >= p.minRotations;
              if (t > bo && stable && wOK && spanOK && rotOK) { found = true; bT = t; bB = bo; bL = oldest; bH = hc; bLo = lc; }
            }
          }
        }
        if (found) {
          active = true; top = bT; bot = bB; left = Math.max(bL, i - 1500); opened = i; hT = bH; lT = bLo;
          upC = 0; dnC = 0; devDir = 0; devExt = NaN; rangeId++;
        }
      }
      if (active) {
        const tol = a * p.clusterATR;
        if (hasPh && i - L >= left && Math.abs(ph - top) <= tol) { top += (ph - top) * p.edgeAdapt; hT++; }
        if (hasPl && i - L >= left && Math.abs(pl - bot) <= tol) { bot += (pl - bot) * p.edgeAdapt; lT++; }
      }
      let brk = 0;
      if (active) {
        const buf = a * p.breakBuffer;
        const oUp = b.c > top + buf, oDn = b.c < bot - buf;
        upC = oUp ? upC + 1 : 0;
        dnC = oDn ? dnC + 1 : 0;
        if (devDir === 0) {
          if (oUp) { devDir = 1; devExt = b.h; devBar = i; }
          else if (oDn) { devDir = -1; devExt = b.l; devBar = i; }
        } else {
          if (devDir === 1 && b.h > devExt) { devExt = b.h; devBar = i; }
          if (devDir === -1 && b.l < devExt) { devExt = b.l; devBar = i; }
          if (b.c <= top && b.c >= bot) {
            events.push({ type: 'dev', i, dir: devDir, ext: devExt, top, bot, atr: a, rid: rangeId });
            devDir = 0; devExt = NaN;
          }
        }
        if (upC >= p.breakCloses) brk = 1;
        if (dnC >= p.breakCloses) brk = -1;
        if (p.maxRangeAge > 0 && i - opened >= p.maxRangeAge) brk = 2;
      }
      if (active && brk !== 0) {
        if (brk === 1 || brk === -1) events.push({ type: 'brk', i, dir: brk, top, bot, atr: a, rid: rangeId });
        active = false; sp.length = 0; sb.length = 0; ss.length = 0;
        upC = 0; dnC = 0; devDir = 0; devExt = NaN; cooldown = p.cooldownBars;
      }
    }
    return events;
  }

  // Precompute session info: index of last bar allowed before flat time (21:00 UTC) per bar
  function sessionInfo(bars, tfMin, flatUTCmin) {
    const n = bars.length, tfMs = tfMin * 60000;
    const exitIdx = new Int32Array(n);   // last bar index of this trading session (before flat time / gap)
    const minuteOfDay = new Int16Array(n);
    for (let i = 0; i < n; i++) {
      const d = new Date(bars[i].t);
      minuteOfDay[i] = d.getUTCHours() * 60 + d.getUTCMinutes();
    }
    // trading-day id: shift so day boundary is at flat time
    const dayId = new Float64Array(n);
    for (let i = 0; i < n; i++) dayId[i] = Math.floor((bars[i].t - flatUTCmin * 60000) / 86400000);
    let last = n - 1;
    for (let i = n - 1; i >= 0; i--) {
      if (i === n - 1 || dayId[i + 1] !== dayId[i] || bars[i + 1].t - bars[i].t > 3 * 3600000) last = i;
      exitIdx[i] = last;
    }
    // ensure bar that ends after flat time is not used: bars whose end > flat boundary belong to next day id already
    return { exitIdx, minuteOfDay, dayId, tfMs };
  }

  function inWindow(mod, w) {
    if (!w) return true;
    if (w[0] <= w[1]) return mod >= w[0] && mod < w[1];
    return mod >= w[0] || mod < w[1];
  }

  // Simulate trades for one variant over events. Returns array of trades.
  function simulate(bars, ev, si, v, cost) {
    const trades = [];
    let busyUntil = -1;
    for (const e of ev) {
      if (v.mode === 'BO' || v.mode === 'RT') { if (e.type !== 'brk') continue; }
      else if (v.mode === 'FADE') { if (e.type !== 'dev') continue; }
      if (v.dirFilter && v.dirFilter !== 0) {
        const tradeDir = v.mode === 'FADE' ? -e.dir : e.dir;
        if (tradeDir !== v.dirFilter) continue;
      }
      const sigI = e.i;
      if (sigI <= busyUntil) continue;
      const ent = sigI + 1;
      if (ent >= bars.length) break;
      if (si.exitIdx[sigI] !== si.exitIdx[ent]) continue; // next bar in a new session
      if (!inWindow(si.minuteOfDay[ent], v.window)) continue;
      const h = e.top - e.bot;
      let dir, entry, sl, tp, entI = ent;
      const lastI = si.exitIdx[ent];
      if (v.mode === 'BO') {
        dir = e.dir; entry = bars[ent].o;
        const edge = dir === 1 ? e.top : e.bot;
        if (v.sl === 'opp') sl = dir === 1 ? e.bot : e.top;
        else if (v.sl === 'mid') sl = (e.top + e.bot) / 2;
        else if (v.sl === 'edge') sl = edge - dir * e.atr * 0.5;
        tp = v.tpType === 'R' ? entry + dir * Math.abs(entry - sl) * v.tp : edge + dir * h * v.tp;
      } else if (v.mode === 'RT') {
        dir = e.dir; const edge = dir === 1 ? e.top : e.bot;
        entry = edge + dir * e.atr * (v.rtOff || 0);
        sl = v.sl === 'opp' ? (dir === 1 ? e.bot : e.top) : (e.top + e.bot) / 2;
        tp = v.tpType === 'R' ? entry + dir * Math.abs(entry - sl) * v.tp : edge + dir * h * v.tp;
        // wait for fill within rtBars, in same session
        entI = -1;
        for (let k = ent; k <= Math.min(lastI, ent + v.rtBars - 1); k++) {
          const bk = bars[k];
          if (dir === 1 ? bk.l <= entry : bk.h >= entry) {
            if (dir === 1 ? bk.o <= entry : bk.o >= entry) entry = bk.o; // gapped through
            entI = k; break;
          }
          if (dir === 1 ? bk.h >= tp : bk.l <= tp) break; // ran to target before retest -> cancel
        }
        if (entI < 0) { busyUntil = Math.min(lastI, ent + v.rtBars - 1); continue; }
      } else { // FADE
        dir = -e.dir; entry = bars[ent].o;
        sl = e.ext + e.dir * e.atr * v.slBuf;
        const mid = (e.top + e.bot) / 2;
        if (v.tpType === 'mid') tp = mid;
        else if (v.tpType === 'opp') tp = dir === 1 ? e.top : e.bot;
        else tp = entry + dir * Math.abs(entry - sl) * v.tp;
      }
      const risk = Math.abs(entry - sl);
      if (!(risk > 0)) continue;
      if (dir === 1 ? (sl >= entry || tp <= entry) : (sl <= entry || tp >= entry)) continue;
      let exitP = NaN, exitI = -1, why = '';
      let stop = sl, beDone = false;
      for (let k = entI; k <= lastI; k++) {
        const bk = bars[k];
        const hitSL = dir === 1 ? bk.l <= stop : bk.h >= stop;
        const hitTP = dir === 1 ? bk.h >= tp : bk.l <= tp;
        if (hitSL) { exitP = (dir === 1 ? Math.min(bk.o, stop) : Math.max(bk.o, stop)); if (k === entI && entI !== ent) exitP = stop; exitI = k; why = beDone ? 'BE' : 'SL'; break; }
        if (hitTP) { exitP = tp; exitI = k; why = 'TP'; break; }
        if (v.be && !beDone) {
          const fav = dir === 1 ? bk.h - entry : entry - bk.l;
          if (fav >= risk * v.be) { stop = entry; beDone = true; }
        }
      }
      if (exitI < 0) { exitI = lastI; exitP = bars[lastI].c; why = 'EOD'; }
      const pts = (exitP - entry) * dir - cost;
      trades.push({ i: entI, x: exitI, t: bars[entI].t, dir, entry, exitP, pts, r: pts / risk, why });
      busyUntil = exitI;
    }
    return trades;
  }

  function stats(tr) {
    let gp = 0, gl = 0, w = 0, eq = 0, pk = 0, dd = 0, eqR = 0, pkR = 0, ddR = 0, sumR = 0, ls = 0, mls = 0;
    for (const t of tr) {
      if (t.pts > 0) { gp += t.pts; w++; ls = 0; } else { gl -= t.pts; ls++; mls = Math.max(mls, ls); }
      eq += t.pts; pk = Math.max(pk, eq); dd = Math.max(dd, pk - eq);
      eqR += t.r; pkR = Math.max(pkR, eqR); ddR = Math.max(ddR, pkR - eqR); sumR += t.r;
    }
    const n = tr.length;
    return { n, wr: n ? w / n : 0, pf: gl > 0 ? gp / gl : (gp > 0 ? 99 : 0), net: eq, dd, netR: sumR, ddR, avgR: n ? sumR / n : 0, mls };
  }

  function variants() {
    const vs = [];
    const windows = [null, [7 * 60, 20 * 60]]; // all-day, or 12:30-01:30 IST
    for (const window of windows) {
      for (const dirFilter of [0]) {
        for (const sl of ['opp', 'mid', 'edge']) for (const tp of [0.5, 1, 1.5, 2]) for (const be of [0, 1])
          vs.push({ mode: 'BO', sl, tpType: 'H', tp, be, window, dirFilter });
        for (const sl of ['opp', 'mid', 'edge']) for (const tp of [1, 1.5, 2, 3])
          vs.push({ mode: 'BO', sl, tpType: 'R', tp, be: 0, window, dirFilter });
        for (const rtBars of [5, 15]) for (const sl of ['opp', 'mid']) for (const tp of [0.5, 1, 2]) for (const be of [0, 1])
          vs.push({ mode: 'RT', rtBars, rtOff: 0, sl, tpType: 'H', tp, be, window, dirFilter });
        for (const slBuf of [0.1, 0.3]) for (const tpType of ['mid', 'opp', 'R1', 'R2']) for (const be of [0, 1])
          vs.push({ mode: 'FADE', slBuf, tpType: tpType.startsWith('R') ? 'R' : tpType, tp: tpType === 'R1' ? 1 : 2, be, window, dirFilter });
      }
    }
    return vs;
  }

  function detGrid() {
    const g = [];
    for (const swingLen of [3, 5, 8]) for (const breakCloses of [1, 2, 3]) for (const breakBuffer of [0, 0.1, 0.25]) for (const clusterATR of [0.3, 0.5])
      g.push({ swingLen, swingMemory: 10, atrLen: 14, minTouches: 2, minRotations: 3, minRangeBars: 8, clusterATR, minWidthATR: 1.0, maxWidthATR: 6.0, edgeAdapt: 0.2, maxRangeAge: 0, breakBuffer, breakCloses, cooldownBars: 4 });
    return g;
  }

  function vkey(v) { return [v.mode, v.sl || '', v.slBuf || '', v.tpType, v.tp, v.rtBars || '', 'be' + v.be, v.window ? 'LNY' : 'ALL'].join('|'); }
  function dkey(p) { return `sw${p.swingLen}|bc${p.breakCloses}|bb${p.breakBuffer}|cl${p.clusterATR}`; }

  // Run full grid on bars; split at isFrac for in-sample/out-of-sample
  function runGrid(bars, tfMin, opts) {
    opts = opts || {};
    const cost = opts.cost != null ? opts.cost : 0.2;
    const isFrac = opts.isFrac || 0.7;
    const si = sessionInfo(bars, tfMin, 21 * 60);
    const splitT = bars[Math.floor(bars.length * isFrac)].t;
    const vs = variants();
    const rows = [];
    for (const p of detGrid()) {
      const ev = detect(bars, p);
      for (const v of vs) {
        const tr = simulate(bars, ev, si, v, cost);
        const all = stats(tr), is = stats(tr.filter(t => t.t < splitT)), oos = stats(tr.filter(t => t.t >= splitT));
        rows.push({ d: dkey(p), v: vkey(v), all, is, oos });
      }
    }
    return { rows, splitT, bars: bars.length, from: bars[0].t, to: bars[bars.length - 1].t };
  }

  return { resample, atrRma, detect, sessionInfo, simulate, stats, variants, detGrid, runGrid, vkey, dkey };
})();
