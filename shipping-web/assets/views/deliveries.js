// assets/views/deliveries.js — manual delivery entry + list.
// Backend: /api/shipping/deliveries (GET list on /api/shipping/day/today for now; Phase 3 can add a dedicated endpoint)

import { shipping, apiGet } from "../api.js";

const $ = (id) => document.getElementById(id);

// Default the date input to today
$("new-delivery").request_date.valueAsDate = new Date();

$("new-delivery").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = e.currentTarget;
  const body = {
    request_date:  f.request_date.value,
    customer_code: f.customer_code.value.trim().toUpperCase(),
    lot_number:    f.lot_number.value.trim() || null,
    qty:           Number(f.qty.value) || 1,
  };
  try {
    await shipping.createDelivery(body);
    f.customer_code.value = "";
    f.lot_number.value = "";
    f.qty.value = 1;
    f.customer_code.focus();
    await refresh();
  } catch (err) {
    alert(`Couldn't save: ${err.message}`);
  }
});

function row(d) {
  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td class="mono">${d.request_date}</td>
    <td class="mono">${d.customer_code}</td>
    <td class="mono">${d.lot_number ?? ""}</td>
    <td class="mono">${d.qty}</td>
    <td><span class="pill ${d.status.toLowerCase()}">${d.status}</span></td>
    <td><span class="pill ${d.source}">${d.source}</span></td>
  `;
  return tr;
}

async function refresh() {
  try {
    // Backend endpoint TBD (Phase 3.2) — using today's schedule payload for now
    const data = await shipping.today();
    const list = data.deliveries || [];
    $("count").textContent = list.length;
    const tbody = $("rows");
    tbody.innerHTML = "";
    if (!list.length) {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td colspan="6" class="empty">No deliveries on record yet.</td>`;
      tbody.appendChild(tr);
      return;
    }
    list.forEach(d => tbody.appendChild(row(d)));
  } catch (err) {
    console.error(err);
    $("count").textContent = "—";
    $("rows").innerHTML = `<tr><td colspan="6" class="empty">Couldn't load: ${err.message}</td></tr>`;
  }
}

refresh();
