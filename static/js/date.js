const now = new Date();
const options = {
  weekday: "long",
  year: "numeric",
  month: "long",
  day: "numeric",
};
const dateStr = now.toLocaleDateString("id-ID", options);
document.getElementById("date").textContent = dateStr;
