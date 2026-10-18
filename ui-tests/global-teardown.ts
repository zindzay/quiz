import fs from 'node:fs';

export default function globalTeardown() {
  const file = process.env.QUIZ_UI_DATA_FILE;
  if (file) {
    fs.rmSync(file, { force: true });
  }
}
