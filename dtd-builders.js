/* ================================================
   DTD — Automation Builders
   Produce ready-to-use URLs and pre-filled content
   for each of the 4 touchpoint types.
   ================================================
   Depends on: dtd-constants.js, dtd-storage.js, dtd-touchpoints.js
   ================================================ */
(function (DTD) {
  'use strict';

  // ── Call ─────────────────────────────────────

  DTD.buildCallAction = function (contact) {
    var settings = DTD.getSettings();
    var script   = DTD.fillTemplate(settings.defaultTemplates.call, contact);
    var phone    = (contact.phone || '').replace(/\s+/g, '');
    return {
      url:    phone ? 'tel:' + phone : null,
      script: script
    };
  };

  // ── Text / SMS ────────────────────────────────

  DTD.buildTextAction = function (contact) {
    var settings = DTD.getSettings();
    var body     = DTD.fillTemplate(settings.defaultTemplates.text, contact);
    var phone    = (contact.phone || '').replace(/\s+/g, '');
    // sms: URI — works on iOS and Android
    var url = phone ? 'sms:' + phone + (body ? '?body=' + encodeURIComponent(body) : '') : null;
    return { url: url, preview: body };
  };

  // ── Email ─────────────────────────────────────

  DTD.buildEmailAction = function (contact) {
    var settings  = DTD.getSettings();
    var template  = settings.defaultTemplates.email || '';
    var filled    = DTD.fillTemplate(template, contact);

    // First line may be "Subject: ..." — split it out
    var subject = '';
    var body    = filled;
    var lines   = filled.split('\n');
    if (lines[0] && lines[0].toLowerCase().startsWith('subject:')) {
      subject = lines[0].replace(/^subject:\s*/i, '').trim();
      body    = lines.slice(1).join('\n').replace(/^\n+/, '');
    }

    var url = contact.email
      ? 'mailto:' + encodeURIComponent(contact.email) +
        '?subject=' + encodeURIComponent(subject) +
        '&body='    + encodeURIComponent(body)
      : null;

    return { url: url, subject: subject, body: body, preview: filled };
  };

  // ── Social ────────────────────────────────────

  DTD.buildSocialAction = function (contact) {
    var settings  = DTD.getSettings();
    var copyText  = DTD.fillTemplate(settings.defaultTemplates.social, contact);

    // Build clickable profile links only for handles that are set
    var links = {};

    if (contact.instagram) {
      var ig = contact.instagram.replace(/^@/, '');
      links.instagram = { label: 'Instagram', url: 'https://instagram.com/' + encodeURIComponent(ig), handle: '@' + ig };
    }
    if (contact.linkedin) {
      // Accept full URLs or just a username
      var li = contact.linkedin.startsWith('http')
        ? contact.linkedin
        : 'https://' + contact.linkedin;
      links.linkedin = { label: 'LinkedIn', url: li, handle: contact.linkedin };
    }
    if (contact.facebook) {
      var fb = contact.facebook.startsWith('http')
        ? contact.facebook
        : 'https://' + contact.facebook;
      links.facebook = { label: 'Facebook', url: fb, handle: contact.facebook };
    }
    if (contact.twitter) {
      var tw = contact.twitter.replace(/^@/, '');
      links.twitter = { label: 'X / Twitter', url: 'https://x.com/' + encodeURIComponent(tw), handle: '@' + tw };
    }

    return { links: links, copyText: copyText };
  };

  // ── Note Card ─────────────────────────────────

  DTD.buildNoteCardAction = function (contact) {
    var settings = DTD.getSettings();
    var body     = DTD.fillTemplate(settings.defaultTemplates.note, contact);
    return {
      address:   contact.address || '',
      body:      body,
      // Minimal HTML for the print pane — styled by @media print rules in CSS
      printHtml: '<div class="address-block">' +
                   DTD.escHtml(contact.firstName) + ' ' + DTD.escHtml(contact.lastName) + '<br>' +
                   DTD.escHtml(contact.address || '(no address on file)').replace(/,\s*/g, '<br>') +
                 '</div>' +
                 '<div class="print-note-body">' + DTD.escHtml(body) + '</div>'
    };
  };

})(window.DTD = window.DTD || {});
