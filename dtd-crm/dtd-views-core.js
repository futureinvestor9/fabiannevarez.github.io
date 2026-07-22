/* ================================================
   DTD — View Render Engine + Dashboard + This Week
   ================================================
   Depends on: all previous modules
   ================================================ */
(function (DTD) {
  'use strict';

  // ── Shared HTML Helpers ───────────────────────

  // Build the 4 status dots for a contact (filled = done this quarter)
  DTD.buildTouchDots = function (contactId) {
    var info   = DTD.getCurrentQuarterInfo();
    var status = DTD.getTouchStatus(contactId, info.quarter, info.year);
    var html   = '';
    DTD.TOUCH_TYPES.forEach(function (t) {
      html += '<span class="touch-dot touch-' + t + (status[t] ? ' done' : '') + '"></span>';
    });
    return html;
  };

  // Build the 4 touchpoint action buttons for a contact card
  DTD.buildTouchButtons = function (contactId) {
    var info    = DTD.getCurrentQuarterInfo();
    var status  = DTD.getTouchStatus(contactId, info.quarter, info.year);
    var contact = DTD.getContactById(contactId);
    // The one touch this contact is scheduled for this week \u2014 highlight it so
    // it's clear which button advances weekly progress (the others are
    // available as catch-up touches but don't count toward this week).
    var dueType = contact ? DTD.getTouchTypeThisWeek(contact) : null;
    var html    = '';
    DTD.TOUCH_TYPES.forEach(function (t) {
      var done  = status[t];
      var isDue = (t === dueType);
      var label = DTD.TOUCH_LABELS[t];
      html += '<button class="touch-btn touch-btn-' + t + (done ? ' done' : '') + (isDue ? ' due' : '') + '"' +
              '  data-action="open-touchpoint"' +
              '  data-contact-id="' + DTD.escHtml(contactId) + '"' +
              '  data-type="' + t + '"' +
              (isDue ? ' aria-label="' + DTD.escHtml(label) + ', due this week"' : '') + '>' +
              DTD.ICONS[t] + '<span>' + label + (isDue ? ' \u00b7 Due' : '') + (done ? ' \u2713' : '') + '</span>' +
              '</button>';
    });
    return html;
  };

  // Full contact card (used on Dashboard and This Week)
  DTD.buildContactCard = function (contact) {
    var initials = DTD.getInitials(contact);
    var group    = DTD.getLetterGroup(contact.lastName);
    var phone    = contact.phone ? contact.phone : '';
    var html     = '';

    html += '<div class="contact-card">';
    html += '  <div class="contact-card__head">';
    html += '    <div class="contact-card__avatar">' + DTD.escHtml(initials) + '</div>';
    html += '    <div class="contact-card__info">';
    html += '      <div class="contact-card__name">' +
            DTD.escHtml(contact.firstName + ' ' + contact.lastName) + '</div>';
    html += '      <div class="contact-card__meta">' +
            DTD.escHtml(phone || group) + '</div>';
    html += '    </div>';
    html += '    <div class="contact-card__dots">' + DTD.buildTouchDots(contact.id) + '</div>';
    html += '    <button style="padding:8px;color:var(--text-muted)" ' +
            '      data-action="open-contact" data-contact-id="' + DTD.escHtml(contact.id) + '">' +
            '      ' + DTD.ICONS.back.replace('15 18 9 12 15 6', '9 18 15 12 9 6') + '</button>';
    html += '  </div>';
    html += '  <div class="contact-card__actions">' + DTD.buildTouchButtons(contact.id) + '</div>';
    html += '</div>';
    return html;
  };

  // ── Render Engine ─────────────────────────────

  DTD.renderView = function (viewName, params) {
    DTD.state.currentView = viewName;

    // Update tab bar active state
    document.querySelectorAll('.tab-btn').forEach(function (btn) {
      btn.classList.toggle('active', btn.dataset.tab === viewName);
    });

    // Dispatch to the right renderer
    switch (viewName) {
      case 'dashboard':   DTD.renderDashboard();           break;
      case 'thisWeek':    DTD.renderThisWeek();            break;
      case 'contacts':    DTD.renderContacts();            break;
      case 'detail':      DTD.renderDetail(params);        break;
      case 'form':        DTD.renderForm(params);          break;
      case 'settings':    DTD.renderSettings();            break;
      case 'import':      DTD.renderImport();              break;
      case 'plans':       DTD.renderPlans();               break;
      default:            DTD.renderDashboard();           break;
    }
  };

  // ── Dashboard ─────────────────────────────────

  DTD.renderDashboard = function () {
    var info   = DTD.getCurrentQuarterInfo();
    var groups = DTD.getGroupsThisWeek();
    var prog   = DTD.getWeekProgress(groups);
    var rot    = info.weekRotation;

    var pct    = prog.total > 0 ? Math.round((prog.weekDone / prog.total) * 100) : 0;
    var r      = 32;
    var circ   = 2 * Math.PI * r;
    var offset = circ - (pct / 100) * circ;

    // Gather this week's contacts (all 4 groups)
    var contacts = [];
    groups.forEach(function (g) {
      DTD.getContactsByGroup(g).forEach(function (c) { contacts.push(c); });
    });
    var preview = contacts.slice(0, 5);

    var html = '<div class="view-dashboard">';

    // Week Banner
    html += '<div class="week-banner">';
    html += '  <div class="week-banner__label">Q' + info.quarter + ' ' + info.year + ' &nbsp;&bull;&nbsp; Week ' + info.weekNum + ' of 13</div>';
    html += '  <div class="week-banner__title">This Week\'s Rotation</div>';
    html += '  <div class="week-banner__meta">' +
            '<span style="color:var(--call-color)">Call: ' + rot.call + '</span> &nbsp;' +
            '<span style="color:var(--text-color)">Text: ' + rot.text + '</span> &nbsp;' +
            '<span style="color:var(--card-color)">Card: ' + rot.card + '</span> &nbsp;' +
            '<span style="color:var(--social-color)">Social: ' + rot.social + '</span>' +
            '</div>';
    html += '  <div class="week-banner__meta" style="margin-top:6px">' +
            DTD.formatWeekDate(info.weekStartDate) + ' – ' + DTD.formatWeekDate(info.weekEndDate) +
            '</div>';
    html += '</div>';

    // Progress ring + stats
    html += '<div class="progress-ring-wrap">';
    html += '  <div class="progress-ring">';
    html += '    <svg width="80" height="80">';
    html += '      <circle class="progress-ring__track" cx="40" cy="40" r="' + r + '" stroke-width="6" fill="none"/>';
    html += '      <circle class="progress-ring__fill"  cx="40" cy="40" r="' + r + '" stroke-width="6" fill="none"' +
            '        stroke-dasharray="' + circ.toFixed(1) + '"' +
            '        stroke-dashoffset="' + offset.toFixed(1) + '"/>';
    html += '    </svg>';
    html += '    <div class="progress-ring__label">' + pct + '%<small>done</small></div>';
    html += '  </div>';
    html += '  <div class="progress-stats">';
    html += '    <div class="progress-stats__row"><span>Contacts this week</span><span class="progress-stats__val">' + prog.total + '</span></div>';
    html += '    <div class="progress-stats__row"><span>Done this week</span><span class="progress-stats__val">' + prog.weekDone + '</span></div>';
    html += '    <div class="progress-stats__row"><span>Q' + info.quarter + ' quarter</span><span class="progress-stats__val">' + info.year + '</span></div>';
    html += '  </div>';
    html += '</div>';

    // Per-type pill counts
    html += '<div class="dash-touchtype-row">';
    DTD.TOUCH_TYPES.forEach(function (t) {
      html += '<div class="dash-touchtype-pill ' + t + '">';
      html += '  <span class="dash-touchtype-pill__icon">' + DTD.ICONS[t] + '</span>';
      html += '  <span class="dash-touchtype-pill__count">' + prog.byType[t] + '</span>';
      html += '  <span class="dash-touchtype-pill__label">' + DTD.TOUCH_LABELS[t] + '</span>';
      html += '</div>';
    });
    html += '</div>';

    // Preview contact cards
    if (contacts.length === 0) {
      html += '<div class="empty-state">' +
              '  <span class="empty-state__icon">&#128100;</span>' +
              '  <div class="empty-state__title">No contacts yet</div>' +
              '  <div class="empty-state__sub">Add contacts to get started</div>' +
              '</div>';
    } else {
      html += '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">';
      html += '  <span style="font-size:1.3rem;font-weight:600;color:var(--white)">This Week\'s Contacts</span>';
      if (contacts.length > 5) {
        html += '  <button data-action="open-tab" data-tab="thisWeek"' +
                '    style="font-size:1.2rem;color:var(--pink)">See all ' + contacts.length + ' →</button>';
      }
      html += '</div>';
      preview.forEach(function (c) { html += DTD.buildContactCard(c); });
    }

    html += '</div>';
    document.getElementById('app').innerHTML = html;

    // Update header
    document.getElementById('header-subtitle').textContent = 'Q' + info.quarter + ' · Week ' + info.weekNum;
    document.getElementById('header-action-btn').innerHTML  = DTD.ICONS.settings;
    document.getElementById('header-action-btn').dataset.action = 'open-tab';
    document.getElementById('header-action-btn').dataset.tab    = 'settings';
  };

  // ── This Week ─────────────────────────────────

  DTD.renderThisWeek = function () {
    var info   = DTD.getCurrentQuarterInfo();
    var rot    = info.weekRotation;
    var groups = DTD.getGroupsThisWeek();

    var html = '<div class="view-this-week">';

    // Week schedule badges
    html += '<div class="week-header-band">';
    html += '  <span class="week-header-band__title">Week ' + info.weekNum + '</span>';
    html += '  <span class="week-header-band__meta">' +
            DTD.formatWeekDate(info.weekStartDate) + ' – ' +
            DTD.formatWeekDate(info.weekEndDate) + '</span>';
    html += '</div>';
    html += '<div class="week-schedule">';
    html += '  <span class="week-schedule__badge call">Call: ' + rot.call + '</span>';
    html += '  <span class="week-schedule__badge text">Text: ' + rot.text + '</span>';
    html += '  <span class="week-schedule__badge card">Card: ' + rot.card + '</span>';
    html += '  <span class="week-schedule__badge social">Social: ' + rot.social + '</span>';
    html += '</div>';

    // One section per group in rotation order
    var typeOrder = ['call', 'text', 'card', 'social'];
    var hasAny    = false;

    typeOrder.forEach(function (touchType) {
      var group    = rot[touchType];
      var contacts = DTD.getContactsByGroup(group);
      if (contacts.length === 0) return;
      hasAny = true;

      html += '<div class="section-header" style="color:var(--' + touchType + '-color)">' +
              DTD.TOUCH_LABELS[touchType].toUpperCase() + ' — Group ' + group +
              ' <span style="color:var(--text-muted);font-weight:400">(' + contacts.length + ')</span></div>';
      contacts.forEach(function (c) { html += DTD.buildContactCard(c); });
    });

    if (!hasAny) {
      html += '<div class="empty-state">' +
              '  <span class="empty-state__icon">&#128197;</span>' +
              '  <div class="empty-state__title">No contacts in these groups</div>' +
              '  <div class="empty-state__sub">Add contacts with last names in ' + groups.join(', ') + '</div>' +
              '</div>';
    }

    html += '</div>';
    document.getElementById('app').innerHTML = html;

    document.getElementById('header-subtitle').textContent = 'Week ' + info.weekNum + ' — ' + groups.join(' · ');
    document.getElementById('header-action-btn').innerHTML  = DTD.ICONS.plus;
    document.getElementById('header-action-btn').dataset.action = 'open-add-contact';
    document.getElementById('header-action-btn').dataset.tab    = '';
  };

})(window.DTD = window.DTD || {});
