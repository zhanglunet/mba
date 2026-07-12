// Single source of truth for the MBA MCP server version.
// Previously '0.1.0' was hard-coded in three places (server.ts registration + the report
// footer blockquote and HTML meta div in phase-5-merge.ts), which could silently drift from
// package.json. Keep this in sync with package.json — tests/version.test.ts asserts equality.
export const SERVER_VERSION = '0.2.0';
