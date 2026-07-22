/* ================================================
   DTD — Modal System + Toast + Confirm Dialog
   ================================================
   Depends on: dtd-constants.js, dtd-storage.js,
               dtd-week.js, dtd-touchpoints.js, dtd-builders.js
   ================================================ */
(function (DTD) {
  'use strict';

  // ── Toast ─────────────────────────────────────

  DTD.showToast = function (message, type) {
    var container = document.getElementById('toast-container');
    if (!container) return;

    var toast = document.createElement('div');
    toast.className = 'toast' + (type ? ' ' + type : '');
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(function () {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.3s';
      setTimeout(function () {
        if (toast.parentNode) toast.parentNode.removeChild(toast);
      }, 300);
    }, 2500);
  };

  // ── Confirm Dialog ────────────────────────────

  DTD.showConfirm = function (message, onOk) {
    var msgEl = document.getElementById('confirm-message');
    if (msgEl) msgEl.textContent = message;

    DTD.state.confirmCallback = onOk;

    document.getElementById('confirm-overlay').classList.remove('hidden');
    document.getElementById('confirm-dialog').classList.remove('hidden');
  };

  DTD.closeConfirm = function () {
    document.getElementById('confirm-overlay').classList.add('hidden');
    document.getElementById('confirm-dialog').classList.add('hidden');
    DTD.state.confirmCallback = null;
  };

  // ── Print a single note card ──────────────────
  // Renders ONLY the address + note (via a dedicated #print-area the print
  // stylesheet isolates), so the CRM screen and modal chrome don't print.
  DTD.printNoteCard = function (contact) {
    if (!contact) return;
    var action = DTD.buildNoteCardAction(contact);
    var area   = document.getElementById('print-area');
    if (!area) {
      area = document.createElement('div');
      area.id = 'print-area';
      document.body.appendChild(area);
    }
    area.innerHTML = action.printHtml;
    window.print();
  };

  // ── Modal Open / Close ────────────────────────

  DTD.closeModal = function () {
    document.getElementById('modal-overlay').classList.add('hidden');
    var container = document.getElementById('modal-container');
    container.classList.add('hidden');
    container.innerHTML = '';
  };

  // Opens a bottom-sheet modal for a specific touchpoint type.
  // contactId: string
  // type: 'call' | 'text' | 'card' | 'social'
  DTD.openModal = function (contactId, type) {
    var contact = DTD.getContactById(contactId);
    if (!contact) return;

    // Track the open contact so actions inside the modal (e.g. Print Card,
    // opened from Dashboard/This Week) resolve to the right person.
    DTD.state.currentContactId = contactId;

    var info   = DTD.getCurrentQuarterInfo();
    var status = DTD.getTouchStatus(contactId, info.quarter, info.year);
    var isDone = status[type];

    var html = '';
    html += '<div class="modal-handle"></div>';
    html += '<div class="modal-header">';
    html += '  <span class="modal-header__title">' + DTD.escHtml(contact.firstName + ' ' + contact.lastName) + '</span>';
    html += '  <span class="modal-header__type ' + type + '">' + DTD.TOUCH_LABELS[type] + '</span>';
    html += '</div>';
    html += '<div class="modal-body">';

    switch (type) {
      case 'call':
        html += buildCallBody(contact);
        break;
      case 'text':
        html += buildTextBody(contact);
        break;
      case 'card':
        html += buildCardBody(contact);
        break;
      case 'social':
        html += buildSocialBody(contact);
        break;
    }

    html += '  <input class="modal-note-input" id="modal-note" type="text" placeholder="Optional note about this touchpoint…" />';
    html += '</div>';
    html += '<div class="modal-footer">';
    if (isDone) {
      html += '  <button class="mark-done-btn already-done" disabled>' +
              '  \u2713 Already logged this quarter</button>';
    } else {
      html += '  <button class="mark-done-btn" data-action="mark-done"' +
              '    data-contact-id="' + DTD.escHtml(contactId) + '"' +
              '    data-type="' + type + '">' +
              '  Mark Done \u2714</button>';
    }
    html += '  <button class="modal-close-btn" data-action="close-modal">Close</button>';
    html += '</div>';

    var container = document.getElementById('modal-container');
    container.innerHTML = html;
    container.classList.remove('hidden');
    document.getElementById('modal-overlay').classList.remove('hidden');
  };

  // ── Modal body builders ───────────────────────

  function buildCallBody(contact) {
    var action = DTD.buildCallAction(contact);
    var html = '';

    if (action.url) {
      html += '<a class="modal-action-btn" href="' + DTD.escHtml(action.url) + '">';
      html += '  <span style="color:var(--call-color)">' + DTD.ICONS.call + '</span>';
      html += '  <span class="modal-action-btn__text">Call ' + DTD.escHtml(contact.firstName) + '</span>';
      html += '  <span class="modal-action-btn__sub">' + DTD.escHtml(contact.phone) + '</span>';
      html += '</a>';
    } else {
      html += '<p style="color:var(--text-muted);font-size:1.3rem;margin-bottom:10px">No phone number on file.</p>';
    }

    html += '<div class="modal-script">' + DTD.escHtml(action.script) + '</div>';
    html += '<button class="modal-copy-btn" data-action="copy-text"' +
            '  data-text="' + DTD.escHtml(action.script) + '">' +
            '  ' + DTD.ICONS.copy + ' Copy Script</button>';

    return html;
  }

  function buildTextBody(contact) {
    var action = DTD.buildTextAction(contact);
    var html = '';

    if (action.url) {
      html += '<a class="modal-action-btn" href="' + DTD.escHtml(action.url) + '">';
      html += '  <span style="color:var(--text-color)">' + DTD.ICONS.text + '</span>';
      html += '  <span class="modal-action-btn__text">Open SMS to ' + DTD.escHtml(contact.firstName) + '</span>';
      html += '  <span class="modal-action-btn__sub">' + DTD.escHtml(contact.phone) + '</span>';
      html += '</a>';
    } else {
      html += '<p style="color:var(--text-muted);font-size:1.3rem;margin-bottom:10px">No phone number on file.</p>';
    }

    html += '<div class="modal-script">' + DTD.escHtml(action.preview) + '</div>';
    html += '<button class="modal-copy-btn" data-action="copy-text"' +
            '  data-text="' + DTD.escHtml(action.preview) + '">' +
            '  ' + DTD.ICONS.copy + ' Copy Message</button>';

    return html;
  }

  function buildCardBody(contact) {
    var action = DTD.buildNoteCardAction(contact);
    var html = '';

    // Address block
    html += '<div style="font-size:1.2rem;color:var(--text-muted);margin-bottom:6px">SEND TO</div>';
    if (action.address) {
      html += '<div class="address-block">' +
              DTD.escHtml(contact.firstName + ' ' + contact.lastName) + '\n' +
              DTD.escHtml(action.address) +
              '</div>';
    } else {
      html += '<div class="address-block" style="color:var(--text-muted)">No address on file</div>';
    }
    html += '<button class="modal-copy-btn" data-action="copy-text"' +
            '  data-text="' + DTD.escHtml(contact.firstName + ' ' + contact.lastName + '\n' + action.address) + '">' +
            '  ' + DTD.ICONS.copy + ' Copy Address</button>';

    // Note body
    html += '<div style="font-size:1.2rem;color:var(--text-muted);margin:10px 0 6px">NOTE BODY</div>';
    html += '<div class="modal-script">' + DTD.escHtml(action.body) + '</div>';
    html += '<button class="modal-copy-btn" data-action="copy-text"' +
            '  data-text="' + DTD.escHtml(action.body) + '">' +
            '  ' + DTD.ICONS.copy + ' Copy Note</button>';
    html += '<button class="modal-copy-btn" data-action="print-card">' +
            '  ' + DTD.ICONS.print + ' Print Card</button>';

    return html;
  }

  function buildSocialBody(contact) {
    var action = DTD.buildSocialAction(contact);
    var email  = DTD.buildEmailAction(contact);
    var html   = '';
    var links  = action.links;

    var hasLinks = Object.keys(links).length > 0;
    var hasEmail = !!email.url;

    // Email is part of this touch (the "Email / Social" slot) — surface it so
    // a contact with an email but no social handles still has an action.
    if (hasEmail) {
      html += '<a class="modal-action-btn" href="' + DTD.escHtml(email.url) + '">';
      html += '  <span style="color:var(--social-color)">' + DTD.ICONS.card + '</span>';
      html += '  <span class="modal-action-btn__text">Email ' + DTD.escHtml(contact.firstName) + '</span>';
      html += '  <span class="modal-action-btn__sub">' + DTD.escHtml(contact.email) + '</span>';
      html += '</a>';
    }

    if (hasLinks) {
      html += '<div class="modal-social-links">';
      Object.keys(links).forEach(function (platform) {
        var link = links[platform];
        html += '<a class="modal-action-btn" href="' + DTD.escHtml(link.url) + '" target="_blank" rel="noopener">';
        html += '  <span style="color:var(--social-color)">' + DTD.ICONS.social + '</span>';
        html += '  <span class="modal-action-btn__text">' + DTD.escHtml(link.label) + '</span>';
        html += '  <span class="modal-action-btn__sub">' + DTD.escHtml(link.handle) + '</span>';
        html += '</a>';
      });
      html += '</div>';
    }

    if (!hasLinks && !hasEmail) {
      html += '<p style="color:var(--text-muted);font-size:1.3rem;margin-bottom:10px">No email or social handles on file.</p>';
    }

    html += '<div style="font-size:1.2rem;color:var(--text-muted);margin-bottom:6px">COPY MESSAGE</div>';
    html += '<div class="modal-script">' + DTD.escHtml(action.copyText) + '</div>';
    html += '<button class="modal-copy-btn" data-action="copy-text"' +
            '  data-text="' + DTD.escHtml(action.copyText) + '">' +
            '  ' + DTD.ICONS.copy + ' Copy Message</button>';

    return html;
  }

})(window.DTD = window.DTD || {});
