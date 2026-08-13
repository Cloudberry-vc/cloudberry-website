# Cloudberry VC Website — Blog Setup Guide

## What you have

Your website folder contains:

| File | What it does |
|------|-------------|
| `index.html` | The main website |
| `admin.html` | Hidden blog admin page (yoursite.com/admin.html) |
| `post.html` | Individual blog post viewer |
| `backend-script.js` | The code to paste into Google Apps Script |
| `assets/` | Logos and images |

## How it works

The blog uses **Google Sheets as a free database**. A tiny script on Google's servers connects your admin page to the spreadsheet. No hosting costs, no servers to maintain.

## Setup (one time, ~5 minutes)

### Step 1: Create the Google Sheet + Script

1. Go to [Google Sheets](https://sheets.google.com) and create a new blank spreadsheet
2. Name it "Cloudberry Blog Posts"
3. Click **Extensions** > **Apps Script**
4. Delete the default code in the editor
5. Open `backend-script.js` from this folder and copy ALL the code
6. Paste it into the Apps Script editor
7. Click **Save** (Ctrl+S)

### Step 2: Run initial setup

1. In the Apps Script editor, select `setup` from the function dropdown (top toolbar)
2. Click **Run**
3. Google will ask you to authorize — click through and allow it
4. You should see "Setup complete!" in the log

### Step 3: Deploy as web app

1. Click **Deploy** > **New deployment** (top right)
2. Click the gear icon and choose **Web app**
3. Set "Execute as": **Me**
4. Set "Who has access": **Anyone**
5. Click **Deploy**
6. Copy the URL it gives you (looks like `https://script.google.com/macros/s/ABC.../exec`)

### Step 4: Paste the URL into your site

Open these 3 files and paste the URL where indicated:

1. **`admin.html`** — find `const BACKEND_URL = '';` and paste between the quotes
2. **`post.html`** — find `const BACKEND_URL = '';` and paste between the quotes
3. **`index.html`** — find `const BLOG_BACKEND_URL = '';` and paste between the quotes

### Step 5: Upload to GoDaddy

Upload the entire `cloudberry-website` folder to your GoDaddy hosting.

## Done!

### To write a blog post:

1. Go to `yoursite.com/admin.html`
2. Enter the team password (default: `cloudberry2025` — change it in admin.html)
3. Write your post with the rich editor — add images, formatting, links, embeds
4. Click **Publish**
5. The post card appears automatically on the main site

### To change the admin password:

Open `admin.html` and find `const ADMIN_PASSWORD = 'cloudberry2025';` — change it to whatever you want.

### To add team photos:

Drop photos in the `assets/` folder and update the team section in `index.html`. Replace:
```html
<div class="team-photo-placeholder"><span class="initials">RK</span></div>
```
with:
```html
<div class="team-photo" style="background-image: url('assets/rene.jpg');"></div>
```

## Post pages and SEO (important)

Individual articles are served as **static pages** under `news/<slug>/index.html`,
generated from the JSON in `posts/`. Each page has its own title, meta
description, Open Graph / Twitter tags (so LinkedIn shows a proper preview
card), and NewsArticle structured data.

**After adding or editing any post** (i.e. after changing `posts/posts.json`
or any `posts/<slug>.json`), regenerate the static pages:

```
python3 generate_posts.py
```

Then commit the updated `news/` directory along with your post changes.

The generator builds each page from `post_template.html` (do not delete it; `post.html` itself is only a redirect for old links). Emails in post content should use the bot-safe `name [at] cloudberry.vc` text form, since static post pages do not run the email-rebuild script.

- Clean URLs: `cloudberry.vc/news/<slug>/`
- The old `post.html?id=<slug>` links still work (they redirect to the clean URL).
- Social share image: `assets/og-share.png` (used as the default preview image).
