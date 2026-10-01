// Simple UX enhancement: show a "Generating..." state on submit so the
// user knows the AI request is in progress (Gemini calls can take a few
// seconds). No frameworks needed - plain JS as per the project spec.

document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("form.fitbuddy-form").forEach(function (form) {
        form.addEventListener("submit", function () {
            var btn = form.querySelector("button[type='submit']");
            if (btn && !btn.disabled) {
                btn.dataset.originalText = btn.textContent;
                btn.textContent = "Please wait... generating with AI";
                btn.disabled = true;
                btn.style.opacity = "0.7";
            }
        });
    });
});

// If the user comes back with the browser's Back button, the page may be
// restored from cache with the button still disabled - reset it.
window.addEventListener("pageshow", function () {
    document.querySelectorAll("form.fitbuddy-form button[type='submit']").forEach(function (btn) {
        if (btn.dataset.originalText) {
            btn.textContent = btn.dataset.originalText;
            btn.disabled = false;
            btn.style.opacity = "";
        }
    });
});
