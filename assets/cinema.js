/* cinema.js — deterministic camera, character rig and fx helpers for HyperFrames scenes.
   Everything is a function of timeline time: no clocks, no unseeded randomness. */
(function () {
  var W = 1920, H = 1080;

  function rnd(seed) { // mulberry32
    return function () {
      seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
      var t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  /* ---------------- camera (multiplane) ----------------
     layers: [{el, d}] d = depth (1 = subject plane, >1 far, <1 near)
     keys:   [{t, x, y, z, ease}] camera position in world px and zoom
     focus:  [{t, f, dur}] focal depth for depth-of-field (blur) */
  function camera(tl, sid, layers, keys, focus, dur, shake) {
    var cam = { x: keys[0].x || 0, y: keys[0].y || 0, z: keys[0].z || 1 };
    var fo = { f: focus && focus.length ? focus[0].f : 1 };
    var clock = { t: 0 };
    var amp = shake == null ? 1 : shake;
    var els = layers.map(function (L) { return { el: document.querySelector(L.sel), d: L.d, blur: L.blur }; });
    function apply() {
      var t = clock.t;
      var sx = amp * (5 * Math.sin(t * 0.83 + 1.3) + 2.5 * Math.sin(t * 2.17 + 0.4));
      var sy = amp * (3.5 * Math.sin(t * 0.67 + 2.1) + 1.8 * Math.sin(t * 1.93 + 3.3));
      var sr = amp * 0.12 * Math.sin(t * 0.51 + 0.7);
      for (var i = 0; i < els.length; i++) {
        var L = els[i]; if (!L.el) continue;
        var p = 1 / L.d;
        var s = 1 + (cam.z - 1) * p;
        var b = L.blur === false ? 0 : Math.min(16, 13 * Math.abs(p - 1 / fo.f));
        gsap.set(L.el, { x: -(cam.x + sx) * p * s, y: -(cam.y + sy) * p * s, scale: s, rotation: sr * p,
                         filter: b > 0.4 ? "blur(" + b.toFixed(2) + "px)" : "none" });
      }
    }
    for (var k = 1; k < keys.length; k++) {
      var a = keys[k - 1], b = keys[k];
      tl.to(cam, { x: b.x != null ? b.x : a.x, y: b.y != null ? b.y : a.y, z: b.z != null ? b.z : a.z,
                   duration: Math.max(0.05, b.t - a.t), ease: b.ease || "power2.inOut", onUpdate: apply }, a.t);
    }
    (focus || []).slice(1).forEach(function (f) {
      tl.to(fo, { f: f.f, duration: f.dur || 0.8, ease: "power2.inOut", onUpdate: apply }, f.t);
    });
    tl.fromTo(clock, { t: 0 }, { t: dur, duration: dur, ease: "none", onUpdate: apply }, 0);
  }

  /* ---------------- character rig ---------------- */
  var POSES = { // [shoulder, elbow] degrees; 0 = arm hanging down
    idle: [[6, -4], [-6, 4]],
    hold: [[6, -4], [-24, -86]],
    point: [[6, -4], [-96, -4]],
    pointup: [[6, -4], [-150, -10]],
    shrug: [[38, 96], [-38, -96]],
    chin: [[6, -4], [-34, -138]],
    wave: [[6, -4], [-158, -24]],
    present: [[30, 40], [-60, -30]],
    hips: [[24, 70], [-24, -70]],
    toss: [[6, -4], [-170, -8]]
  };
  var SHOULDER = { l: [-68, -326], r: [68, -326] };

  function q(id, part) { return document.getElementById(id + "-" + part); }
  // shoulders per rig: the Tag mascot carries data-sx on its root (arms on the tag's edges)
  function shoulders(id) {
    var root = q(id, "root"), sx = root && root.getAttribute("data-sx") ? +root.getAttribute("data-sx") : 68;
    return { l: [-sx, -326], r: [sx, -326] };
  }

  function pose(tl, id, name, t, d, side) {
    var p = POSES[name] || POSES.idle;
    var sides = side ? [side] : ["l", "r"];
    sides.forEach(function (s, i) {
      var idx = s === "l" ? 0 : 1;
      var sh = shoulders(id)[s];
      tl.to(q(id, "arm" + s), { rotation: p[idx][0], svgOrigin: sh[0] + " " + sh[1], duration: d || 0.42, ease: "back.out(1.5)" }, t + i * 0.06);
      tl.to(q(id, "fore" + s), { rotation: p[idx][1], svgOrigin: sh[0] + " " + (sh[1] + 92), duration: (d || 0.42) * 1.15, ease: "back.out(1.7)" }, t + 0.05 + i * 0.06);
    });
  }

  function setPose(tl, id, name, t) {
    var p = POSES[name] || POSES.idle;
    ["l", "r"].forEach(function (s) {
      var idx = s === "l" ? 0 : 1, sh = shoulders(id)[s];
      tl.set(q(id, "arm" + s), { rotation: p[idx][0], svgOrigin: sh[0] + " " + sh[1] }, t);
      tl.set(q(id, "fore" + s), { rotation: p[idx][1], svgOrigin: sh[0] + " " + (sh[1] + 92) }, t);
    });
  }

  var EXPR = ["neutral", "happy", "surprised", "worried", "thinking", "proud"];
  function face(tl, id, expr, t) {
    EXPR.forEach(function (e) {
      ["fe-", "fm-"].forEach(function (pre) {
        var el = q(id, pre + e);
        if (el) tl.to(el, { opacity: e === expr ? 1 : 0, duration: 0.1 }, t + 0.07);
      });
    });
    // a take: small squash, then settle
    tl.to(q(id, "head"), { scaleY: 0.94, scaleX: 1.04, svgOrigin: "0 -345", duration: 0.08, ease: "power2.out" }, t);
    tl.to(q(id, "head"), { scaleY: 1, scaleX: 1, svgOrigin: "0 -345", duration: 0.35, ease: "elastic.out(1, 0.45)" }, t + 0.08);
  }

  function look(tl, id, dx, t) {
    tl.to(q(id, "face"), { x: dx, duration: 0.3, ease: "power2.inOut" }, t);
    tl.to(q(id, "head"), { rotation: dx * 0.18, svgOrigin: "0 -345", duration: 0.4, ease: "power2.inOut" }, t);
  }

  function blinks(tl, id, dur, seed) {
    var r = rnd(seed || 7), t = 0.6 + r() * 1.2;
    while (t < dur - 0.3) {
      tl.to(q(id, "eyes"), { scaleY: 0.1, svgOrigin: "-2 -432", duration: 0.06, ease: "power1.in" }, t);
      tl.to(q(id, "eyes"), { scaleY: 1, svgOrigin: "-2 -432", duration: 0.09, ease: "power1.out" }, t + 0.07);
      t += 2.2 + r() * 2.6;
    }
  }

  function breathe(tl, id, dur) {
    var n = Math.max(1, Math.floor(dur / 3.4));
    tl.fromTo(q(id, "torso"), { scaleY: 1 }, { scaleY: 1.014, svgOrigin: "0 -170", duration: dur / (2 * n), ease: "sine.inOut", yoyo: true, repeat: 2 * n - 1 }, 0);
  }

  // walk: moves the character wrapper by dx over dur with a planted-foot cycle
  function walk(tl, id, dx, t, dur, swingRight) {
    var steps = Math.max(2, Math.round(dur / 0.36));
    var ph = { p: 0 };
    var legL = q(id, "legl"), legR = q(id, "legr"), body = q(id, "upper"), armL = q(id, "arml"), armR = q(id, "armr");
    tl.to("#" + id, { x: "+=" + dx, duration: dur, ease: "none" }, t);
    tl.fromTo(ph, { p: 0 }, { p: steps * Math.PI, duration: dur, ease: "none", onUpdate: function () {
      var s = Math.sin(ph.p);
      var fade = Math.min(1, ph.p / 1.2, (steps * Math.PI - ph.p) / 1.2);
      gsap.set(legL, { rotation: 24 * s * fade, svgOrigin: "-26 -170" });
      gsap.set(legR, { rotation: -24 * s * fade, svgOrigin: "26 -170" });
      gsap.set(body, { y: -7 * Math.abs(s) * fade });
      gsap.set(armL, { rotation: -16 * s * fade, svgOrigin: shoulders(id).l.join(" ") });
      if (swingRight) gsap.set(armR, { rotation: 16 * s * fade, svgOrigin: shoulders(id).r.join(" ") });
    } }, t);
  }

  function hop(tl, id, t) {
    tl.to("#" + id + "-inner", { y: -40, duration: 0.18, ease: "power2.out" }, t);
    tl.to("#" + id + "-inner", { y: 0, duration: 0.22, ease: "bounce.out" }, t + 0.18);
  }

  /* ---------------- fx ---------------- */
  function grain(tl, sel, dur) {
    var n = Math.max(1, Math.floor(dur * 12));
    var r = rnd(99), xs = [], ys = [];
    for (var i = 0; i < n; i++) { xs.push(Math.floor(r() * 256)); ys.push(Math.floor(r() * 256)); }
    var o = { i: 0 }, el = document.querySelector(sel);
    tl.fromTo(o, { i: 0 }, { i: n - 1, duration: dur, ease: "none", onUpdate: function () {
      var k = Math.floor(o.i); el.style.backgroundPosition = xs[k] + "px " + ys[k] + "px";
    } }, 0);
  }

  function dust(tl, sel, dur, seed) {
    var r = rnd(seed || 3);
    document.querySelectorAll(sel).forEach(function (el) {
      var dx = (r() - 0.5) * 120, dy = -60 - r() * 140;
      tl.fromTo(el, { x: 0, y: 0, opacity: 0 }, { x: dx, y: dy, opacity: 0.25 + r() * 0.5, duration: dur, ease: "sine.inOut" }, 0);
    });
  }

  function roll(tl, el, from, to, t, d, dec, pre, suf, comma) {
    var o = { v: from }; el = typeof el === "string" ? document.querySelector(el) : el;
    var f = function (v) { var s = v.toFixed(dec); var p = s.split("."); if (comma !== false) p[0] = p[0].replace(/\B(?=(\d{3})+(?!\d))/g, ","); return pre + p.join(".") + suf; };
    el.textContent = f(from);
    tl.fromTo(o, { v: from }, { v: to, duration: d, ease: "power2.out", onUpdate: function () { el.textContent = f(o.v); } }, t);
  }

  window.CIN = { camera: camera, pose: pose, setPose: setPose, face: face, look: look, blinks: blinks, breathe: breathe,
                 walk: walk, hop: hop, grain: grain, dust: dust, roll: roll, rnd: rnd, W: W, H: H };
})();
