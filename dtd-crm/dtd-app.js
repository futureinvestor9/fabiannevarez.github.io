/* ================================================
   DTD — App Entry Point
   Event delegation + keyboard shortcuts + init
   ================================================
   Depends on: ALL other dtd-*.js modules
   Load this LAST.
   ================================================ */
(function (DTD) {
  'use strict';

  // ── Single delegated click handler ───────────
  // All interactive elements carry data-action="…" attributes.
  // This one listener handles the entire app.

  document.addEventListener('click', function (e) {
    // Walk up the DOM to find the nearest data-action ancestor
    var target = e.target;
    var el     = target;
    while (el && !el.dataset.action) { el = el.parentElement; }
    if (!el) return;

    var action    = el.dataset.action;
    var contactId = el.dataset.contactId || DTD.state.currentContactId;
    var type      = el.dataset.type;
    var tab       = el.dataset.tab;
    var group     = el.dataset.group;
    var text      = el.dataset.text;

    switch (action) {

      // ── Navigation ─────────────────────────
      case 'open-tab':
        DTD.state.searchQuery = '';
        DTD.renderView(tab);
        break;

      case 'open-contact':
        DTD.state.currentContactId = contactId;
        DTD.renderDetail(contactId);
        break;

      case 'open-add-contact':
        DTD.state.currentContactId = null;
        DTD.renderForm(null);
        break;

      case 'open-edit-contact':
        DTD.renderForm(contactId);
        break;

      case 'cancel-form':
        if (contactId) {
          DTD.renderDetail(contactId);
        } else {
          DTD.renderContacts();
        }
        break;

      case 'nav-back':
        // From detail → contacts; from form → previous
        DTD.renderContacts();
        break;

      // ── Touchpoints ────────────────────────
      case 'open-touchpoint':
        DTD.openModal(contactId, type);
        break;

      case 'close-modal':
        DTD.closeModal();
        break;

      case 'mark-done': {
        var noteEl = document.getElementById('modal-note');
        var note   = noteEl ? noteEl.value.trim() : '';
        DTD.logTouchpoint(contactId, type, note);
        DTD.closeModal();
        DTD.showToast(DTD.TOUCH_LABELS[type] + ' logged \u2713', 'success');

        // Refresh current view so dots update without full navigation
        var cv = DTD.state.currentView;
        if (cv === 'detail') {
          DTD.renderDetail(contactId);
        } else if (cv === 'thisWeek') {
          DTD.renderThisWeek();
        } else {
          DTD.renderDashboard();
        }
        break;
      }

      // ── Contacts ───────────────────────────
      case 'delete-contact':
        DTD.showConfirm(
          'Delete this contact and all their touch logs?',
          function () {
            DTD.deleteContact(contactId);
            DTD.showToast('Contact deleted', '');
            DTD.renderContacts();
          }
        );
        break;

      case 'filter-group':
        DTD.state.filterGroup  = group;
        DTD.state.searchQuery  = '';
        DTD.renderContacts();
        break;

      // ── Settings ───────────────────────────
      case 'save-settings':
        DTD.handleSaveSettings();
        break;

      case 'reset-template':
        DTD.handleResetTemplate(type);
        break;

      case 'export-contacts':
        DTD.exportContactsToCSV();
        DTD.showToast('Contacts exported', 'success');
        break;

      case 'export-logs':
        DTD.exportTouchlogsToCSV();
        DTD.showToast('Touch log exported', 'success');
        break;

      case 'go-import':
        DTD.state.csvData = null;
        DTD.renderImport();
        break;

      case 'confirm-import':
        DTD.handleConfirmImport();
        break;

      case 'reset-import':
        DTD.state.csvData = null;
        DTD.renderImport();
        break;

      // ── Utilities ──────────────────────────
      case 'copy-text':
        if (navigator.clipboard && text) {
          navigator.clipboard.writeText(text).then(function () {
            DTD.showToast('Copied!', 'success');
          }).catch(function () {
            DTD.showToast('Copy failed', 'error');
          });
        }
        break;

      case 'print-card': {
        var pcContact = DTD.getContactById(DTD.state.currentContactId);
        if (pcContact) { DTD.printNoteCard(pcContact); }
        break;
      }

      // ── Confirm dialog ─────────────────────
      case 'confirm-ok': {
        // Capture the callback before closeConfirm() clears it, or the
        // confirmed action (e.g. delete-contact) never runs.
        var confirmCb = DTD.state.confirmCallback;
        DTD.closeConfirm();
        if (typeof confirmCb === 'function') { confirmCb(); }
        break;
      }

      case 'confirm-cancel':
        DTD.closeConfirm();
        break;
    }
  });

  // ── Tab bar wiring ────────────────────────────
  // Tab buttons use data-tab directly; the click handler above covers them.
  // But we also want to reset search state on tab switch.
  document.querySelectorAll('.tab-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      DTD.state.searchQuery = '';
      DTD.state.filterGroup = 'all';
      DTD.renderView(this.dataset.tab);
    });
  });

  // ── Confirm overlay click to close ────────────
  document.getElementById('confirm-overlay').addEventListener('click', function () {
    DTD.closeConfirm();
  });

  // ── Init ─────────────────────────────────────

  function init() {
    // Ensure settings exist (seeds defaults on first run)
    var settings = DTD.getSettings();
    DTD.saveSettings(settings);

    // Boot to dashboard
    DTD.renderView('dashboard');
  }

  document.addEventListener('DOMContentLoaded', init);

})(window.DTD = window.DTD || {});
