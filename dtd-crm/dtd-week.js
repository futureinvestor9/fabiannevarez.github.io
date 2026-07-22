/* ================================================
   DTD — Week & Quarter Calculator
   ================================================
   Depends on: dtd-constants.js, dtd-storage.js
   ================================================ */
(function (DTD) {
  'use strict';

  // Return the 2-letter group code for a given last name (e.g. "Smith" → "SU")
  DTD.getLetterGroup = function (lastName) {
    if (!lastName) return 'YZ';
    var initial = lastName.trim().charAt(0).toUpperCase();
    return DTD.LETTER_TO_GROUP[initial] || 'YZ';
  };

  // Core quarter calculator.
  // Returns:
  //   { quarter, year, weekNum, weekRotation, quarterStartDate,
  //     weekStartDate, weekEndDate }
  DTD.getCurrentQuarterInfo = function () {
    var settings = DTD.getSettings();
    var startStr = settings.quarterStartDate || DTD.DEFAULT_SETTINGS.quarterStartDate;

    // Count elapsed days in pure calendar time via UTC components. Subtracting
    // local-midnight timestamps would undercount across a DST spring-forward
    // (that day is only 23h), shifting the week/quarter boundary by a day.
    var msPerDay  = 86400000;
    var sp        = startStr.split('-');
    var startUTC  = Date.UTC(+sp[0], (+sp[1]) - 1, +sp[2]);
    var now       = new Date();
    var todayUTC  = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
    var daysElapsed = Math.max(0, Math.round((todayUTC - startUTC) / msPerDay));

    // Roll forward in 13-week quarter blocks instead of clamping at week 13,
    // so the cadence keeps advancing (and progress resets) each new quarter.
    var weeksElapsed    = Math.floor(daysElapsed / 7);   // 0-based
    var quartersElapsed = Math.floor(weeksElapsed / 13);
    var weekNum         = (weeksElapsed % 13) + 1;        // 1..13

    // Start of the quarter we're currently in (UTC ms — DST-independent)
    var quarterStartMs = startUTC + quartersElapsed * 13 * 7 * msPerDay;

    // Label cycles sequentially from the user's start date (Q1→Q4, then year+1)
    // rather than from the calendar month. Two 13-week blocks can fall in the
    // same calendar quarter; since touch status is keyed by quarter+year, a
    // calendar label would collide and stop progress from resetting each cycle.
    var quarter = (quartersElapsed % 4) + 1;
    var year    = (+sp[0]) + Math.floor(quartersElapsed / 4);

    // Week window dates
    var weekOffset  = (weekNum - 1) * 7;
    var weekStartMs = quarterStartMs + weekOffset * msPerDay;
    var weekEndMs   = weekStartMs + 6 * msPerDay;

    return {
      quarter:          quarter,
      year:             year,
      weekNum:          weekNum,
      weekRotation:     DTD.WEEK_ROTATION[weekNum - 1],
      quarterStartDate: new Date(quarterStartMs).toISOString().slice(0, 10),
      weekStartDate:    new Date(weekStartMs).toISOString().slice(0, 10),
      weekEndDate:      new Date(weekEndMs).toISOString().slice(0, 10)
    };
  };

  // Return an array of the 4 group codes active this week
  // e.g. ['FG', 'AW', 'BE', 'CK'] for week 10
  DTD.getGroupsThisWeek = function () {
    var rot = DTD.getCurrentQuarterInfo().weekRotation;
    return [rot.call, rot.text, rot.card, rot.social];
  };

  // For a given contact, which touchpoint type does it get THIS week?
  // Returns 'call' | 'text' | 'card' | 'social' | null
  DTD.getTouchTypeThisWeek = function (contact) {
    var group = DTD.getLetterGroup(contact.lastName);
    var rot   = DTD.getCurrentQuarterInfo().weekRotation;
    if (rot.call   === group) return 'call';
    if (rot.text   === group) return 'text';
    if (rot.card   === group) return 'card';
    if (rot.social === group) return 'social';
    return null;
  };

  // Human-readable week banner, e.g.:
  //   "Week 10 · Call: FG · Text: AW · Card: BE · Social: CK"
  DTD.getWeekBannerText = function () {
    var info = DTD.getCurrentQuarterInfo();
    var r    = info.weekRotation;
    return 'Week ' + info.weekNum +
      '  \u00B7  Call: '   + r.call +
      '  \u00B7  Text: '   + r.text +
      '  \u00B7  Card: '   + r.card +
      '  \u00B7  Social: ' + r.social;
  };

  // Format a YYYY-MM-DD string as "Mar 24"
  DTD.formatWeekDate = function (isoDate) {
    if (!isoDate) return '';
    var d = new Date(isoDate + 'T00:00:00');
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

})(window.DTD = window.DTD || {});
