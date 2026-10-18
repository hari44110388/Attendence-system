/**
 * AttendanceSystem - Client-side Utilities and Interactive Enhancements
 */

document.addEventListener("DOMContentLoaded", function () {
  // 1. Mobile Sidebar Toggle
  const sidebarToggle = document.getElementById("sidebarToggle");
  const sidebar = document.querySelector(".sidebar");
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener("click", function () {
      sidebar.classList.toggle("show");
    });
  }

  // 2. Auto-dismiss Bootstrap Alerts after 5 seconds
  const autoAlerts = document.querySelectorAll(".alert-dismissible");
  autoAlerts.forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) {
        bsAlert.close();
      }
    }, 6000);
  });

  // 3. Mark All Attendance Shortcuts
  const markAllPresentBtn = document.getElementById("markAllPresentBtn");
  const markAllAbsentBtn = document.getElementById("markAllAbsentBtn");
  const markAllLateBtn = document.getElementById("markAllLateBtn");

  if (markAllPresentBtn) {
    markAllPresentBtn.addEventListener("click", function () {
      document.querySelectorAll('input[type="radio"][value="present"]').forEach(function (radio) {
        radio.checked = true;
      });
    });
  }

  if (markAllAbsentBtn) {
    markAllAbsentBtn.addEventListener("click", function () {
      document.querySelectorAll('input[type="radio"][value="absent"]').forEach(function (radio) {
        radio.checked = true;
      });
    });
  }

  if (markAllLateBtn) {
    markAllLateBtn.addEventListener("click", function () {
      document.querySelectorAll('input[type="radio"][value="late"]').forEach(function (radio) {
        radio.checked = true;
      });
    });
  }

  // 4. Quick Live Table Search Filter (Client-side fast search)
  const quickSearchInput = document.getElementById("quickTableSearch");
  if (quickSearchInput) {
    quickSearchInput.addEventListener("keyup", function () {
      const filter = quickSearchInput.value.toLowerCase();
      const rows = document.querySelectorAll(".searchable-table tbody tr");
      rows.forEach(function (row) {
        const text = row.textContent.toLowerCase();
        row.style.display = text.indexOf(filter) > -1 ? "" : "none";
      });
    });
  }

  // 5. Delete Confirmation Modal
  const deleteModal = document.getElementById("deleteConfirmModal");
  if (deleteModal) {
    deleteModal.addEventListener("show.bs.modal", function (event) {
      const button = event.relatedTarget;
      const actionUrl = button.getAttribute("data-action");
      const itemName = button.getAttribute("data-name") || "this item";
      
      const form = deleteModal.querySelector("#deleteConfirmForm");
      const itemSpan = deleteModal.querySelector("#deleteItemName");
      
      if (form && actionUrl) form.action = actionUrl;
      if (itemSpan) itemSpan.textContent = itemName;
    });
  }
});
