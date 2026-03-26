/* ================================================
   DTD — Storage Layer + Shared Utilities
   ================================================
   Depends on: dtd-constants.js
   ================================================ */
(function (DTD) {
  'use strict';

  // ── HTML escape (prevents XSS when injecting user data into innerHTML) ──
  DTD.escHtml = function (str) {
    if (str == null) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  };

  // ── UUID-like ID generator ──
  DTD.generateId = function () {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
      return crypto.randomUUID();
    }
    // Fallback for older browsers
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      var r = (Math.random() * 16) | 0;
      return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
    });
  };

  // ── localStorage wrappers ──
  DTD.loadData = function (key) {
    try {
      var raw = localStorage.getItem(key);
      if (raw === null) return null;
      return JSON.parse(raw);
    } catch (e) {
      console.warn('[DTD] loadData failed for key:', key, e);
      return null;
    }
  };

  DTD.saveData = function (key, data) {
    try {
      localStorage.setItem(key, JSON.stringify(data));
    } catch (e) {
      console.warn('[DTD] saveData failed for key:', key, e);
    }
  };

  // ── ISO date helpers ──

  // Returns today as a YYYY-MM-DD string
  DTD.todayISO = function () {
    var d = new Date();
    return d.getFullYear() + '-' +
      String(d.getMonth() + 1).padStart(2, '0') + '-' +
      String(d.getDate()).padStart(2, '0');
  };

  // Format an ISO timestamp for display: "Mar 24, 2026"
  DTD.formatDate = function (isoString) {
    if (!isoString) return '';
    var d = new Date(isoString);
    if (isNaN(d)) return isoString;
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  // Format short: "Mar 24"
  DTD.formatDateShort = function (isoString) {
    if (!isoString) return '';
    var d = new Date(isoString);
    if (isNaN(d)) return isoString;
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  // ── Contact initials (for avatar) ──
  DTD.getInitials = function (contact) {
    var f = (contact.firstName || '').charAt(0).toUpperCase();
    var l = (contact.lastName  || '').charAt(0).toUpperCase();
    return f + l || '?';
  };

  // ── App-level state (shared across all modules) ──
  DTD.state = {
    currentView:      'dashboard',
    currentContactId: null,
    searchQuery:      '',
    filterGroup:      'all',
    csvData:          null,
    csvMapping:       {},
    confirmCallback:  null
  };

})(window.DTD = window.DTD || {});
