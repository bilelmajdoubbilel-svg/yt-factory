/* drip.js — Hidden Systems runtime: Drip's rig, the "follow the drop" camera, the pipe-iris transition,
   gauges and spinning parts. Every frame is a closed-form function of timeline time (seeded, no clocks),
   so any frame renders on its own. Loaded after gsap.min.js; uses the same pattern as cinema.js
   (one clock tween per driver, state applied in onUpdate). */
(function () {
  function rnd(seed) { // mulberry32
    return function () {
      seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
      var t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function io(u) { u = clamp(u, 0, 1); return u < .5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2; }
  function backOut(u) { u = clamp(u, 0, 1); var c1 = 2.0, c3 = c1 + 1; return 1 + c3 * Math.pow(u - 1, 3) + c1 * Math.pow(u - 1, 2); }
  function q(id, part) { return document.getElementById(id + "-" + part); }
  function clock(tl, dur, fn) {
    var c = { t: 0 };
    tl.fromTo(c, { t: 0 }, { t: dur, duration: dur, ease: "none", onUpdate: function () { fn(c.t); } }, 0);
    fn(0);
  }
  // eased keyed value: keys [[t, v], ...]; each key eases from the previous value over d seconds
  function keyed(keys, t, d, v0) {
    var prev = v0, v = v0;
    for (var i = 0; i < keys.length; i++) {
      var k = keys[i];
      if (t < k[0]) break;
      v = prev + (k[1] - prev) * io((t - k[0]) / d);
      prev = k[1];
    }
    return v;
  }

  var EXPRS = { happy: ["base", "smile"], neutral: ["neutral", "rest"], surprised: ["wide", "o"], thinking: ["think", "flat"],
                worried: ["worried", "frown"], proud: ["squint", "smile"] };
  var EYES = ["base", "neutral", "wide", "think", "worried", "squint"];
  var MOUTHS = ["smile", "rest", "o", "flat", "frown", "a", "e", "wide"];

  /* ---------------- Drip's rig ----------------
     cfg: {seed, expr, flip, takes:[[t, expr, amp]], exprs:[[t, expr]], look:[[t, dx, dy]], lean:[[t, deg]],
           arms:{R:[[t, scale, angle]], L:[...]}, hops:[t], mouth:[[t, shape|""]]}
     A take: anticipation squash, stretch while the hat pops, new face at the peak, elastic settle,
     the hat lands last with a small bob. */
  function rig(tl, id, dur, cfg) {
    cfg = cfg || {};
    var r = rnd(cfg.seed || 5), blinks = [], tb = .7 + r() * 1.3;
    while (tb < dur) { blinks.push(tb); tb += 2.1 + r() * 2.7; }
    var el = { root: q(id, "root"), bod: q(id, "bod"), hat: q(id, "hat"), face: q(id, "face"), eyes: q(id, "eyes"),
               armR: q(id, "armR"), armL: q(id, "armL") };
    var eyeEl = {}, browEl = {}, mouthEl = {};
    EYES.forEach(function (n) { eyeEl[n] = q(id, "eyes-" + n); browEl[n] = q(id, "brows-" + n); });
    MOUTHS.forEach(function (n) { mouthEl[n] = q(id, "m-" + n); });
    var takes = cfg.takes || [], faces = [];
    takes.forEach(function (k) { faces.push([k[0] + .1, k[1]]); });
    (cfg.exprs || []).forEach(function (k) { faces.push([k[0], k[1]]); });
    faces.sort(function (a, b) { return a[0] - b[0]; });
    var mouth = cfg.mouth || [], hops = cfg.hops || [], flip = cfg.flip ? -1 : 1, ph = (cfg.seed || 5) * .37;
    var lastE = null, lastM = null;
    function setOp(map, on) { for (var k in map) if (map[k]) map[k].setAttribute("opacity", k === on ? 1 : 0); }

    function apply(t) {
      // expression
      var expr = cfg.expr || "happy";
      for (var i = 0; i < faces.length && faces[i][0] <= t; i++) expr = faces[i][1];
      var E = EXPRS[expr] || EXPRS.happy;
      // take envelope (latest take)
      var sx = 1, sy = 1, hatY = 0, hatR = 0;
      for (var j = takes.length - 1; j >= 0; j--) {
        var u = t - takes[j][0];
        if (u < 0) continue;
        if (u > 2.2) break;
        var A = takes[j][2] == null ? 1 : takes[j][2], dir = (j % 2 ? -1 : 1);
        if (u < .09) { var k0 = io(u / .09); sy = 1 - .1 * A * k0; sx = 1 + .07 * A * k0; }
        else if (u < .21) { var k1 = io((u - .09) / .12); sy = 1 - .1 * A + .22 * A * k1; sx = 1 + .07 * A - .14 * A * k1; }
        else { var v = u - .21, dmp = Math.exp(-5.5 * v) * Math.cos(13 * v); sy = 1 + .12 * A * dmp; sx = 1 - .07 * A * dmp; }
        if (u >= .09) {
          var w = u - .09;
          if (w < .38) hatY = -36 * A * Math.sin(Math.PI * w / .38);
          else hatY = -7 * A * Math.exp(-7 * (w - .38)) * Math.abs(Math.sin(15 * (w - .38)));
          hatR = 11 * A * dir * Math.exp(-3.5 * w) * Math.sin(11 * w);
        }
        break;
      }
      // breath + idle sway
      var br = Math.sin(2 * Math.PI * t / 3.1 + ph);
      sy *= 1 + .014 * br; sx *= 1 - .007 * br;
      hatY += -1.2 * Math.sin(2 * Math.PI * (t - .15) / 3.1 + ph);
      var lean = keyed(cfg.lean || [], t, .35, 0) + .9 * Math.sin(t * .9 + ph);
      // hops
      var hopY = 0;
      hops.forEach(function (h) {
        var u = t - h;
        if (u >= 0 && u < .42) hopY = -46 * Math.sin(Math.PI * u / .42);
        else if (u >= .42 && u < .62) { hopY = -7 * Math.sin(Math.PI * (u - .42) / .2); }
        if (u >= .4 && u < .52) { var s2 = Math.sin(Math.PI * (u - .4) / .12); sy *= 1 - .08 * s2; sx *= 1 + .05 * s2; }
      });
      // look
      var lx = keyed((cfg.look || []).map(function (k) { return [k[0], k[1]]; }), t, .3, 0);
      var ly = keyed((cfg.look || []).map(function (k) { return [k[0], k[2] || 0]; }), t, .3, 0);
      // blink
      var b = 1;
      for (var n = 0; n < blinks.length; n++) {
        var ub = (t - blinks[n]) / .16;
        if (ub >= 0 && ub <= 1) { b = 1 - .92 * (ub < .4 ? ub / .4 : (1 - ub) / .6); break; }
      }
      // arms
      ["R", "L"].forEach(function (s) {
        var keys = (cfg.arms || {})[s] || [], a = el["arm" + s];
        if (!a) return;
        var sc = 0, ang = 0, prevS = 0, prevA = 0;
        for (var i = 0; i < keys.length; i++) {
          var k = keys[i];
          if (t < k[0]) break;
          var u = (t - k[0]) / .3;
          sc = prevS + (k[1] - prevS) * (k[1] > prevS ? backOut(u) : io(u));
          ang = prevA + ((k[2] == null ? prevA : k[2]) - prevA) * io(u);
          prevS = k[1]; prevA = k[2] == null ? prevA : k[2];
        }
        ang += sc > .05 ? 3 * Math.sin(t * 5.3 + (s === "R" ? 0 : 1.7)) : 0;
        a.setAttribute("transform", "translate(" + (s === "R" ? 80 : -80) + " 28) rotate(" + ang.toFixed(2) + ") scale(" + Math.max(0, sc).toFixed(3) + ")");
      });
      // mouth: lip-sync keys override the expression's mouth
      var m = E[1];
      if (mouth.length) {
        var lo = 0, hi = mouth.length - 1, idx = -1;
        while (lo <= hi) { var mid = (lo + hi) >> 1; if (mouth[mid][0] <= t) { idx = mid; lo = mid + 1; } else hi = mid - 1; }
        if (idx >= 0 && mouth[idx][1]) m = mouth[idx][1];
      }
      el.root.setAttribute("transform", (flip < 0 ? "scale(-1 1) " : "") + "translate(0 " + hopY.toFixed(2) + ") rotate(" + lean.toFixed(2) + " 0 100)");
      el.bod.setAttribute("transform", "translate(0 100) scale(" + sx.toFixed(4) + " " + sy.toFixed(4) + ") translate(0 -100)");
      el.hat.setAttribute("transform", "translate(0 " + hatY.toFixed(2) + ") rotate(" + hatR.toFixed(2) + " 0 -52) translate(0 -52) scale(" +
                          (1 / sx).toFixed(4) + " " + (1 / sy).toFixed(4) + ") translate(0 52)");
      el.face.setAttribute("transform", "translate(" + lx.toFixed(2) + " " + ly.toFixed(2) + ")");
      el.eyes.setAttribute("transform", "translate(0 -0.25) scale(1 " + b.toFixed(3) + ") translate(0 0.25)");
      if (E[0] !== lastE) { setOp(eyeEl, E[0]); setOp(browEl, E[0]); lastE = E[0]; }
      if (m !== lastM) { setOp(mouthEl, m); lastM = m; }
    }
    clock(tl, dur, apply);
  }

  /* ---------------- follow the drop ----------------
     cfg: {W, H, g0, path:[[x,y]...], len, keys:[[gt, d, ease]], lag, mix, anchor:[ax, ay], c0:[x,y],
           zoom:[[gt, z]], lead:[[gt, dx, dy]], layers:[{sel, p}], spark, trail:[sel], lit, litLen, spin:[[sel, rps]],
           belt:[[sel, pxps]] }
     gt = global (film) time, so the motion runs on unbroken across scene cuts. */
  function follow(tl, sid, cfg, dur) {
    var P = cfg.path, n = P.length, acc = [0];
    for (var i = 1; i < n; i++) acc.push(acc[i - 1] + Math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]));
    var L = acc[n - 1];
    function at(d) {
      d = clamp(d, 0, L);
      var lo = 0, hi = n - 1;
      while (hi - lo > 1) { var m = (lo + hi) >> 1; if (acc[m] <= d) lo = m; else hi = m; }
      var seg = acc[hi] - acc[lo] || 1, f = (d - acc[lo]) / seg;
      return [P[lo][0] + (P[hi][0] - P[lo][0]) * f, P[lo][1] + (P[hi][1] - P[lo][1]) * f];
    }
    var K = cfg.keys;
    function dist(gt) {
      if (gt <= K[0][0]) return K[0][1];
      for (var i = 1; i < K.length; i++) {
        if (gt <= K[i][0]) {
          var u = (gt - K[i - 1][0]) / (K[i][0] - K[i - 1][0]), e = K[i][2] || "linear";
          var f = e === "in" ? u * u : e === "out" ? 1 - (1 - u) * (1 - u) : e === "inout" ? io(u) : u;
          return K[i - 1][1] + (K[i][1] - K[i - 1][1]) * f;
        }
      }
      return K[K.length - 1][1];
    }
    function kv(keys, gt, d, v0, idx) {
      return keyed(keys.map(function (k) { return [k[0], k[idx]]; }), gt, d, v0);
    }
    var layers = cfg.layers.map(function (L) { return { el: document.querySelector(L.sel), p: L.p }; });
    var spark = cfg.spark && document.querySelector(cfg.spark);
    var trail = (cfg.trail || []).map(function (s) { return document.querySelector(s); });
    var lit = cfg.lit && document.querySelector(cfg.lit);
    var spins = (cfg.spin || []).map(function (s) { return [document.querySelectorAll(s[0]), s[1]]; });
    var flows = (cfg.flow || []).map(function (s) { return [document.querySelectorAll(s[0]), s[1]]; });
    var a = cfg.anchor, c0 = cfg.c0 || [0, 1000], lag = cfg.lag == null ? .2 : cfg.lag, mix = cfg.mix == null ? .45 : cfg.mix;
    function apply(t) {
      var gt = cfg.g0 + t, d = dist(gt), p = at(d), pl = at(dist(gt - lag));
      var z = kv(cfg.zoom || [[0, 1]], gt, .9, (cfg.zoom || [[0, 1]])[0][1], 1);
      var ldx = kv(cfg.lead || [[0, 0, 0]], gt, .9, (cfg.lead || [[0, 0, 0]])[0][1], 1);
      var ldy = kv(cfg.lead || [[0, 0, 0]], gt, .9, (cfg.lead || [[0, 0, 0]])[0][2], 2);
      var hx = 3 * Math.sin(gt * .83 + 1.3) + 1.5 * Math.sin(gt * 2.1), hy = 2.4 * Math.sin(gt * .67 + 2.1) + 1.2 * Math.sin(gt * 1.9 + 3.3);
      var cx = pl[0] * (1 - mix) + p[0] * mix + ldx + hx, cy = pl[1] * (1 - mix) + p[1] * mix + ldy + hy;
      layers.forEach(function (L) {
        if (!L.el) return;
        var zl = 1 + (z - 1) * Math.min(1, L.p);
        var ox = c0[0] + (cx - c0[0]) * L.p, oy = c0[1] + (cy - c0[1]) * L.p;
        gsap.set(L.el, { x: a[0] - ox * zl, y: a[1] - oy * zl, scale: zl, transformOrigin: "0 0" });
      });
      if (spark) {
        var jit = 1 + .08 * Math.sin(gt * 37) + .05 * Math.sin(gt * 23 + 1);
        gsap.set(spark, { x: p[0], y: p[1], scale: jit });
      }
      var sp = Math.min(1, Math.abs(d - dist(gt - .06)) / 8);   // trail only while moving
      trail.forEach(function (el, k) {
        var q2 = at(d - (k + 1) * 26);
        gsap.set(el, { x: q2[0], y: q2[1], opacity: d > (k + 1) * 26 ? (.7 - k * .1) * sp : 0 });
      });
      if (lit) {
        var seg = Math.min(cfg.litLen || 700, d);
        lit.setAttribute("stroke-dasharray", seg.toFixed(1) + " " + (L * 3).toFixed(0));
        lit.setAttribute("stroke-dashoffset", (-(d - seg)).toFixed(1));
      }
      spins.forEach(function (s) { s[0].forEach(function (e) { e.setAttribute("transform", "rotate(" + ((gt * s[1] * 360) % 360).toFixed(1) + ")"); }); });
      flows.forEach(function (s) { s[0].forEach(function (e) { e.setAttribute("stroke-dashoffset", (-(gt * s[1]) % 4000).toFixed(1)); }); });
    }
    clock(tl, dur, apply);
  }

  /* ---------------- pipe iris ----------------
     mode "close": the pipe mouth at (x, y) grows until its dark bore fills the frame (flying in);
     mode "open": we come out of the bore, the hole grows from the centre. Elements: #<p>-hole (circle in a
     mask), #<p>-ring (flange ring group), #<p>-ring2 (inner ring for depth). */
  function iris(tl, p, t0, d, mode, W, H, x, y, r0) {
    var hole = document.getElementById(p + "-hole"), ring = document.getElementById(p + "-ring"),
        ring2 = document.getElementById(p + "-ring2"), dark = document.getElementById(p + "-dark");
    var R = Math.hypot(W, H) * .62;
    var o = { u: 0 };
    function apply() {
      var u = o.u;
      if (mode === "close") {
        var e = u * u * (3 - 2 * u), far = Math.max(Math.hypot(x, y), Math.hypot(W - x, y), Math.hypot(x, H - y), Math.hypot(W - x, H - y));
        var r = r0 * Math.pow(far * 1.08 / r0, e * e), cx = x, cy = y;   // grows from the pipe mouth itself
        dark.setAttribute("r", r.toFixed(1)); dark.setAttribute("cx", cx.toFixed(1)); dark.setAttribute("cy", cy.toFixed(1));
        dark.setAttribute("opacity", u > 0 ? 1 : 0);
        ring.setAttribute("transform", "translate(" + cx.toFixed(1) + " " + cy.toFixed(1) + ") scale(" + (r / 100).toFixed(3) + ")");
        ring.setAttribute("opacity", u > 0 && u < .995 ? 1 : 0);
        ring2.setAttribute("transform", "translate(" + cx.toFixed(1) + " " + cy.toFixed(1) + ") scale(" + (r * .45 / 100).toFixed(3) + ")");
        ring2.setAttribute("opacity", u > .15 ? Math.min(1, (u - .15) * 3) : 0);
      } else {
        var e2 = 1 - Math.pow(1 - u, 3), rh = Math.max(.1, R * 1.15 * e2);
        hole.setAttribute("r", rh.toFixed(1));
        dark.setAttribute("opacity", u < 1 ? 1 : 0);
        ring.setAttribute("transform", "translate(" + W / 2 + " " + H / 2 + ") scale(" + (rh / 100).toFixed(3) + ")");
        ring.setAttribute("opacity", u < .98 ? 1 : 0);
        ring2.setAttribute("transform", "translate(" + W / 2 + " " + H / 2 + ") scale(" + (rh * 1.9 / 100).toFixed(3) + ")");
        ring2.setAttribute("opacity", u < .7 ? 1 - u / .7 : 0);
      }
    }
    o.u = mode === "close" ? 0 : 0; apply();
    tl.fromTo(o, { u: 0 }, { u: 1, duration: d, ease: "none", onUpdate: apply }, t0);
  }

  /* ---------------- gauge ----------------
     needle angle from a keyed value with a small seeded tremble: cfg {keys:[[t,v]], min, max, a0, a1, wobble} */
  function gauge(tl, sel, dur, cfg) {
    var el = document.querySelector(sel);
    clock(tl, dur, function (t) {
      var v = keyed(cfg.keys, t, cfg.ease || .7, cfg.keys[0][1]);
      v += (cfg.wobble || 0) * (Math.sin(t * 7.3) * .6 + Math.sin(t * 17.1 + 1) * .4);
      var f = clamp((v - cfg.min) / (cfg.max - cfg.min), -.05, 1.05);
      el.setAttribute("transform", "rotate(" + (cfg.a0 + (cfg.a1 - cfg.a0) * f).toFixed(2) + ")");
    });
  }

  function spin(tl, sel, dur, rps) {
    var els = document.querySelectorAll(sel);
    clock(tl, dur, function (t) { els.forEach(function (e) { e.setAttribute("transform", "rotate(" + ((t * rps * 360) % 360).toFixed(1) + ")"); }); });
  }

  window.DRIP = { rig: rig, follow: follow, iris: iris, gauge: gauge, spin: spin, rnd: rnd };
})();
