# "Check your area" — how to put it live

You have two files that make this work:

- **`docs/anywhere.html`** — the web page people use (a council dropdown + postcode box).
  Goes on GitHub Pages alongside your existing dashboard. Stores nothing.
- **`relay/worker.js`** — a tiny free "relay" on Cloudflare. FixMyStreet's fast
  map feed won't let a plain web page call it directly, so this passes the request
  through. It has no database and keeps nothing about anyone.

You set the relay up **once**. After that the page just works for everyone.

---

## Step 1 — Create the free Cloudflare relay (about 5 minutes)

1. Go to **https://dash.cloudflare.com** and sign up / log in (free — no card needed).
2. In the left menu click **Workers & Pages**, then **Create application** →
   **Create Worker**.
3. Give it a name, e.g. `street-reports-relay`. Click **Deploy** (it deploys a
   placeholder).
4. Click **Edit code**. Delete everything in the editor, then paste the entire
   contents of `relay/worker.js`. Click **Deploy** (top right).
5. Cloudflare shows the Worker's address, like
   `https://street-reports-relay.YOUR-NAME.workers.dev`.
   **Copy that address** — you need it in Step 2.

## Step 2 — Point the page at your relay

1. Open `docs/anywhere.html` in a text editor.
2. Near the top of the `<script>` section, find this line:

   ```js
   const WORKER_URL = "https://REPLACE-WITH-YOUR-WORKER.workers.dev/around";
   ```

3. Replace it with your Worker address from Step 1, **keeping `/around` on the end**:

   ```js
   const WORKER_URL = "https://street-reports-relay.YOUR-NAME.workers.dev/around";
   ```

4. Save the file.

## Step 3 — Publish the page

Put `anywhere.html` in the same `docs/` folder that already publishes your Oswestry
dashboard, commit, and push. It will be live at
`https://shutpa01.github.io/oswestry-street-reports/anywhere.html`
(or link to it from your main dashboard).

---

## Trying it on your own computer first (optional)

You don't need Cloudflare to test locally — there's a stand-in relay:

1. In one terminal:  `py relay/local_relay.py`  (starts the local relay)
2. In another:       `py -m http.server 8137`  (run this inside the `docs/` folder)
3. Open `http://localhost:8137/anywhere.html`

The page automatically uses the local relay when it sees `localhost`, and your real
Cloudflare relay everywhere else — so the same file works in both places.

---

## Good to know

- **Nothing is stored about users.** Each visit fetches fresh from FixMyStreet and
  is forgotten. The Worker briefly (15 min) keeps a copy of the *public* report list
  for an area so repeat visits are instant — that's public council data, not anyone's
  personal information, and it expires on its own.
- **It's polite to FixMyStreet.** The page fetches an area's reports in a few pages
  and the relay caches them, so FixMyStreet isn't hit hard even if the tool gets busy.
- **Free limits are ample.** Cloudflare's free plan allows 100,000 relay requests a
  day — far more than this needs.
- **What it shows:** every currently-open report in the chosen area, how long each has
  been waiting, an aging breakdown, and a searchable list linking back to FixMyStreet.
  It does **not** include the "42% of closures weren't fixed" analysis — that one needs
  data gathered ahead of time, which is why it stays exclusive to your Oswestry
  dashboard.
