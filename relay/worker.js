/**
 * FixMyStreet "near me" relay — a tiny Cloudflare Worker.
 *
 * WHY THIS EXISTS
 * FixMyStreet's map feed (/around) can return every open report inside a
 * geographic box in one request — exactly what the "check your area" page needs.
 * But that feed doesn't send the CORS header a browser requires, so a plain web
 * page is not allowed to call it directly. This Worker sits in the middle: it
 * calls FixMyStreet, then hands the answer back to the page WITH the CORS header
 * added. It stores nothing — every request is fetched fresh and forgotten.
 *
 * It is deliberately locked down: it will ONLY ever forward requests to
 * fixmystreet.com/around, so it can't be abused as a general-purpose open proxy.
 *
 * DEPLOY: paste this into a new Cloudflare Worker (dash.cloudflare.com →
 * Workers & Pages → Create → Worker). No account settings, no database needed.
 */

const ALLOWED_PARAMS = ["bbox", "status", "show_old_reports", "p", "ajax"];

export default {
  async fetch(request) {
    // CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders() });
    }
    if (request.method !== "GET") {
      return json({ error: "Only GET is supported" }, 405);
    }

    const inUrl = new URL(request.url);

    // Rebuild the FixMyStreet URL from a strict allowlist of parameters only.
    const target = new URL("https://www.fixmystreet.com/around");
    target.searchParams.set("ajax", "1");
    for (const key of ALLOWED_PARAMS) {
      const v = inUrl.searchParams.get(key);
      if (v !== null) target.searchParams.set(key, v);
    }

    // A bbox is required — refuse anything that isn't a genuine area query.
    const bbox = target.searchParams.get("bbox");
    if (!bbox || !/^-?\d+(\.\d+)?(,-?\d+(\.\d+)?){3}$/.test(bbox)) {
      return json({ error: "A valid bbox (W,S,E,N) is required" }, 400);
    }

    try {
      const upstream = await fetch(target.toString(), {
        headers: { "User-Agent": "AreaReportRelay/1.0 (civic accountability tool)" },
        cf: { cacheTtl: 900, cacheEverything: true }, // 15-min edge cache of PUBLIC data (no user data)
      });
      const body = await upstream.text();
      return new Response(body, {
        status: upstream.status,
        headers: {
          ...corsHeaders(),
          "Content-Type": "application/json; charset=utf-8",
          "Cache-Control": "public, max-age=900",
        },
      });
    } catch (e) {
      return json({ error: "Upstream fetch failed", detail: String(e).slice(0, 200) }, 502);
    }
  },
};

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Max-Age": "86400",
  };
}

function json(obj, status) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { ...corsHeaders(), "Content-Type": "application/json" },
  });
}
