/* mm.js — Map Minutes runtime for HyperFrames scenes: the map camera (world units = km), map moves
   (borders drawing on, labels landing, the coral route travelling) and Pin's acting.
   Everything is a function of timeline time: no clocks, no unseeded randomness. */
(function () {
  function rnd(seed) { // mulberry32
    return function () {
      seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
      var t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function $(s) { return typeof s === "string" ? document.querySelector(s) : s; }
  function $$(s) { return [].slice.call(document.querySelectorAll(s)); }

  /* ---------------- map camera ----------------
     o.world: <g> holding the map in km; o.wrap: element that carries --k (px per km) for strokes;
     o.anchor: screen point the camera centre lands on; o.fw: focus width in px (span km fills it);
     o.keys: [{t, cx, cy, span, ease}]; o.blur: [{t, b, dur}] depth of field on the map layer;
     o.labels: selector of overlay elements with data-wx/data-wy (km) that ride on the map. */
  function mapcam(tl, o) {
    var k0 = o.keys[0];
    var cam = { cx: k0.cx, cy: k0.cy, span: k0.span };
    var fo = { b: o.blur && o.blur.length ? o.blur[0].b : 0 };
    var clock = { t: 0 };
    var world = $(o.world), wrap = $(o.wrap), far = o.far ? $(o.far) : null, mapEl = o.map ? $(o.map) : null;
    var labs = o.labels ? $$(o.labels).map(function (el) {
      return { el: el, wx: +el.getAttribute("data-wx"), wy: +el.getAttribute("data-wy") };
    }) : [];
    var amp = o.drift == null ? 1 : o.drift;
    var kk0 = o.fw / k0.span, tx0 = o.anchor[0] - k0.cx * kk0, ty0 = o.anchor[1] - k0.cy * kk0;
    function apply() {
      var t = clock.t;
      var sx = amp * (4 * Math.sin(t * 0.83 + 1.3) + 2 * Math.sin(t * 2.17 + 0.4));
      var sy = amp * (3 * Math.sin(t * 0.67 + 2.1) + 1.5 * Math.sin(t * 1.93 + 3.3));
      var k = o.fw / cam.span;
      var tx = o.anchor[0] + sx - cam.cx * k, ty = o.anchor[1] + sy - cam.cy * k;
      world.setAttribute("transform", "matrix(" + k + " 0 0 " + k + " " + tx + " " + ty + ")");
      wrap.style.setProperty("--k", k);
      for (var i = 0; i < labs.length; i++) gsap.set(labs[i].el, { x: labs[i].wx * k + tx, y: labs[i].wy * k + ty });
      if (far) gsap.set(far, { x: (tx - tx0) * 0.12 + sx * 0.4, y: (ty - ty0) * 0.12 + sy * 0.4 });
      if (mapEl) mapEl.style.filter = fo.b > 0.3 ? "blur(" + fo.b.toFixed(2) + "px)" : "none";
    }
    for (var k = 1; k < o.keys.length; k++) {
      var a = o.keys[k - 1], b = o.keys[k];
      tl.to(cam, { cx: b.cx, cy: b.cy, span: b.span, duration: Math.max(0.05, b.t - a.t),
                   ease: b.ease || "power2.inOut", onUpdate: apply }, a.t);
    }
    (o.blur || []).slice(1).forEach(function (f) {
      tl.to(fo, { b: f.b, duration: f.dur || 0.8, ease: "power2.inOut", onUpdate: apply }, f.t);
    });
    tl.fromTo(clock, { t: 0 }, { t: o.dur, duration: o.dur, ease: "none", onUpdate: apply }, 0);
  }

  /* ---------------- map moves ---------------- */
  // paths with pathLength="1" and stroke-dasharray="1 2": a border drawing itself on
  function draw(tl, sel, t, dur, stagger, ease) {
    tl.fromTo(sel, { attr: { "stroke-dashoffset": 1 } },
      { attr: { "stroke-dashoffset": 0 }, duration: dur || 1.2, ease: ease || "power2.inOut", stagger: stagger || 0 }, t);
  }
  // the coral route: a mask path (pathLength=1) reveals the dashed line; a head dot rides the tip
  function route(tl, maskSel, headSel, t, dur, ease) {
    var mp = $(maskSel), head = headSel ? $(headSel) : null, L = mp.getTotalLength() || 1, st = { p: 0 };
    function upd() {
      mp.setAttribute("stroke-dashoffset", (1 - st.p).toFixed(4));
      if (head) {
        var q = mp.getPointAtLength(Math.max(0.001, st.p) * L);
        head.setAttribute("cx", q.x.toFixed(2)); head.setAttribute("cy", q.y.toFixed(2));
        head.setAttribute("opacity", st.p > 0.002 ? 1 : 0);
      }
    }
    tl.fromTo(st, { p: 0 }, { p: 1, duration: dur || 2, ease: ease || "power1.inOut", onUpdate: upd }, t);
    upd();
  }
  // a label lands: drops a little, settles with a small overshoot; its dot pops first
  function land(tl, sel, t, big) {
    var el = $(sel); if (!el) return;
    var dot = el.querySelector(".dot"), body = el.querySelector(".lab-in");
    if (dot) tl.fromTo(dot, { scale: 0 }, { scale: 1, duration: 0.3, ease: "back.out(3)" }, t);
    if (body) tl.fromTo(body, { opacity: 0, y: big ? -40 : -22, scale: big ? 1.15 : 0.92 },
      { opacity: 1, y: 0, scale: 1, duration: big ? 0.55 : 0.42, ease: "back.out(2)" }, t + (dot ? 0.08 : 0));
  }
  // a region fills in, swept west to east by a growing clip rect (attr width in km)
  function sweep(tl, rectSel, fillSel, w, t, dur, op) {
    tl.fromTo(rectSel, { attr: { width: 0 } }, { attr: { width: w }, duration: dur || 1.2, ease: "power2.inOut" }, t);
    if (fillSel) tl.fromTo(fillSel, { opacity: 0 }, { opacity: op == null ? 1 : op, duration: 0.3 }, t);
  }
  function pulse(tl, sel, t, n) {
    tl.to(sel, { opacity: 0.55, duration: 0.35, yoyo: true, repeat: 2 * (n || 2) - 1, ease: "sine.inOut" }, t);
  }

  /* ---------------- Pin ----------------
     Rig space: tip (ground contact) at 0,0; head centre 0,-185; needle pivot 0,-305; eyes at +-21.85,-194.5.
     Groups: -lean (rotation about the tip) > -squash (takes) > -body (breath) > needle, head, -face. */
  var TIP = "0 0", PIV = "0 -305", HEAD = "0 -185", EYE = { l: "-21.85 -194.5", r: "21.85 -194.5" };
  function g(id, part) { return document.getElementById(id + "-" + part); }

  function breathe(tl, id, dur) {
    var n = Math.max(1, Math.floor(dur / 3.2));
    tl.fromTo(g(id, "body"), { scaleY: 1, scaleX: 1 }, { scaleY: 1.016, scaleX: 0.994, svgOrigin: TIP, duration: dur / (2 * n),
      ease: "sine.inOut", yoyo: true, repeat: 2 * n - 1 }, 0);
  }
  function blinks(tl, id, dur, seed) {
    var r = rnd(seed || 7), t = 0.5 + r() * 1.2;
    while (t < dur - 0.3) {
      ["l", "r"].forEach(function (s, i) {
        tl.to(g(id, "lid" + s), { scaleY: 0.1, svgOrigin: EYE[s], duration: 0.06, ease: "power1.in" }, t + i * 0.02);
        tl.to(g(id, "lid" + s), { scaleY: 1, svgOrigin: EYE[s], duration: 0.1, ease: "power1.out" }, t + 0.07 + i * 0.02);
      });
      t += 2.0 + r() * 2.8;
    }
  }
  // the needle reacts last and settles with drag
  function needle(tl, id, mode, t, amt) {
    var n = g(id, "needle"), a = amt == null ? 1 : amt;
    if (mode === "swing") {
      tl.to(n, { keyframes: [{ rotation: 34 * a, duration: 0.16, ease: "power2.out" }, { rotation: -26 * a, duration: 0.24 },
        { rotation: 16 * a, duration: 0.24 }, { rotation: -8 * a, duration: 0.26 }, { rotation: 0, duration: 0.4, ease: "sine.out" }],
        svgOrigin: PIV }, t);
    } else if (mode === "spin") {
      tl.fromTo(n, { rotation: 0 }, { rotation: 360 * (a || 1), svgOrigin: PIV, duration: 1.1, ease: "power3.out" }, t);
      tl.set(n, { rotation: 0, svgOrigin: PIV }, t + 1.12);
    } else if (mode === "tremble") {
      tl.to(n, { rotation: 7 * a, svgOrigin: PIV, duration: 0.05, yoyo: true, repeat: 13, ease: "none" }, t);
      tl.to(n, { rotation: 0, svgOrigin: PIV, duration: 0.2 }, t + 0.72);
    } else if (mode === "waver") {
      tl.to(n, { keyframes: [{ rotation: -16 * a, duration: 0.7, ease: "sine.inOut" }, { rotation: 12 * a, duration: 0.8, ease: "sine.inOut" },
        { rotation: -6 * a, duration: 0.6, ease: "sine.inOut" }, { rotation: 0, duration: 0.5, ease: "sine.inOut" }], svgOrigin: PIV }, t);
    } else if (mode === "wiggle") {
      tl.to(n, { keyframes: [{ rotation: 12 * a, duration: 0.1 }, { rotation: -10 * a, duration: 0.12 }, { rotation: 6 * a, duration: 0.12 },
        { rotation: 0, duration: 0.25, ease: "sine.out" }], svgOrigin: PIV }, t);
    }
  }
  // eyes lead, the face follows, the body leans, the needle drags behind
  function look(tl, id, dx, dy, t) {
    ["l", "r"].forEach(function (s, i) {
      tl.to(g(id, "eye" + s), { x: dx * 0.7, y: dy * 0.7, duration: 0.12, ease: "power2.out" }, t + i * 0.03);
    });
    tl.to(g(id, "face"), { x: dx * 0.45, y: dy * 0.35, duration: 0.28, ease: "power2.inOut" }, t + 0.07);
    tl.to(g(id, "lean"), { rotation: dx * 0.45, svgOrigin: TIP, duration: 0.45, ease: "power2.inOut" }, t + 0.13);
    tl.to(g(id, "needle"), { keyframes: [{ rotation: -dx * 1.1, duration: 0.2, ease: "power2.out" },
      { rotation: 0, duration: 0.7, ease: "elastic.out(1, 0.4)" }], svgOrigin: PIV }, t + 0.2);
  }
  // point: lean toward the target, eyes on it, the needle swings round to aim at it (deg, 0 = up, 90 = right)
  function point(tl, id, ang, t, hold) {
    var rad = ang * Math.PI / 180, dx = Math.sin(rad) * 9, dy = -Math.cos(rad) * 7;
    var lean = Math.max(-9, Math.min(9, Math.sin(rad) * 8));
    ["l", "r"].forEach(function (s, i) {
      tl.to(g(id, "eye" + s), { x: dx * 0.7, y: dy * 0.7, duration: 0.12, ease: "power2.out" }, t + i * 0.03);
    });
    tl.to(g(id, "face"), { x: dx * 0.45, y: dy * 0.35, duration: 0.3, ease: "power2.inOut" }, t + 0.07);
    tl.to(g(id, "lean"), { rotation: lean, svgOrigin: TIP, duration: 0.42, ease: "back.out(2)" }, t + 0.12);
    tl.to(g(id, "needle"), { rotation: ang - lean, svgOrigin: PIV, duration: 0.95, ease: "elastic.out(1, 0.38)" }, t + 0.18);
    if (hold) {
      tl.to(g(id, "needle"), { rotation: 0, svgOrigin: PIV, duration: 0.7, ease: "elastic.out(1, 0.5)" }, t + hold);
      tl.to(g(id, "lean"), { rotation: 0, svgOrigin: TIP, duration: 0.5, ease: "power2.inOut" }, t + hold);
    }
  }
  // expression take: anticipation squash, the new face, a settle; brows/eyes per expression
  var FACES = {
    neutral:   { eye: 1, eyeY: 1, bl: [0, 0], br: [0, 0], cheek: 0.35 },
    happy:     { eye: 1, eyeY: 0.8, bl: [-3, -4], br: [-3, 4], cheek: 0.65 },
    surprised: { eye: 1.22, eyeY: 1.22, bl: [-9, 0], br: [-9, 0], cheek: 0.3 },
    thinking:  { eye: 1, eyeY: 1, bl: [2, 6], br: [-9, -10], cheek: 0.3 },
    worried:   { eye: 1.05, eyeY: 1.05, bl: [-4, 14], br: [-4, -14], cheek: 0.2 }
  };
  var REACT = { surprised: "swing", happy: "wiggle", thinking: "waver", worried: "tremble" };
  function face(tl, id, expr, t, react) {
    var f = FACES[expr] || FACES.neutral;
    tl.to(g(id, "squash"), { scaleY: 0.93, scaleX: 1.05, svgOrigin: TIP, duration: 0.08, ease: "power2.out" }, t);
    tl.to(g(id, "squash"), { scaleY: 1, scaleX: 1, svgOrigin: TIP, duration: 0.5, ease: "elastic.out(1, 0.42)" }, t + 0.08);
    ["l", "r"].forEach(function (s, i) {
      tl.to(g(id, "eye" + s), { scaleX: f.eye, scaleY: f.eyeY, svgOrigin: EYE[s], duration: 0.18, ease: "back.out(2)" }, t + 0.06 + i * 0.03);
      var b = s === "l" ? f.bl : f.br;
      tl.to(g(id, "brow" + s), { y: b[0], rotation: b[1], svgOrigin: EYE[s], duration: 0.2, ease: "back.out(2)" }, t + 0.04 + i * 0.04);
      tl.to(g(id, "cheek" + s), { opacity: f.cheek, duration: 0.2 }, t + 0.1);
    });
    if (react !== false && REACT[expr]) needle(tl, id, REACT[expr], t + 0.16, 1);
  }
  function setFace(tl, id, expr) {
    var f = FACES[expr] || FACES.neutral;
    ["l", "r"].forEach(function (s) {
      var b = s === "l" ? f.bl : f.br;
      tl.set(g(id, "eye" + s), { scaleX: f.eye, scaleY: f.eyeY, svgOrigin: EYE[s] }, 0);
      tl.set(g(id, "brow" + s), { y: b[0], rotation: b[1], svgOrigin: EYE[s] }, 0);
      tl.set(g(id, "cheek" + s), { opacity: f.cheek }, 0);
    });
  }
  // mouth track [[t, name], ...] computed from the expression keys and the word timings
  var MOUTHS = ["smile", "talka", "talkb", "o", "flat", "grin", "wobble"];
  function mouths(tl, id, track) {
    track.forEach(function (k) {
      MOUTHS.forEach(function (m) { tl.set(g(id, "m-" + m), { opacity: m === k[1] ? 1 : 0 }, k[0]); });
    });
  }
  function hop(tl, id, t, h) {
    var w = document.getElementById(id), s = (+w.getAttribute("data-r") || 100) / 100, H = (h || 70) * s;
    tl.to(g(id, "squash"), { scaleY: 0.86, scaleX: 1.1, svgOrigin: TIP, duration: 0.1, ease: "power2.in" }, t);
    tl.to(w, { y: -H, duration: 0.22, ease: "power2.out" }, t + 0.1);
    tl.to(g(id, "squash"), { scaleY: 1.08, scaleX: 0.95, svgOrigin: TIP, duration: 0.12 }, t + 0.1);
    tl.to(w, { y: 0, duration: 0.2, ease: "power2.in" }, t + 0.32);
    tl.to(g(id, "squash"), { scaleY: 0.9, scaleX: 1.08, svgOrigin: TIP, duration: 0.07 }, t + 0.5);
    tl.to(g(id, "squash"), { scaleY: 1, scaleX: 1, svgOrigin: TIP, duration: 0.45, ease: "elastic.out(1, 0.4)" }, t + 0.57);
    tl.to(g(id, "shadow"), { scale: 0.6, opacity: 0.6, svgOrigin: TIP, duration: 0.22, yoyo: true, repeat: 1 }, t + 0.1);
    needle(tl, id, "wiggle", t + 0.5, 1);
  }
  // drop in from above the frame: lands on its tip, squashes, settles; the needle spins on impact
  function drop(tl, id, t, from) {
    var w = document.getElementById(id);
    tl.fromTo(w, { y: from || -1100 }, { y: 0, duration: 0.42, ease: "power2.in" }, t);
    tl.fromTo(g(id, "shadow"), { scale: 0.2, opacity: 0, svgOrigin: TIP }, { scale: 1, opacity: 1, svgOrigin: TIP, duration: 0.42, ease: "power2.in" }, t);
    tl.to(g(id, "squash"), { scaleY: 0.8, scaleX: 1.16, svgOrigin: TIP, duration: 0.07, ease: "power2.out" }, t + 0.42);
    tl.to(g(id, "squash"), { scaleY: 1, scaleX: 1, svgOrigin: TIP, duration: 0.6, ease: "elastic.out(1, 0.35)" }, t + 0.49);
    needle(tl, id, "swing", t + 0.44, 1.1);
  }
  function slide(tl, id, dx, t, dur) {
    var w = document.getElementById(id);
    tl.fromTo(w, { x: dx }, { x: 0, duration: dur || 0.6, ease: "power3.out" }, t);
    tl.fromTo(g(id, "lean"), { rotation: dx > 0 ? -8 : 8, svgOrigin: TIP }, { rotation: 0, svgOrigin: TIP, duration: 0.8, ease: "elastic.out(1, 0.45)" }, t + (dur || 0.6) * 0.6);
  }

  /* ---------------- fx ---------------- */
  function grain(tl, sel, dur) {
    var n = Math.max(1, Math.floor(dur * 12)), r = rnd(99), xs = [], ys = [];
    for (var i = 0; i < n; i++) { xs.push(Math.floor(r() * 256)); ys.push(Math.floor(r() * 256)); }
    var o = { i: 0 }, el = $(sel);
    tl.fromTo(o, { i: 0 }, { i: n - 1, duration: dur, ease: "none", onUpdate: function () {
      var k = Math.floor(o.i); el.style.backgroundPosition = xs[k] + "px " + ys[k] + "px";
    } }, 0);
  }
  function roll(tl, sel, from, to, t, d, dec, pre, suf) {
    var el = $(sel), o = { v: from };
    var f = function (v) { var s = v.toFixed(dec || 0), p = s.split("."); p[0] = p[0].replace(/\B(?=(\d{3})+(?!\d))/g, ","); return (pre || "") + p.join(".") + (suf || ""); };
    el.textContent = f(from);
    tl.fromTo(o, { v: from }, { v: to, duration: d || 1.4, ease: "power2.out", onUpdate: function () { el.textContent = f(o.v); } }, t);
  }

  window.MM = { rnd: rnd, mapcam: mapcam, draw: draw, route: route, land: land, sweep: sweep, pulse: pulse,
                pin: { breathe: breathe, blinks: blinks, needle: needle, look: look, point: point, face: face,
                       setFace: setFace, mouths: mouths, hop: hop, drop: drop, slide: slide },
                grain: grain, roll: roll };
})();
