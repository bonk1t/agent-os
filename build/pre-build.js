const fs = require('fs');
const path = require('path');
// Function to write environment variable content to a file
function writeEnvToFile(envVar, outputPath) {
  const content = process.env[envVar];
  if (content) {
    fs.writeFileSync(path.resolve(outputPath), content);
    console.log(`${envVar} written to ${outputPath}`);
  } else {
    console.log(`${envVar} is not set`);
  }
}
writeEnvToFile('FIREBASE_CONFIG', './frontend/src/firebase/firebaseConfig.json');
writeEnvToFile('CHATBOT_WIDGET', './frontend/static/chatbot-widget.js');
