/* global process */

// Do this as the first thing so that any code reading it knows the right env.
// process.env.BABEL_ENV = 'test';
process.env.NODE_ENV = 'test';
process.env.PUBLIC_URL = '';
process.env.TZ = 'America/New_York';

// Marker to indicate that we've correctly ran with `yarn test`.
process.env.USING_YARN_TEST = true;

// Makes the script crash on unhandled rejections instead of silently
// ignoring them. In the future, promise rejections that are not handled will
// terminate the Node.js process with a non-zero exit code.
process.on('unhandledRejection', err => {
  throw err;
});

const jest = require('jest');

let argv = process.argv.slice(2);

// Remove watch if in CI or in coverage mode
if (process.env.CI || process.env.SENTRY_PRECOMMIT || argv.includes('--coverage')) {
  argv = argv.filter(arg => arg !== '--watch');
}

jest.run(argv);
