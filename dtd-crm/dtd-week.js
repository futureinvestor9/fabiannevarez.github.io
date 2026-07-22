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

    var startDate = new Date(startStr + 'T00:00:00');
    var today     = new Date();
    today.setHours(0, 0, 0, 0);

    // Number of full days elapsed since the original quarter start
    var msPerDay  = 86400000;
    var daysElapsed = Math.max(0, Math.floor((today - startDate) / msPerDay));

    // Roll forward in 13-week quarter blocks instead of clamping at week 13,
    // so the cadence keeps advancing (and progress resets) each new quarter.
    var weeksElapsed    = Math.floor(daysElapsed / 7);   // 0-based
    var quartersElapsed = Math.floor(weeksElapsed / 13);
    var weekNum         = (weeksElapsed % 13) + 1;        // 1..13

    // Start date of the quarter we're currently in
    var quarterStart = new Date(startDate.getTime() + quartersElapsed * 13 * 7 * msPerDay);

    // Derive quarter number from that month (1-3=Q1, 4-6=Q2, 7-9=Q3, 10-12=Q4)
    var startMonth = quarterStart.getMonth() + 1; // 1-indexed
    var quarter    = Math.ceil(startMonth / 3);
    var year       = quarterStart.getFullYear();

    // Week window dates
    var weekOffset    = (weekNum - 1) * 7;
    var weekStartDate = new Date(quarterStart.getTime() + weekOffset * msPerDay);
    var weekEndDate   = new Date(weekStartDate.getTime() + 6 * msPerDay);

    return {
      quarter:          quarter,
      year:             year,
      weekNum:          weekNum,
      weekRotation:     DTD.WEEK_ROTATION[weekNum - 1],
      quarterStartDate: quarterStart.toISOString().slice(0, 10),
      weekStartDate:    weekStartDate.toISOString().slice(0, 10),
      weekEndDate:      weekEndDate.toISOString().slice(0, 10)
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
