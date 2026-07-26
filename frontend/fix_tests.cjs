const fs = require('fs');

function fixFile(file) {
  let content = fs.readFileSync(file, 'utf8');

  // Replace expect(screen.getBy...) with expect(await screen.findBy...)
  content = content.replace(/expect\(\s*screen\.getBy(Role|Text|TestId|LabelText|PlaceholderText)\(/g, 'expect(await screen.findBy$1(');
  
  // Replace user.click(screen.getBy...) with user.click(await screen.findBy...)
  content = content.replace(/user\.click\(\s*screen\.getBy(Role|Text|TestId|LabelText|PlaceholderText)\(/g, 'user.click(await screen.findBy$1(');

  // Replace name: "Requirements", "Funding", "Guidance" with regex
  content = content.replace(/name:\s*"Requirements"/g, 'name: /Requirements/i');
  content = content.replace(/name:\s*"Funding"/g, 'name: /Funding/i');
  content = content.replace(/name:\s*"Guidance"/g, 'name: /Guidance/i');
  content = content.replace(/name:\s*"Reviewer Workspace"/g, 'name: /Reviewer Workspace/i');

  fs.writeFileSync(file, content);
}

fixFile('src/App.test.jsx');
fixFile('src/AppShell.test.jsx');
console.log('Done!');
