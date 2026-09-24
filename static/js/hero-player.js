(function () {
  document.querySelectorAll('[data-hero-player]').forEach(function (container) {
    var video = container.querySelector('video');
    var overlay = container.querySelector('[data-play-overlay]');
    if (!video || !overlay) { return; }

    var src = video.getAttribute('data-hls-src');
    if (src) {
      if (window.Hls && Hls.isSupported()) {
        var hls = new Hls();
        hls.loadSource(src);
        hls.attachMedia(video);
      } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
        video.src = src;
      }
    }

    overlay.addEventListener('click', function () {
      video.play();
      if (video.requestFullscreen) { video.requestFullscreen(); }
    });

    video.addEventListener('play', function () {
      overlay.style.display = 'none';
    });

    video.addEventListener('pause', function () {
      overlay.style.display = 'flex';
    });
  });
})();