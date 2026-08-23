(function () {
  var root = document.querySelector("[data-rev-carousel]");
  var track = document.querySelector("[data-rev-track]");
  if (!root || !track) return;

  var prev = document.querySelector("[data-rev-prev]");
  var next = document.querySelector("[data-rev-next]");
  var slides = track.querySelectorAll(".reviews-carousel__slide");
  if (slides.length < 2) return;

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var paused = false;
  var pos = 0;
  var speed = 0.8;
  var resumeTimer = null;

  Array.prototype.forEach.call(slides, function (node) {
    var clone = node.cloneNode(true);
    clone.setAttribute("aria-hidden", "true");
    track.appendChild(clone);
  });

  track.style.scrollSnapType = "none";
  track.style.scrollBehavior = "auto";

  function halfWidth() {
    return track.scrollWidth / 2;
  }

  function applyPos() {
    var half = halfWidth();
    if (half <= 0) return;
    if (pos >= half) pos -= half;
    if (pos < 0) pos += half;
    track.scrollLeft = pos;
  }

  function loop() {
    if (!paused && !reduceMotion) {
      pos += speed;
      applyPos();
    } else {
      pos = track.scrollLeft;
    }
    window.requestAnimationFrame(loop);
  }

  function pause() {
    paused = true;
    pos = track.scrollLeft;
    if (resumeTimer) {
      window.clearTimeout(resumeTimer);
      resumeTimer = null;
    }
  }

  function resume(delay) {
    if (reduceMotion) return;
    if (resumeTimer) window.clearTimeout(resumeTimer);
    resumeTimer = window.setTimeout(function () {
      paused = false;
      pos = track.scrollLeft;
      resumeTimer = null;
    }, delay || 0);
  }

  function stepSize() {
    var slide = track.querySelector(".reviews-carousel__slide");
    if (!slide) return 320;
    var styles = window.getComputedStyle(track);
    var gap = parseFloat(styles.columnGap || styles.gap || "16") || 16;
    return slide.getBoundingClientRect().width + gap;
  }

  function nudge(dir) {
    pause();
    var start = track.scrollLeft;
    var target = start + dir * stepSize();
    var dist = target - start;
    var t0 = null;
    var dur = 700;

    function ease(t) {
      return 1 - Math.pow(1 - t, 3);
    }

    function anim(ts) {
      if (t0 === null) t0 = ts;
      var p = Math.min(1, (ts - t0) / dur);
      pos = start + dist * ease(p);
      applyPos();
      if (p < 1) {
        window.requestAnimationFrame(anim);
      } else {
        resume(1000);
      }
    }
    window.requestAnimationFrame(anim);
  }

  if (prev) prev.addEventListener("click", function (e) { e.preventDefault(); nudge(-1); });
  if (next) next.addEventListener("click", function (e) { e.preventDefault(); nudge(1); });

  root.addEventListener("mouseenter", pause);
  root.addEventListener("mouseleave", function () { resume(250); });
  root.addEventListener("focusin", pause);
  root.addEventListener("focusout", function () { resume(250); });
  root.addEventListener("touchstart", pause, { passive: true });
  root.addEventListener("touchend", function () { resume(1400); });

  root.style.minWidth = "0";
  track.style.minWidth = "0";
  track.style.width = "100%";

  pos = track.scrollLeft || 0;
  window.requestAnimationFrame(loop);
})();
