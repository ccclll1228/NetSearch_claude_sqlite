'use strict';
const cron = require('node-cron');

/**
 * Start cron jobs based on settings.cronSchedule.
 * @param {Function} reloadFn - async function to call on schedule
 * @param {string[]} schedules - array of cron expressions e.g. ["0 5 * * *"]
 */
function startScheduler(reloadFn, schedules) {
  if (!schedules || schedules.length === 0) {
    console.log('[scheduler] No cron schedules configured.');
    return;
  }
  schedules.forEach(expr => {
    if (!cron.validate(expr)) {
      console.error(`[scheduler] Invalid cron expression: ${expr}`);
      return;
    }
    cron.schedule(expr, async () => {
      console.log(`[scheduler] Cron triggered (${expr}), reloading configs...`);
      await reloadFn();
    });
    console.log(`[scheduler] Scheduled reload: ${expr}`);
  });
}

module.exports = { startScheduler };
