/* ================================================
   DTD — Settings · CSV Import · Plans Views
   ================================================
   Depends on: all previous modules + dtd-views-core.js
   ================================================ */
(function (DTD) {
  'use strict';

  // ── Settings ──────────────────────────────────

  DTD.renderSettings = function () {
    var settings  = DTD.getSettings();
    var templates = settings.defaultTemplates;

    var html = '<div class="view-settings">';

    // ── General
    html += '<div class="section-header">General</div>';
    html += '<div class="settings-card">';

    html += '<div class="settings-row">';
    html += '  <div><div class="settings-row__label">Your Name</div></div>';
    html += '  <input class="form-input" id="s-username" type="text" value="' +
            DTD.escHtml(settings.userName) + '" style="width:140px;min-height:36px;font-size:1.4rem" />';
    html += '</div>';

    html += '<div class="settings-row">';
    html += '  <div>';
    html += '    <div class="settings-row__label">Quarter Start Date</div>';
    html += '    <div class="settings-row__sub">Week 1 begins on this date</div>';
    html += '  </div>';
    html += '  <input class="form-input" id="s-qstart" type="date" value="' +
            DTD.escHtml(settings.quarterStartDate) + '" style="width:155px;min-height:36px;font-size:1.4rem" />';
    html += '</div>';
    html += '</div>'; // settings-card

    // ── Templates
    html += '<div class="section-header">Message Templates</div>';
    html += '<div class="settings-card">';
    html += '<div class="template-editor">';

    var templateMeta = [
      { key: 'call',   label: 'Phone Call Script',    hint: 'Use [firstName] for personalization' },
      { key: 'text',   label: 'Text Message',          hint: '' },
      { key: 'email',  label: 'Email (first line = Subject:)', hint: 'Subject: Your subject here' },
      { key: 'social', label: 'Social DM / Comment',  hint: '' },
      { key: 'note',   label: 'Handwritten Note Body', hint: '' }
    ];

    templateMeta.forEach(function (t) {
      html += '<label class="form-label" style="color:var(--' + (t.key === 'email' ? 'social' : t.key) + '-color);margin-top:14px">' +
              DTD.TOUCH_LABELS[t.key] || t.label;
      html += t.label + '</label>';
      if (t.hint) html += '<div style="font-size:1.1rem;color:var(--text-muted);margin-bottom:4px">' + t.hint + '</div>';
      html += '<textarea class="form-textarea" id="tpl-' + t.key + '">' +
              DTD.escHtml(templates[t.key] || '') + '</textarea>';
      html += '<button class="modal-copy-btn" style="margin-bottom:4px" data-action="reset-template" data-type="' + t.key + '">Reset to default</button>';
    });

    html += '</div></div>'; // template-editor + settings-card

    // ── Data
    html += '<div class="section-header">Data</div>';
    html += '<div class="settings-card">';
    html += '<div class="settings-row" style="flex-direction:column;align-items:flex-start;gap:10px">';
    html += '  <button class="btn-secondary btn-full" data-action="export-contacts">' + DTD.ICONS.copy + ' Export Contacts CSV</button>';
    html += '  <button class="btn-secondary btn-full" data-action="export-logs">' + DTD.ICONS.copy + ' Export Touch Log CSV</button>';
    html += '  <button class="btn-secondary btn-full" data-action="go-import">' + DTD.ICONS.plus + ' Import Contacts CSV</button>';
    html += '</div>';
    html += '</div>';

    // Save
    html += '<button class="btn-primary" id="save-settings-btn" data-action="save-settings" style="margin-top:8px">' +
            DTD.ICONS.check + ' Save Settings</button>';

    html += '</div>';
    document.getElementById('app').innerHTML = html;

    document.getElementById('header-subtitle').textContent = 'Settings';
    document.getElementById('header-action-btn').innerHTML  = DTD.ICONS.back;
    document.getElementById('header-action-btn').dataset.action = 'open-tab';
    document.getElementById('header-action-btn').dataset.tab    = 'dashboard';
  };

  // Called from event delegation
  DTD.handleSaveSettings = function () {
    var settings = DTD.getSettings();

    var nameEl   = document.getElementById('s-username');
    var qstartEl = document.getElementById('s-qstart');

    if (nameEl)   settings.userName          = nameEl.value.trim();
    if (qstartEl && qstartEl.value) settings.quarterStartDate = qstartEl.value;

    var tplKeys = ['call', 'text', 'email', 'social', 'note'];
    tplKeys.forEach(function (k) {
      var el = document.getElementById('tpl-' + k);
      if (el) settings.defaultTemplates[k] = el.value;
    });

    DTD.saveSettings(settings);
    DTD.showToast('Settings saved', 'success');
  };

  DTD.handleResetTemplate = function (type) {
    var el = document.getElementById('tpl-' + type);
    if (el) el.value = DTD.DEFAULT_SETTINGS.defaultTemplates[type] || '';
    DTD.showToast(DTD.TOUCH_LABELS[type] + ' template reset', '');
  };

  // ── CSV Import ────────────────────────────────

  DTD.renderImport = function () {
    var csvData = DTD.state.csvData;

    var html = '<div class="view-import">';
    html += '<div class="section-header">Import Contacts</div>';

    if (!csvData) {
      // Step 1: file picker
      html += '<div class="import-drop-zone" id="drop-zone">';
      html += '  <span class="import-drop-zone__icon">&#128196;</span>';
      html += '  <div>Tap to choose a CSV file</div>';
      html += '  <div style="font-size:1.2rem;margin-top:6px;color:var(--text-muted)">First row must be headers</div>';
      html += '</div>';
      html += '<input id="csv-file-input" type="file" accept=".csv,text/csv" style="display:none" />';
      html += '<button class="btn-primary" id="pick-csv-btn">Choose CSV File</button>';
    } else {
      // Step 2: column mapping
      var headers = csvData.headers;
      var rows    = csvData.rows;

      html += '<div style="font-size:1.3rem;margin-bottom:12px;color:var(--white-1)">' +
              rows.length + ' rows found. Map columns to contact fields:</div>';

      html += '<table class="column-map-table"><thead><tr>';
      html += '  <th>CSV Column</th><th>Maps To</th>';
      html += '</tr></thead><tbody>';

      headers.forEach(function (h, i) {
        var optionHtml = DTD.CSV_CONTACT_FIELDS.map(function (f) {
          // Auto-guess based on header name
          var isMatch = f.value !== '__skip__' &&
            (h.toLowerCase().replace(/\s+/g, '').includes(f.value.toLowerCase()) ||
             f.label.toLowerCase().replace(/\s+/g, '').includes(h.toLowerCase().replace(/\s+/g, '')));
          return '<option value="' + f.value + '"' + (isMatch ? ' selected' : '') + '>' + DTD.escHtml(f.label) + '</option>';
        }).join('');

        html += '<tr>';
        html += '  <td>' + DTD.escHtml(h) + '</td>';
        html += '  <td><select class="form-select" style="min-height:36px" data-col="' + i + '" id="map-col-' + i + '">' + optionHtml + '</select></td>';
        html += '</tr>';
      });
      html += '</tbody></table>';

      // Preview first 3 rows
      html += '<div style="font-size:1.2rem;color:var(--text-muted);margin-bottom:6px">Preview (first 3 rows)</div>';
      html += '<div class="import-preview">';
      rows.slice(0, 3).forEach(function (row) {
        html += '<div style="padding:4px 0;border-bottom:1px solid var(--border)">' +
                row.map(function (f) { return DTD.escHtml(f); }).join(' | ') + '</div>';
      });
      html += '</div>';

      html += '<button class="btn-primary" data-action="confirm-import">Import ' + rows.length + ' Contacts</button>';
      html += '<button class="btn-secondary btn-full" style="margin-top:8px" data-action="reset-import">Choose different file</button>';
    }

    html += '</div>';
    document.getElementById('app').innerHTML = html;

    // Wire file picker button
    var pickBtn   = document.getElementById('pick-csv-btn');
    var fileInput = document.getElementById('csv-file-input');
    var dropZone  = document.getElementById('drop-zone');

    if (pickBtn && fileInput) {
      pickBtn.addEventListener('click', function () { fileInput.click(); });
      if (dropZone) {
        dropZone.addEventListener('click', function () { fileInput.click(); });
      }
      fileInput.addEventListener('change', function () {
        var file = this.files[0];
        if (!file) return;
        var reader = new FileReader();
        reader.onload = function (e) {
          DTD.state.csvData = DTD.parseCSV(e.target.result);
          DTD.renderImport();
        };
        reader.readAsText(file);
      });
    }

    document.getElementById('header-subtitle').textContent = 'Import CSV';
    document.getElementById('header-action-btn').innerHTML  = DTD.ICONS.back;
    document.getElementById('header-action-btn').dataset.action = 'open-tab';
    document.getElementById('header-action-btn').dataset.tab    = 'settings';
  };

  DTD.handleConfirmImport = function () {
    var csvData = DTD.state.csvData;
    if (!csvData) return;

    var mapping = {};
    csvData.headers.forEach(function (h, i) {
      var el = document.getElementById('map-col-' + i);
      if (el) mapping[i] = el.value;
    });

    var contacts = DTD.mapCSVToContacts(csvData.rows, mapping);
    var imported = 0;
    contacts.forEach(function (c) {
      if (c.firstName || c.lastName) {
        DTD.saveContact(c);
        imported++;
      }
    });

    DTD.state.csvData   = null;
    DTD.state.csvMapping = {};
    DTD.showToast(imported + ' contacts imported', 'success');
    DTD.renderContacts();
  };

  // ── Plans View ────────────────────────────────

  DTD.renderPlans = function () {
    var info    = DTD.getCurrentQuarterInfo();
    var currWeek = info.weekNum;

    var html = '<div class="view-plans">';

    // Intro card
    html += '<div class="plans-intro">';
    html += '  <h3>DTD 4\u00D74 System</h3>';
    html += '  <p>Every quarter, every contact gets 4 touchpoints: a <strong style="color:var(--call-color)">Phone Call</strong>, ' +
            '  a <strong style="color:var(--text-color)">Text</strong>, an <strong style="color:var(--social-color)">Email/Social</strong>, ' +
            '  and a <strong style="color:var(--card-color)">Handwritten Note Card</strong>.</p>';
    html += '  <p>Contacts are divided into 13 letter groups. Each week, the rotation table below tells you which group ' +
            '  gets which touchpoint. Over 4 quarters = <strong>16 touchpoints per person per year</strong>.</p>';
    html += '  <p style="color:var(--pink);font-weight:600">You are in Week ' + currWeek + ' of Q' + info.quarter + ' ' + info.year + '</p>';
    html += '</div>';

    // Rotation table
    html += '<div class="section-header">13-Week Rotation</div>';
    html += '<table class="rotation-table"><thead><tr>';
    html += '  <th>Wk</th>';
    html += '  <th class="rt-call">Call</th>';
    html += '  <th class="rt-text">Text</th>';
    html += '  <th class="rt-card">Card</th>';
    html += '  <th class="rt-social">Social</th>';
    html += '</tr></thead><tbody>';

    DTD.WEEK_ROTATION.forEach(function (row, i) {
      var wn   = i + 1;
      var curr = (wn === currWeek) ? ' current-row' : '';
      html += '<tr class="' + curr + '">';
      html += '  <td><strong>' + wn + (curr ? ' \u25C4' : '') + '</strong></td>';
      html += '  <td class="rt-call">'   + row.call   + '</td>';
      html += '  <td class="rt-text">'   + row.text   + '</td>';
      html += '  <td class="rt-card">'   + row.card   + '</td>';
      html += '  <td class="rt-social">' + row.social + '</td>';
      html += '</tr>';
    });

    html += '</tbody></table>';

    // Group legend
    html += '<div class="section-header">Letter Group Legend</div>';
    html += '<div class="settings-card" style="padding:12px 14px">';
    html += '<div style="display:flex;flex-wrap:wrap;gap:8px 16px">';
    DTD.ALL_GROUPS.forEach(function (g) {
      // Find which letters map to this group
      var letters = Object.keys(DTD.LETTER_TO_GROUP).filter(function (l) {
        return DTD.LETTER_TO_GROUP[l] === g;
      }).join(', ');
      html += '<div style="font-size:1.3rem">' +
              '<strong style="color:var(--pink)">' + g + '</strong>' +
              ' <span style="color:var(--text-muted)">= ' + letters + '</span>' +
              '</div>';
    });
    html += '</div></div>';

    html += '</div>';
    document.getElementById('app').innerHTML = html;

    document.getElementById('header-subtitle').textContent = 'Plans & Schedule';
    document.getElementById('header-action-btn').innerHTML  = '';
    document.getElementById('header-action-btn').dataset.action = '';
    document.getElementById('header-action-btn').dataset.tab    = '';
  };

})(window.DTD = window.DTD || {});
