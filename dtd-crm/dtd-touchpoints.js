/* ================================================
   DTD — Touchpoint Engine + Template Engine + Settings
   ================================================
   Depends on: dtd-constants.js, dtd-storage.js, dtd-week.js
   ================================================ */
(function (DTD) {
  'use strict';

  // ── Settings ──────────────────────────────────

  DTD.getSettings = function () {
    var saved = DTD.loadData(DTD.KEYS.settings);
    // Deep-merge saved over defaults so new template keys are always present
    var settings = Object.assign({}, DTD.DEFAULT_SETTINGS, saved);
    settings.defaultTemplates = Object.assign(
      {},
      DTD.DEFAULT_SETTINGS.defaultTemplates,
      (saved && saved.defaultTemplates) ? saved.defaultTemplates : {}
    );
    return settings;
  };

  DTD.saveSettings = function (settings) {
    DTD.saveData(DTD.KEYS.settings, settings);
  };

  // ── Template Engine ───────────────────────────

  // Replace [firstName], [lastName], [fullName], [date] tokens
  DTD.fillTemplate = function (template, contact) {
    if (!template) return '';
    var today = new Date().toLocaleDateString('en-US', {
      month: 'long', day: 'numeric', year: 'numeric'
    });
    return template
      .replace(/\[firstName\]/g,  contact.firstName  || '')
      .replace(/\[lastName\]/g,   contact.lastName   || '')
      .replace(/\[fullName\]/g,   ((contact.firstName || '') + ' ' + (contact.lastName || '')).trim())
      .replace(/\[date\]/g,       today);
  };

  // ── Touchpoint Log ────────────────────────────

  // Append a new touch log entry
  DTD.logTouchpoint = function (contactId, type, noteText) {
    var info  = DTD.getCurrentQuarterInfo();
    var group = DTD.getLetterGroup(
      (DTD.getContactById(contactId) || {}).lastName
    );

    var entry = {
      id:          DTD.generateId(),
      contactId:   contactId,
      type:        type,
      quarter:     info.quarter,
      year:        info.year,
      weekGroup:   group,
      completedAt: new Date().toISOString(),
      note:        noteText || ''
    };

    var logs = DTD.loadData(DTD.KEYS.touchlogs) || [];
    logs.push(entry);
    DTD.saveData(DTD.KEYS.touchlogs, logs);
    return entry;
  };

  // Return { call, text, card, social } booleans for a contact this quarter
  DTD.getTouchStatus = function (contactId, quarter, year) {
    var logs   = DTD.loadData(DTD.KEYS.touchlogs) || [];
    var status = { call: false, text: false, card: false, social: false };
    logs.forEach(function (l) {
      if (l.contactId === contactId && l.quarter === quarter && l.year === year) {
        if (status.hasOwnProperty(l.type)) {
          status[l.type] = true;
        }
      }
    });
    return status;
  };

  // Get all touch logs for a contact, newest first
  DTD.getContactLogs = function (contactId) {
    var logs = DTD.loadData(DTD.KEYS.touchlogs) || [];
    return logs
      .filter(function (l) { return l.contactId === contactId; })
      .sort(function (a, b) { return b.completedAt.localeCompare(a.completedAt); });
  };

  // ── Weekly Progress ───────────────────────────

  // Given an array of group codes (the 4 active groups for this week),
  // return completion stats for the current quarter.
  //
  // Returns:
  //   { total, fullyDone, byType: { call, text, card, social } }
  //   where byType values are counts of contacts that have that type done.
  DTD.getWeekProgress = function (groups) {
    var info = DTD.getCurrentQuarterInfo();
    var rot  = info.weekRotation;

    // Which single touch type each active group owes THIS week
    var groupType = {};
    groupType[rot.call]   = 'call';
    groupType[rot.text]   = 'text';
    groupType[rot.card]   = 'card';
    groupType[rot.social] = 'social';

    var contacts = [];
    groups.forEach(function (g) {
      DTD.getContactsByGroup(g).forEach(function (c) { contacts.push(c); });
    });

    var byType    = { call: 0, text: 0, card: 0, social: 0 };
    var weekDone  = 0;   // completed THIS week's one assigned touch
    var fullyDone = 0;   // completed all 4 quarterly touches

    contacts.forEach(function (c) {
      var status  = DTD.getTouchStatus(c.id, info.quarter, info.year);
      var allDone = true;
      DTD.TOUCH_TYPES.forEach(function (t) {
        if (status[t]) { byType[t]++; } else { allDone = false; }
      });
      if (allDone) fullyDone++;

      var assigned = groupType[DTD.getLetterGroup(c.lastName)];
      if (assigned && status[assigned]) { weekDone++; }
    });

    return {
      total:      contacts.length,
      weekDone:   weekDone,
      fullyDone:  fullyDone,
      byType:     byType
    };
  };

})(window.DTD = window.DTD || {});
