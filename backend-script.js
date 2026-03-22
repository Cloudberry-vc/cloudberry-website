// =====================================================
// CLOUDBERRY VC BLOG BACKEND — Google Apps Script
// =====================================================
//
// This runs for free on Google's servers. It uses a
// Google Sheet as your database.
//
// SETUP (one time, ~5 minutes):
//
// 1. Go to https://script.google.com and create a new project
// 2. Delete the default code and paste this entire file
// 3. Click "Run" on the setup() function first (it creates the Sheet)
// 4. Authorize when prompted (it needs access to your Drive)
// 5. Click "Deploy" > "New deployment"
// 6. Choose type: "Web app"
// 7. Set "Execute as": Me
// 8. Set "Who has access": Anyone
// 9. Click "Deploy" and copy the URL
// 10. Paste that URL into admin.html and post.html where it says BACKEND_URL
// 11. Also paste it into the <script> at the bottom of index.html
//
// That's it! Your blog is now live.
// =====================================================

const SHEET_NAME = 'BlogPosts';

// Creates the spreadsheet on first run
function setup() {
  const ss = SpreadsheetApp.getActiveSpreadsheet() || SpreadsheetApp.create('Cloudberry Blog Posts');
  let sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(SHEET_NAME);
    sheet.appendRow(['id', 'title', 'summary', 'content', 'coverImage', 'date', 'timestamp']);
    sheet.setFrozenRows(1);
  }
  Logger.log('Setup complete! Sheet URL: ' + ss.getUrl());
}

// Handle GET requests (list posts, get single post, ping)
function doGet(e) {
  const action = e.parameter.action || 'list';

  if (action === 'ping') {
    return jsonResponse({ status: 'ok' });
  }

  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  const data = sheet.getDataRange().getValues();
  const headers = data[0];

  const posts = data.slice(1).map(row => {
    const obj = {};
    headers.forEach((h, i) => obj[h] = row[i]);
    return obj;
  }).sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0));

  if (action === 'get') {
    const id = e.parameter.id;
    const post = posts.find(p => p.id == id);
    return jsonResponse(post || null);
  }

  // Return list (without full content to keep it light)
  const list = posts.map(p => ({
    id: p.id,
    title: p.title,
    summary: p.summary,
    coverImage: p.coverImage ? 'yes' : '',
    date: p.date,
    timestamp: p.timestamp
  }));

  return jsonResponse(list);
}

// Handle POST requests (save, delete)
function doPost(e) {
  const body = JSON.parse(e.postData.contents);
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);

  if (body.action === 'save') {
    const post = body.post;
    const data = sheet.getDataRange().getValues();
    const headers = data[0];

    // Check if post exists (update) or is new
    let found = false;
    for (let i = 1; i < data.length; i++) {
      if (data[i][0] == post.id) {
        // Update existing row
        const row = headers.map(h => post[h] || '');
        sheet.getRange(i + 1, 1, 1, row.length).setValues([row]);
        found = true;
        break;
      }
    }

    if (!found) {
      // Append new row
      const row = headers.map(h => post[h] || '');
      sheet.appendRow(row);
    }

    return jsonResponse({ status: 'saved', id: post.id });
  }

  if (body.action === 'delete') {
    const data = sheet.getDataRange().getValues();
    for (let i = 1; i < data.length; i++) {
      if (data[i][0] == body.id) {
        sheet.deleteRow(i + 1);
        break;
      }
    }
    return jsonResponse({ status: 'deleted' });
  }

  return jsonResponse({ status: 'unknown action' });
}

function jsonResponse(data) {
  return ContentService
    .createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}