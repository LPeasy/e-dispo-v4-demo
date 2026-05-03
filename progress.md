Current source-of-truth note, 2026-05-02: `e-dispo-prototype/` is the active app folder to continue working on. It combines the top-tab prototype UI, the `PROTOTYPE` ribbon arcade easter egg, and the active educational/statistical `e-dispo-v4.0` model.

Original prompt: Create a simplified/product-style class app called E-Dispo in ed-disposition-web-class with Landing, Model Explorer, Use the Model, Results, and Technical Docs. Restore deleted src/App.tsx as a simple app shell, remove old sidebar/stage/worksheet/report workflow, and keep ed-disposition-web-v3 unchanged.

Progress:
- Restored missing class data files from the v3 reference copy into ed-disposition-web-class/src/data so the existing test script can resolve empirical artifacts and documentation tests.
- Added simulation-count support to the class simulation worker hook.
- Replaced src/App.tsx with the requested five-page state-routed E-Dispo shell only.
- Removed the hidden arcade and old multi-stage workflow from the class app shell.
- Updated package.json and package-lock.json package names to ed-disposition-web-class.
- Verified the app with npm run test, npm run lint, npm run build, and a Playwright navigation smoke check across all five pages.
- Added hidden ambulance arcade overlay behind repeated PROTOTYPE ribbon clicks, with keyboard/touch controls and deterministic game-state hooks for testing.
- Verified arcade with npm run lint, npm run build, npm run test, manual CDP browser smoke, and screenshot inspection. The packaged web_game_playwright_client could not run because its Playwright import was unavailable from the skill script path, so browser validation used Chrome CDP directly.
- Completed end-to-end polish pass: removed the remaining "Class app shell" visible header text, verified no visible old workflow language, checked mobile/desktop overflow, confirmed hidden-game isolation, and reran npm run test, npm run lint, and npm run build.

TODO:
- No known follow-up blockers.
