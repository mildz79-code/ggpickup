// assets/views/schedule.js — Today's schedule board with native HTML5 drag-and-drop.
// Pool (left) = unscheduled pickups + unscheduled deliveries.
// Route (right) = ordered schedule_stops. Reordering persists via /api/shipping/stops/reorder.

import { shipping } from "../api.js";

const $ = (id) => document.getElementById(id);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

const fmt = new Intl.DateTimeFormat(undefined, {
  weekday: "long", month: "long", day: "numeric", year: "numeric",
});

let state = {
  date: null,
  pickups: [],
  deliveries: [],
  stops: [],
};

// ---------- rendering ----------

function renderHeader() {
  const d = state.date ? new Date(state.date + "T00:00:00") : new Date();
  $("day-title").textContent = fmt.format(d);
  $("count-pickups").textContent    = state.pickups.length;
  $("count-deliveries").textContent = state.deliveries.length;
  $("count-stops").textContent      = state.stops.length;
}

function itemLabel(item, type) {
  if (type === "pickup") {
    const lot = item.lot_number ? ` · ${item.lot_number}` : "";
    return `${item.knitter} → ${item.customer}${lot} · ${item.qty}`;
  }
  const lot = item.lot_number ? ` · ${item.lot_number}` : "";
  return `${item.customer_code}${lot} · ${item.qty}`;
}

function itemEl(item, type, inRoute = false) {
  const li = document.createElement("li");
  li.draggable = true;
  li.dataset.type = type;
  li.dataset.id   = item.id;
  if (inRoute && item.stop_id) li.dataset.stopId = item.stop_id;
  li.innerHTML = `
    <span class="tag ${type}">${type}</span>
    <span class="body">${itemLabel(item, type)}</span>
  `;
  li.addEventListener("dragstart", onDragStart);
  li.addEventListener("dragend",   onDragEnd);
  return li;
}

function render() {
  renderHeader();

  // Pool: items not referenced by any stop
  const inRoutePickups    = new Set(state.stops.filter(s => s.stop_type === "pickup").map(s => s.ref_id));
  const inRouteDeliveries = new Set(state.stops.filter(s => s.stop_type === "delivery").map(s => s.ref_id));

  const poolP = $("pool-pickups");    poolP.innerHTML = "";
  const poolD = $("pool-deliveries"); poolD.innerHTML = "";
  state.pickups   .filter(p => !inRoutePickups.has(p.id))   .forEach(p => poolP.appendChild(itemEl(p, "pickup")));
  state.deliveries.filter(d => !inRouteDeliveries.has(d.id)).forEach(d => poolD.appendChild(itemEl(d, "delivery")));

  // Route: ordered by sequence
  const route = $("route"); route.innerHTML = "";
  const byId = {
    pickup:   Object.fromEntries(state.pickups.map(p => [p.id, p])),
    delivery: Object.fromEntries(state.deliveries.map(d => [d.id, d])),
  };
  [...state.stops].sort((a, b) => a.sequence - b.sequence).forEach(stop => {
    const item = byId[stop.stop_type]?.[stop.ref_id];
    if (!item) return;
    route.appendChild(itemEl({ ...item, stop_id: stop.id }, stop.stop_type, true));
  });
}

// ---------- drag and drop ----------

let dragging = null;

function onDragStart(e) {
  dragging = e.currentTarget;
  dragging.classList.add("dragging");
  e.dataTransfer.effectAllowed = "move";
}
function onDragEnd()   { dragging?.classList.remove("dragging"); dragging = null; }

function onDragOver(e) {
  if (!dragging) return;
  e.preventDefault();
  const list = e.currentTarget;
  const after = getDragAfter(list, e.clientY);
  if (!after) list.appendChild(dragging);
  else list.insertBefore(dragging, after);
}

function getDragAfter(list, y) {
  const els = [...list.querySelectorAll("li:not(.dragging)")];
  return els.reduce((closest, el) => {
    const box = el.getBoundingClientRect();
    const offset = y - box.top - box.height / 2;
    if (offset < 0 && offset > closest.offset) return { offset, el };
    return closest;
  }, { offset: -Infinity, el: null }).el;
}

async function onDrop(e) {
  e.preventDefault();
  if (!dragging) return;
  const targetList = e.currentTarget;
  const type = dragging.dataset.type;
  const id   = Number(dragging.dataset.id);

  if (targetList.id === "route") {
    // Add or reorder stops
    if (!dragging.dataset.stopId) {
      // new stop
      try {
        await shipping.addStop({ stop_type: type, ref_id: id, sequence: targetList.children.length });
      } catch (err) { alert(`Couldn't add stop: ${err.message}`); return await refresh(); }
    }
    // Persist new order
    const order = [...targetList.querySelectorAll("li")].map((li, idx) => ({
      id: Number(li.dataset.stopId), sequence: idx + 1,
    })).filter(o => o.id);
    try {
      if (order.length) await shipping.reorderStops(order);
    } catch (err) { alert(`Couldn't reorder: ${err.message}`); }
    await refresh();
  } else {
    // Dropped back into pool → remove stop if it was one
    if (dragging.dataset.stopId) {
      try { await shipping.removeStop(Number(dragging.dataset.stopId)); }
      catch (err) { alert(`Couldn't remove stop: ${err.message}`); }
    }
    await refresh();
  }
}

// ---------- data ----------

async function refresh() {
  try {
    const data = await shipping.today();
    state = {
      date:       data.schedule_date,
      pickups:    data.pickups || [],
      deliveries: data.deliveries || [],
      stops:      (data.stops || []).map(s => ({
        id: s.id,
        stop_type: s.stop_type,
        ref_id: s.pickup_request_id ?? s.delivery_request_id ?? s.ref_id,
        sequence: s.sequence,
      })),
    };
    render();
  } catch (err) {
    console.error(err);
    $("day-title").textContent = "Couldn't load schedule";
    $$(".counts strong").forEach(el => el.textContent = "—");
  }
}

// ---------- init ----------

["route", "pool-pickups", "pool-deliveries"].forEach(id => {
  const el = $(id);
  el.addEventListener("dragover", onDragOver);
  el.addEventListener("drop",     onDrop);
});

refresh();
