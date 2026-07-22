/* ================================================
   DTD — CSV Import / Export
   ================================================
   Depends on: dtd-constants.js, dtd-storage.js
   ================================================ */
(function (DTD) {
  'use strict';

  // ── Parser ────────────────────────────────────

  // Robust CSV parser that handles quoted fields and embedded commas/newlines.
  // Returns { headers: string[], rows: string[][] }
  DTD.parseCSV = function (text) {
    var lines  = [];
    var row    = [];
    var field  = '';
    var inQuote = false;
    var i = 0;

    while (i < text.length) {
      var ch = text[i];

      if (inQuote) {
        if (ch === '"') {
          if (text[i + 1] === '"') {
            field += '"';   // escaped double-quote
            i += 2;
            continue;
          }
          inQuote = false;
        } else {
          field += ch;
        }
      } else {
        if (ch === '"') {
          inQuote = true;
        } else if (ch === ',') {
          row.push(field.trim());
          field = '';
        } else if (ch === '\n') {
          row.push(field.trim());
          field = '';
          if (row.some(function (f) { return f !== ''; })) {
            lines.push(row);
          }
          row = [];
        } else if (ch !== '\r') {
          field += ch;
        }
      }
      i++;
    }
    // Last field / row
    row.push(field.trim());
    if (row.some(function (f) { return f !== ''; })) {
      lines.push(row);
    }

    if (lines.length === 0) return { headers: [], rows: [] };
    return { headers: lines[0], rows: lines.slice(1) };
  };

  // Map a parsed CSV into contact objects using a column-mapping object.
  // mapping = { csvColumnIndex: contactFieldName }
  // e.g. { 0: 'firstName', 1: 'lastName', 2: 'phone' }
  DTD.mapCSVToContacts = function (rows, mapping) {
    return rows
      .filter(function (row) { return row.some(function (f) { return f; }); })
      .map(function (row) {
        var contact = {};
        Object.keys(mapping).forEach(function (colIdx) {
          var field = mapping[colIdx];
          if (field && field !== '__skip__') {
            contact[field] = row[parseInt(colIdx, 10)] || '';
          }
        });
        return contact;
      });
  };

  // ── Export ────────────────────────────────────

  var CONTACT_FIELDS = [
    'id',
    'firstName','lastName','phone','email',
    'instagram','linkedin','facebook','twitter',
    'address','notes','createdAt'
  ];

  var LOG_FIELDS = [
    'id','contactId','type','quarter','year','weekGroup','completedAt','note'
  ];

  function toCsvRow(fields, obj) {
    return fields.map(function (f) {
      var val = obj[f] == null ? '' : String(obj[f]);
      // Quote fields that contain commas, quotes, or newlines
      if (/[,"\n]/.test(val)) {
        return '"' + val.replace(/"/g, '""') + '"';
      }
      return val;
    }).join(',');
  }

  DTD.exportContactsToCSV = function () {
    var contacts = DTD.getContacts();
    var lines    = [CONTACT_FIELDS.join(',')];
    contacts.forEach(function (c) { lines.push(toCsvRow(CONTACT_FIELDS, c)); });
    DTD.triggerDownload('dtd-contacts-' + DTD.todayISO() + '.csv', lines.join('\n'));
  };

  DTD.exportTouchlogsToCSV = function () {
    var logs  = DTD.loadData(DTD.KEYS.touchlogs) || [];
    var lines = [LOG_FIELDS.join(',')];
    logs.forEach(function (l) { lines.push(toCsvRow(LOG_FIELDS, l)); });
    DTD.triggerDownload('dtd-touchlogs-' + DTD.todayISO() + '.csv', lines.join('\n'));
  };

  DTD.triggerDownload = function (filename, content) {
    var blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
    var url  = URL.createObjectURL(blob);
    var a    = document.createElement('a');
    a.href     = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  };

  // Known contact field names for the CSV mapping UI
  DTD.CSV_CONTACT_FIELDS = [
    { value: '__skip__',   label: '— Skip —' },
    { value: 'firstName',  label: 'First Name' },
    { value: 'lastName',   label: 'Last Name' },
    { value: 'phone',      label: 'Phone' },
    { value: 'email',      label: 'Email' },
    { value: 'instagram',  label: 'Instagram' },
    { value: 'linkedin',   label: 'LinkedIn' },
    { value: 'facebook',   label: 'Facebook' },
    { value: 'twitter',    label: 'Twitter / X' },
    { value: 'address',    label: 'Address' },
    { value: 'notes',      label: 'Notes' }
  ];

})(window.DTD = window.DTD || {});
