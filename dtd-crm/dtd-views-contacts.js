/* ================================================
   DTD — Contact List · Contact Detail · Add/Edit Form
   ================================================
   Depends on: all previous modules + dtd-views-core.js
   ================================================ */
(function (DTD) {
  'use strict';

  // ── Contact List ──────────────────────────────

  DTD.renderContacts = function () {
    var query    = DTD.state.searchQuery;
    var filter   = DTD.state.filterGroup;
    var contacts = query ? DTD.searchContacts(query) : DTD.getContacts();

    if (filter !== 'all') {
      contacts = contacts.filter(function (c) {
        return DTD.getLetterGroup(c.lastName) === filter;
      });
    }

    var info = DTD.getCurrentQuarterInfo();
    var html = '<div class="view-contacts">';

    // Search bar
    html += '<div class="search-bar">';
    html += '  <span class="search-bar__icon">' + DTD.ICONS.search + '</span>';
    html += '  <input class="search-bar__input" id="contact-search" type="search"' +
            '    placeholder="Search contacts…" value="' + DTD.escHtml(query) + '" />';
    html += '</div>';

    // Filter chips
    html += '<div class="filter-chips">';
    html += '  <button class="filter-chip' + (filter === 'all' ? ' active' : '') + '"' +
            '    data-action="filter-group" data-group="all">All</button>';
    DTD.ALL_GROUPS.forEach(function (g) {
      html += '  <button class="filter-chip' + (filter === g ? ' active' : '') + '"' +
              '    data-action="filter-group" data-group="' + g + '">' + g + '</button>';
    });
    html += '</div>';

    // Contact rows grouped by first letter of lastName
    if (contacts.length === 0) {
      html += '<div class="empty-state">' +
              '  <span class="empty-state__icon">&#128269;</span>' +
              '  <div class="empty-state__title">' +
                   (query ? 'No results for "' + DTD.escHtml(query) + '"' : 'No contacts yet') +
              '  </div>' +
              '  <div class="empty-state__sub">' +
                   (query ? 'Try a different search' : 'Tap + to add your first contact') +
              '  </div>' +
              '</div>';
    } else {
      var lastAlpha = '';
      contacts.forEach(function (c) {
        var alpha = (c.lastName || '?').charAt(0).toUpperCase();
        if (alpha !== lastAlpha) {
          lastAlpha = alpha;
          html += '<div class="alpha-header">' + DTD.escHtml(alpha) + '</div>';
        }
        var status  = DTD.getTouchStatus(c.id, info.quarter, info.year);
        var group   = DTD.getLetterGroup(c.lastName);
        var phone   = c.phone || c.email || group;
        html += '<div class="contact-row" data-action="open-contact" data-contact-id="' + DTD.escHtml(c.id) + '">';
        html += '  <div class="contact-row__avatar">' + DTD.escHtml(DTD.getInitials(c)) + '</div>';
        html += '  <div class="contact-row__info">';
        html += '    <div class="contact-row__name">' + DTD.escHtml(c.firstName + ' ' + c.lastName) + '</div>';
        html += '    <div class="contact-row__sub">' + DTD.escHtml(phone) + '</div>';
        html += '  </div>';
        html += '  <div class="contact-row__dots">';
        DTD.TOUCH_TYPES.forEach(function (t) {
          html += '<span class="touch-dot touch-' + t + (status[t] ? ' done' : '') + '"></span>';
        });
        html += '  </div>';
        html += '  <span class="contact-row__chevron">' + DTD.ICONS.back.replace('15 18 9 12 15 6', '9 18 15 12 9 6') + '</span>';
        html += '</div>';
      });
    }

    html += '</div>';

    // FAB
    html += '<button class="fab" data-action="open-add-contact" aria-label="Add contact">' +
            DTD.ICONS.plus + '</button>';

    document.getElementById('app').innerHTML = html;

    // Wire search input
    var searchEl = document.getElementById('contact-search');
    if (searchEl) {
      searchEl.addEventListener('input', function () {
        DTD.state.searchQuery = this.value;
        DTD.renderContacts();
        // Re-focus and restore cursor
        var el = document.getElementById('contact-search');
        if (el) { el.focus(); el.setSelectionRange(9999, 9999); }
      });
    }

    document.getElementById('header-subtitle').textContent = contacts.length + ' contacts';
    document.getElementById('header-action-btn').innerHTML  = DTD.ICONS.plus;
    document.getElementById('header-action-btn').dataset.action = 'open-add-contact';
    document.getElementById('header-action-btn').dataset.tab    = '';
  };

  // ── Contact Detail ────────────────────────────

  DTD.renderDetail = function (contactId) {
    DTD.state.currentContactId = contactId;
    var contact = DTD.getContactById(contactId);
    if (!contact) { DTD.renderContacts(); return; }

    var info     = DTD.getCurrentQuarterInfo();
    var status   = DTD.getTouchStatus(contactId, info.quarter, info.year);
    var group    = DTD.getLetterGroup(contact.lastName);
    var logs     = DTD.getContactLogs(contactId).slice(0, 10);
    var initials = DTD.getInitials(contact);

    var html = '<div class="view-detail">';

    // Hero
    html += '<div class="detail-hero">';
    html += '  <div class="detail-hero__avatar">' + DTD.escHtml(initials) + '</div>';
    html += '  <div>';
    html += '    <div class="detail-hero__name">' + DTD.escHtml(contact.firstName + ' ' + contact.lastName) + '</div>';
    html += '    <div class="detail-hero__group">Group ' + group + ' &nbsp;·&nbsp; Q' + info.quarter + '</div>';
    html += '  </div>';
    html += '</div>';

    // 4 large touch buttons
    html += '<div class="detail-touch-row">';
    DTD.TOUCH_TYPES.forEach(function (t) {
      var done = status[t];
      html += '<button class="detail-touch-btn detail-touch-btn-' + t + (done ? ' done' : '') + '"' +
              '  data-action="open-touchpoint"' +
              '  data-contact-id="' + DTD.escHtml(contactId) + '"' +
              '  data-type="' + t + '">' +
              DTD.ICONS[t] +
              '<span>' + DTD.TOUCH_LABELS[t] + (done ? ' \u2713' : '') + '</span>' +
              '</button>';
    });
    html += '</div>';

    // Info card
    html += '<div class="info-card">';
    function infoRow(label, value, action, actionLabel) {
      if (!value) return '';
      var row = '<div class="info-row">';
      row += '<span class="info-row__label">' + label + '</span>';
      row += '<span class="info-row__value">' + DTD.escHtml(value) + '</span>';
      if (action) {
        row += '<a class="info-row__action" href="' + action + '">' + actionLabel + '</a>';
      }
      row += '</div>';
      return row;
    }

    if (contact.phone)     html += infoRow('Phone',   contact.phone,    'tel:' + contact.phone, 'Call');
    if (contact.email)     html += infoRow('Email',   contact.email,    'mailto:' + contact.email, 'Email');
    if (contact.address)   html += infoRow('Address', contact.address,  null, null);
    if (contact.instagram) html += infoRow('Instagram', contact.instagram, 'https://instagram.com/' + contact.instagram.replace(/^@/, ''), 'Open');
    if (contact.linkedin)  html += infoRow('LinkedIn', contact.linkedin,
      contact.linkedin.startsWith('http') ? contact.linkedin : 'https://' + contact.linkedin, 'Open');
    if (contact.facebook)  html += infoRow('Facebook', contact.facebook,
      contact.facebook.startsWith('http') ? contact.facebook : 'https://' + contact.facebook, 'Open');
    if (contact.twitter)   html += infoRow('Twitter', contact.twitter, 'https://x.com/' + contact.twitter.replace(/^@/, ''), 'Open');
    if (contact.notes)     html += infoRow('Notes',   contact.notes,    null, null);
    if (!contact.phone && !contact.email && !contact.address) {
      html += '<div class="info-row" style="color:var(--text-muted)">No contact info on file</div>';
    }
    html += '</div>';

    // Touch log
    html += '<div class="section-header">Touchpoint History</div>';
    if (logs.length === 0) {
      html += '<p style="color:var(--text-muted);font-size:1.3rem;padding:8px 0">No touchpoints logged yet.</p>';
    } else {
      html += '<div class="log-timeline">';
      logs.forEach(function (l) {
        html += '<div class="log-entry">';
        html += '  <span class="log-entry__dot ' + l.type + '"></span>';
        html += '  <div>';
        html += '    <div>' + DTD.TOUCH_LABELS[l.type] + ' &nbsp;·&nbsp; Q' + l.quarter + ' ' + l.year + '</div>';
        html += '    <div class="log-entry__meta">' + DTD.formatDate(l.completedAt) + '</div>';
        if (l.note) html += '    <div class="log-entry__note">' + DTD.escHtml(l.note) + '</div>';
        html += '  </div>';
        html += '</div>';
      });
      html += '</div>';
    }

    // Edit / Delete
    html += '<div style="display:flex;gap:10px;margin-top:20px">';
    html += '  <button class="btn-secondary btn-full" style="flex:1" data-action="open-edit-contact"' +
            '    data-contact-id="' + DTD.escHtml(contactId) + '">' + DTD.ICONS.edit + ' Edit</button>';
    html += '  <button class="btn-danger" data-action="delete-contact"' +
            '    data-contact-id="' + DTD.escHtml(contactId) + '">' + DTD.ICONS.trash + ' Delete</button>';
    html += '</div>';

    html += '</div>';
    document.getElementById('app').innerHTML = html;

    document.getElementById('header-subtitle').textContent = contact.firstName + ' ' + contact.lastName;
    document.getElementById('header-action-btn').innerHTML  = DTD.ICONS.back;
    document.getElementById('header-action-btn').dataset.action = 'nav-back';
    document.getElementById('header-action-btn').dataset.tab    = '';
  };

  // ── Add / Edit Form ───────────────────────────

  DTD.renderForm = function (contactId) {
    var isEdit  = !!contactId;
    var contact = isEdit ? (DTD.getContactById(contactId) || {}) : {};

    function val(field) { return DTD.escHtml(contact[field] || ''); }

    var html = '<div class="view-form">';
    html += '<div class="form-section-title">' + (isEdit ? 'Edit Contact' : 'New Contact') + '</div>';

    html += '<form id="contact-form">';

    // Name row
    html += '<div class="form-row">';
    html += '  <div class="form-group">';
    html += '    <label class="form-label">First Name *</label>';
    html += '    <input class="form-input" name="firstName" type="text" value="' + val('firstName') + '" required autocomplete="given-name" />';
    html += '  </div>';
    html += '  <div class="form-group">';
    html += '    <label class="form-label">Last Name *</label>';
    html += '    <input class="form-input" name="lastName" type="text" value="' + val('lastName') + '" required autocomplete="family-name" />';
    html += '  </div>';
    html += '</div>';

    // Contact info
    html += '<div class="form-section-title">Contact Info</div>';
    html += '<div class="form-group"><label class="form-label">Phone</label>';
    html += '  <input class="form-input" name="phone" type="tel" value="' + val('phone') + '" autocomplete="tel" /></div>';
    html += '<div class="form-group"><label class="form-label">Email</label>';
    html += '  <input class="form-input" name="email" type="email" value="' + val('email') + '" autocomplete="email" /></div>';
    html += '<div class="form-group"><label class="form-label">Address</label>';
    html += '  <textarea class="form-textarea" name="address">' + val('address') + '</textarea></div>';

    // Social
    html += '<div class="form-section-title">Social Handles</div>';
    html += '<div class="form-group"><label class="form-label">Instagram</label>';
    html += '  <input class="form-input" name="instagram" type="text" value="' + val('instagram') + '" placeholder="@handle" /></div>';
    html += '<div class="form-group"><label class="form-label">LinkedIn</label>';
    html += '  <input class="form-input" name="linkedin" type="text" value="' + val('linkedin') + '" placeholder="linkedin.com/in/…" /></div>';
    html += '<div class="form-group"><label class="form-label">Facebook</label>';
    html += '  <input class="form-input" name="facebook" type="text" value="' + val('facebook') + '" placeholder="facebook.com/…" /></div>';
    html += '<div class="form-group"><label class="form-label">Twitter / X</label>';
    html += '  <input class="form-input" name="twitter" type="text" value="' + val('twitter') + '" placeholder="@handle" /></div>';

    // Notes
    html += '<div class="form-section-title">Notes</div>';
    html += '<div class="form-group">';
    html += '  <textarea class="form-textarea" name="notes" placeholder="How you met, context, etc.">' + val('notes') + '</textarea>';
    html += '</div>';

    // Actions
    html += '<button type="submit" class="btn-primary">' + (isEdit ? 'Save Changes' : 'Add Contact') + '</button>';

    if (isEdit) {
      html += '<input type="hidden" name="_id" value="' + DTD.escHtml(contactId) + '" />';
    }

    html += '</form>';

    // Cancel
    html += '<button class="btn-secondary btn-full" style="margin-top:10px" data-action="cancel-form"' +
            '  data-contact-id="' + DTD.escHtml(contactId || '') + '">Cancel</button>';

    html += '</div>';
    document.getElementById('app').innerHTML = html;

    // Wire submit
    document.getElementById('contact-form').addEventListener('submit', function (e) {
      e.preventDefault();
      var data  = DTD.readContactForm(this);
      var idVal = (this.querySelector('[name="_id"]') || {}).value;
      if (idVal) {
        DTD.updateContact(idVal, data);
        DTD.showToast('Contact updated', 'success');
        DTD.renderDetail(idVal);
      } else {
        var saved = DTD.saveContact(data);
        DTD.showToast('Contact added', 'success');
        DTD.renderDetail(saved.id);
      }
    });

    document.getElementById('header-subtitle').textContent = isEdit ? 'Edit Contact' : 'New Contact';
    document.getElementById('header-action-btn').innerHTML  = DTD.ICONS.back;
    document.getElementById('header-action-btn').dataset.action = 'cancel-form';
    document.getElementById('header-action-btn').dataset.tab    = '';
    document.getElementById('header-action-btn').dataset.contactId = contactId || '';
  };

})(window.DTD = window.DTD || {});
