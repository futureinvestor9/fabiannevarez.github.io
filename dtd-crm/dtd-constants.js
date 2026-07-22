/* ================================================
   DTD — Constants, Rotation Table, Icons, Defaults
   ================================================ */
(function (DTD) {
  'use strict';

  // Maps each last-name initial to its 2-letter group code
  DTD.LETTER_TO_GROUP = {
    A:'AW', B:'BE', C:'CK', D:'DO', E:'BE', F:'FG', G:'FG',
    H:'HV', I:'IQ', J:'TJ', K:'CK', L:'PL', M:'MX', N:'NR',
    O:'DO', P:'PL', Q:'IQ', R:'NR', S:'SU', T:'TJ', U:'SU',
    V:'HV', W:'AW', X:'MX', Y:'YZ', Z:'YZ'
  };

  // 13-week rotation — which group does each touchpoint type this week.
  // Built as a full rotation over all 13 groups so that every group receives
  // each of the 4 touch types exactly once across the quarter (4 touches / 16
  // per year per contact) — no group is left out and none is doubled up.
  DTD.WEEK_ROTATION = [
    { call:'AW', text:'BE', card:'CK', social:'DO' }, // Week 1
    { call:'BE', text:'CK', card:'DO', social:'FG' }, // Week 2
    { call:'CK', text:'DO', card:'FG', social:'HV' }, // Week 3
    { call:'DO', text:'FG', card:'HV', social:'IQ' }, // Week 4
    { call:'FG', text:'HV', card:'IQ', social:'MX' }, // Week 5
    { call:'HV', text:'IQ', card:'MX', social:'NR' }, // Week 6
    { call:'IQ', text:'MX', card:'NR', social:'PL' }, // Week 7
    { call:'MX', text:'NR', card:'PL', social:'SU' }, // Week 8
    { call:'NR', text:'PL', card:'SU', social:'TJ' }, // Week 9
    { call:'PL', text:'SU', card:'TJ', social:'YZ' }, // Week 10
    { call:'SU', text:'TJ', card:'YZ', social:'AW' }, // Week 11
    { call:'TJ', text:'YZ', card:'AW', social:'BE' }, // Week 12
    { call:'YZ', text:'AW', card:'BE', social:'CK' }, // Week 13
  ];

  // All 13 group codes in a stable order (for UI display)
  DTD.ALL_GROUPS = ['AW','BE','CK','DO','FG','HV','IQ','MX','NR','PL','SU','TJ','YZ'];

  // The 4 touchpoint types in order
  DTD.TOUCH_TYPES = ['call', 'text', 'card', 'social'];

  // Human-readable labels for each type
  DTD.TOUCH_LABELS = {
    call:   'Call',
    text:   'Text',
    card:   'Note Card',
    social: 'Social'
  };

  // Default settings & message templates
  DTD.DEFAULT_SETTINGS = {
    quarterStartDate: '2026-01-01',
    userName: 'Fabian',
    defaultTemplates: {
      call:   'Hi [firstName], this is Fabian calling to check in! How are things going?',
      text:   'Hey [firstName]! Just thinking of you and wanted to say hi. Hope all is well! \uD83D\uDE0A',
      email:  'Subject: Checking in!\n\nHi [firstName],\n\nJust wanted to reach out and see how you\'re doing. Hope life is treating you well!\n\nBest,\nFabian',
      social: 'Hey [firstName], great content lately! Hope you\'re doing well!',
      note:   'Dear [firstName],\n\nJust wanted to take a moment to reach out and let you know I\'m thinking of you. Hope all is well!\n\nWarmly,\nFabian'
    }
  };

  // localStorage key names
  DTD.KEYS = {
    contacts:  'dtd_contacts',
    touchlogs: 'dtd_touchlogs',
    settings:  'dtd_settings'
  };

  // Inline SVG icon strings (stroke-based, currentColor)
  DTD.ICONS = {
    call:
      '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
      '<path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07' +
      'A19.5 19.5 0 013.07 9.81a19.79 19.79 0 01-3.07-8.7A2 2 0 012.18 1h3' +
      'a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L6.91 8.16' +
      'a16 16 0 006.93 6.93l1.52-1.52a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7' +
      'A2 2 0 0122 16.92z"/></svg>',

    text:
      '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
      '<path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>',

    card:
      '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
      '<path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>' +
      '<polyline points="22,6 12,13 2,6"/></svg>',

    social:
      '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
      '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>' +
      '<line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/>' +
      '<line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>',

    edit:
      '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
      '<path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>' +
      '<path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>',

    trash:
      '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
      '<polyline points="3 6 5 6 21 6"/>' +
      '<path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/>' +
      '<path d="M10 11v6M14 11v6"/><path d="M9 6V4h6v2"/></svg>',

    plus:
      '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
      '<line x1="12" y1="5" x2="12" y2="19"/>' +
      '<line x1="5" y1="12" x2="19" y2="12"/></svg>',

    back:
      '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
      '<polyline points="15 18 9 12 15 6"/></svg>',

    copy:
      '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
      '<rect x="9" y="9" width="13" height="13" rx="2"/>' +
      '<path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>',

    print:
      '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
      '<polyline points="6 9 6 2 18 2 18 9"/>' +
      '<path d="M6 18H4a2 2 0 01-2-2v-5a2 2 0 012-2h16a2 2 0 012 2v5a2 2 0 01-2 2h-2"/>' +
      '<rect x="6" y="14" width="12" height="8"/></svg>',

    check:
      '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
      '<polyline points="20 6 9 17 4 12"/></svg>',

    close:
      '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
      '<line x1="18" y1="6" x2="6" y2="18"/>' +
      '<line x1="6" y1="6" x2="18" y2="18"/></svg>',

    search:
      '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
      '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',

    settings:
      '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
      '<circle cx="12" cy="12" r="3"/>' +
      '<path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06' +
      'a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4' +
      'a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15' +
      'a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82' +
      'l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3' +
      'a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06' +
      'a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21' +
      'a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>'
  };

})(window.DTD = window.DTD || {});
