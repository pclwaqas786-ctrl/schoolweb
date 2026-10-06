/* SchoolWeb v2 — scroll reveal + animated counters (no dependencies) */
(function(){
  // reveal on scroll
  var io = new IntersectionObserver(function(es){
    es.forEach(function(e){ if(e.isIntersecting){ e.target.classList.add("in"); io.unobserve(e.target); } });
  }, {threshold:.12});
  document.querySelectorAll(".reveal").forEach(function(el){ io.observe(el); });

  // animated counters: <span class="num" data-count="1250" data-suffix="+">
  var cio = new IntersectionObserver(function(es){
    es.forEach(function(e){
      if(!e.isIntersecting) return;
      var el = e.target, target = parseInt(el.dataset.count||"0",10), suf = el.dataset.suffix||"";
      cio.unobserve(el);
      var t0 = null, dur = 1400;
      function tick(t){
        if(!t0) t0 = t;
        var p = Math.min((t-t0)/dur, 1), ease = 1-Math.pow(1-p,3);
        el.textContent = Math.round(target*ease).toLocaleString("en-US") + suf;
        if(p<1) requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    });
  }, {threshold:.4});
  document.querySelectorAll(".num[data-count]").forEach(function(el){ cio.observe(el); });
})();
