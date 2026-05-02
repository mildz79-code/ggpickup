// assets/auth.js — shared auth for shipping-web.
// Relies on the same cf_token sessionStorage key used by gg.colorfashiondnf.com.

const TOKEN_KEY = "cf_token";
const USER_KEY  = "cf_user";

function getToken() { return sessionStorage.getItem(TOKEN_KEY); }
function getUser()  {
  try { return JSON.parse(sessionStorage.getItem(USER_KEY) || "null"); }
  catch { return null; }
}

export function requireAuth() {
  const token = getToken();
  if (!token) {
    // Bounce to GG Pickup login, then return here.
    const next = encodeURIComponent(location.href);
    location.href = `https://gg.colorfashiondnf.com/index.html?next=${next}`;
    return null;
  }
  const user = getUser();
  if (user?.display_name) {
    const el = document.getElementById("who-name");
    if (el) el.textContent = user.display_name;
  }
  return user;
}

export function signOut() {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(USER_KEY);
  sessionStorage.setItem("skipAutoLogin", "1");
  location.href = "https://gg.colorfashiondnf.com/index.html";
}

// Wire up if the page has the standard header
document.getElementById("sign-out")?.addEventListener("click", signOut);
requireAuth();
