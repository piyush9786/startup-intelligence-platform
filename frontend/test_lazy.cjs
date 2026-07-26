const fs = require('fs');

let content = fs.readFileSync('src/App.test.jsx', 'utf8');
content = content.replace(/await screen\.findByRole\("heading", {\s*name:\s*"Explore schemes",\s*}\)/g, 'await screen.findByRole("heading", { name: "Explore schemes" }, { timeout: 5000 })');
fs.writeFileSync('src/App.test.jsx', content);
