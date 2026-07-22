/* ================================================
   DTD — Contact CRUD
   ================================================
   Depends on: dtd-constants.js, dtd-storage.js, dtd-week.js
   ================================================ */
(function (DTD) {
  'use strict';

  // ── Read ──────────────────────────────────────

  // Returns all contacts sorted by lastName, then firstName
  DTD.getContacts = function () {
    var contacts = DTD.loadData(DTD.KEYS.contacts) || [];
    return contacts.sort(function (a, b) {
      var la = (a.lastName  || '').toLowerCase();
      var lb = (b.lastName  || '').toLowerCase();
      if (la !== lb) return la < lb ? -1 : 1;
      var fa = (a.firstName || '').toLowerCase();
      var fb = (b.firstName || '').toLowerCase();
      return fa < fb ? -1 : fa > fb ? 1 : 0;
    });
  };

  DTD.getContactById = function (id) {
    var contacts = DTD.loadData(DTD.KEYS.contacts) || [];
    return contacts.find(function (c) { return c.id === id; }) || null;
  };

  // All contacts whose last-name initial maps to the given group code
  DTD.getContactsByGroup = function (groupCode) {
    return DTD.getContacts().filter(function (c) {
      return DTD.getLetterGroup(c.lastName) === groupCode;
    });
  };

  // Case-insensitive search across name, phone, email
  DTD.searchContacts = function (query) {
    if (!query) return DTD.getContacts();
    var q = query.toLowerCase();
    return DTD.getContacts().filter(function (c) {
      return (c.firstName + ' ' + c.lastName).toLowerCase().includes(q) ||
             (c.phone  || '').toLowerCase().includes(q) ||
             (c.email  || '').toLowerCase().includes(q) ||
             (c.notes  || '').toLowerCase().includes(q);
    });
  };

  // ── Write ─────────────────────────────────────

  // Create a new contact. Returns the saved contact with an id.
  DTD.saveContact = function (data) {
    var contacts = DTD.loadData(DTD.KEYS.contacts) || [];
    var contact  = Object.assign({
      id:        DTD.generateId(),
      createdAt: new Date().toISOString(),
      tags:      []
    }, data);
    contacts.push(contact);
    DTD.saveData(DTD.KEYS.contacts, contacts);
    return contact;
  };

  // Update an existing contact by id. Returns the updated contact or null.
  DTD.updateContact = function (id, data) {
    var contacts = DTD.loadData(DTD.KEYS.contacts) || [];
    var idx = contacts.findIndex(function (c) { return c.id === id; });
    if (idx === -1) return null;
    contacts[idx] = Object.assign({}, contacts[idx], data, { id: id });
    DTD.saveData(DTD.KEYS.contacts, contacts);
    return contacts[idx];
  };

  // Delete a contact and all their touch logs
  DTD.deleteContact = function (id) {
    var contacts = DTD.loadData(DTD.KEYS.contacts) || [];
    DTD.saveData(
      DTD.KEYS.contacts,
      contacts.filter(function (c) { return c.id !== id; })
    );

    var logs = DTD.loadData(DTD.KEYS.touchlogs) || [];
    DTD.saveData(
      DTD.KEYS.touchlogs,
      logs.filter(function (l) { return l.contactId !== id; })
    );
  };

  // ── Helpers ───────────────────────────────────

  // Build a form-data object from a <form> element's named inputs
  DTD.readContactForm = function (formEl) {
    var data = {};
    var fields = [
      'firstName','lastName','phone','email',
      'instagram','linkedin','facebook','twitter',
      'address','notes'
    ];
    fields.forEach(function (f) {
      var el = formEl.querySelector('[name="' + f + '"]');
      data[f] = el ? el.value.trim() : '';
    });
    return data;
  };

})(window.DTD = window.DTD || {});
