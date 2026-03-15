const map = L.map("map").setView([10, 20], 3);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  maxZoom: 18
}).addTo(map);

const statusColors = {
  active: "#22c55e",
  scheduled: "#3b82f6",
  completed: "#94a3b8",
  paused: "#f59e0b"
};

function createMarkerIcon(status) {
  return L.divIcon({
    className: "",
    html: `<div class="status-marker ${status}"></div>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8]
  });
}

function showSidebar(conversation) {
  const sidebar = document.getElementById("sidebar");
  const content = document.getElementById("sidebar-content");

  content.innerHTML = `
    <h2>${conversation.title}</h2>
    <div class="detail-row">
      <span class="label">Status</span>
      <span class="value"><span class="status-badge ${conversation.status}">${conversation.status}</span></span>
    </div>
    <div class="detail-row">
      <span class="label">Location</span>
      <span class="value">${conversation.location}</span>
    </div>
    <div class="detail-row">
      <span class="label">Partner</span>
      <span class="value">${conversation.partner}</span>
    </div>
    <div class="detail-row">
      <span class="label">Started</span>
      <span class="value">${conversation.startDate}</span>
    </div>
    <div class="detail-row">
      <span class="label">Last Update</span>
      <span class="value">${conversation.lastUpdate}</span>
    </div>
    <div class="notes">${conversation.notes}</div>
  `;

  sidebar.classList.remove("hidden");
}

document.getElementById("sidebar-close").addEventListener("click", function () {
  document.getElementById("sidebar").classList.add("hidden");
});

conversations.forEach(function (conv) {
  var marker = L.marker([conv.lat, conv.lng], {
    icon: createMarkerIcon(conv.status)
  }).addTo(map);

  marker.bindTooltip(conv.title, { direction: "top", offset: [0, -10] });

  marker.on("click", function () {
    showSidebar(conv);
  });
});
