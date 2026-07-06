/**
 * Playlist drag-and-drop
 *
 * Handles two interactions:
 *   1. Reorder playlist items by dragging within #playlist-items.
 *   2. Add a media item by dragging a [data-media-id] card from the provider
 *      panel onto #playlist-drop-zone.
 *
 * Uses event delegation on `document` so it works after HTMX swaps the
 * provider panel without needing to re-attach listeners.
 */
(function () {
  'use strict';

  let dragState = null;
  // dragState = { type: 'sort', el: <li> }
  //           | { type: 'add', mediaId: '...' }

  function csrf() {
    const el = document.querySelector('[name=csrfmiddlewaretoken]');
    return el ? el.value : '';
  }

  // ------------------------------------------------------------------
  // dragstart — fired on the dragged element
  // ------------------------------------------------------------------
  document.addEventListener('dragstart', function (e) {
    // Playlist item reorder
    const item = e.target.closest('#playlist-items [data-item-id]');
    if (item) {
      dragState = { type: 'sort', el: item };
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', item.dataset.itemId);
      // Defer so the element isn't invisible while the drag image is captured
      setTimeout(() => item.classList.add('is-dragging'), 0);
      return;
    }

    // Provider panel card → add to playlist
    const card = e.target.closest('[data-media-id]');
    if (card && !card.dataset.added) {
      dragState = { type: 'add', mediaId: card.dataset.mediaId };
      e.dataTransfer.effectAllowed = 'copy';
      e.dataTransfer.setData('text/plain', card.dataset.mediaId);
      card.classList.add('is-dragging');
      const zone = document.getElementById('playlist-drop-zone');
      if (zone) zone.classList.add('drop-zone');
    }
  });

  // ------------------------------------------------------------------
  // dragend — always fires on the dragged element
  // ------------------------------------------------------------------
  document.addEventListener('dragend', function () {
    document.querySelectorAll(
      '.is-dragging, .drag-over, .drop-zone, .drop-zone-hover'
    ).forEach(el => el.classList.remove('is-dragging', 'drag-over', 'drop-zone', 'drop-zone-hover'));
    dragState = null;
  });

  // ------------------------------------------------------------------
  // dragover — must call preventDefault to allow drop
  // ------------------------------------------------------------------
  document.addEventListener('dragover', function (e) {
    if (!dragState) return;

    if (dragState.type === 'sort') {
      const target = e.target.closest('#playlist-items [data-item-id]');
      if (target && target !== dragState.el) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        document.querySelectorAll('[data-item-id].drag-over')
          .forEach(el => el !== target && el.classList.remove('drag-over'));
        target.classList.add('drag-over');
      }
    }

    if (dragState.type === 'add') {
      const zone = document.getElementById('playlist-drop-zone');
      if (zone && zone.contains(e.target)) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'copy';
        zone.classList.add('drop-zone-hover');
      }
    }
  });

  // ------------------------------------------------------------------
  // dragleave
  // ------------------------------------------------------------------
  document.addEventListener('dragleave', function (e) {
    if (!dragState) return;

    if (dragState.type === 'sort') {
      const target = e.target.closest('[data-item-id]');
      if (target) target.classList.remove('drag-over');
    }

    if (dragState.type === 'add') {
      const zone = document.getElementById('playlist-drop-zone');
      if (zone && !zone.contains(e.relatedTarget)) {
        zone.classList.remove('drop-zone-hover');
      }
    }
  });

  // ------------------------------------------------------------------
  // drop
  // ------------------------------------------------------------------
  document.addEventListener('drop', function (e) {
    if (!dragState) return;

    if (dragState.type === 'sort') {
      const target = e.target.closest('#playlist-items [data-item-id]');
      if (!target || target === dragState.el) return;
      e.preventDefault();

      const list = target.closest('ul');
      const items = Array.from(list.querySelectorAll('[data-item-id]'));
      const fromIdx = items.indexOf(dragState.el);
      const toIdx = items.indexOf(target);

      if (fromIdx < toIdx) {
        list.insertBefore(dragState.el, target.nextSibling);
      } else {
        list.insertBefore(dragState.el, target);
      }

      const newOrder = Array.from(list.querySelectorAll('[data-item-id]'))
        .map(el => el.dataset.itemId);
      saveOrder(newOrder);
    }

    if (dragState.type === 'add') {
      const zone = document.getElementById('playlist-drop-zone');
      if (!zone || !zone.contains(e.target)) return;
      e.preventDefault();
      addMedia(dragState.mediaId);
    }
  });

  // ------------------------------------------------------------------
  // Server calls
  // ------------------------------------------------------------------

  function saveOrder(ids) {
    const form = new FormData();
    form.append('csrfmiddlewaretoken', csrf());
    form.append('action', 'reorder');
    ids.forEach(id => form.append('order[]', id));
    // Fire-and-forget; the DOM is already updated. Use 'manual' to avoid
    // an unwanted page navigation from the server's redirect response.
    fetch(window.location.pathname, { method: 'POST', body: form, redirect: 'manual' });
  }

  function addMedia(mediaId) {
    const form = new FormData();
    form.append('csrfmiddlewaretoken', csrf());
    form.append('action', 'add_media');
    form.append('media_id', mediaId);
    // Follow the server redirect; its final URL preserves ?provider=<id>
    fetch(window.location.pathname, { method: 'POST', body: form })
      .then(r => { window.location.href = r.url; });
  }

})();
