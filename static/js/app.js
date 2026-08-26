(function () {
  const STORAGE_LANG = "luxe_lang";
  const STORAGE_PRODUCT_VIEW = "luxe_product_view";
  const i18n = window.LUXE_I18N || {};
  let toastTimer;

  function getLang() {
    return localStorage.getItem(STORAGE_LANG) || "ar";
  }

  function tr(key) {
    const lang = getLang();
    return i18n[lang]?.[key] || i18n.ar?.[key] || key;
  }

  function applyTranslations() {
    document.querySelectorAll("[data-i18n]").forEach((element) => {
      element.textContent = tr(element.dataset.i18n);
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
      element.placeholder = tr(element.dataset.i18nPlaceholder);
    });
    document.querySelectorAll("[data-i18n-aria-label]").forEach((element) => {
      element.setAttribute("aria-label", tr(element.dataset.i18nAriaLabel));
    });
  }

  function getProductView() {
    try {
      return localStorage.getItem(STORAGE_PRODUCT_VIEW) === "list" ? "list" : "grid";
    } catch (error) {
      return "grid";
    }
  }

  function setProductView(view, persist = true) {
    const selectedView = view === "list" ? "list" : "grid";
    document.querySelectorAll("[data-product-grid]").forEach((grid) => {
      grid.classList.toggle("is-list", selectedView === "list");
    });
    document.querySelectorAll("[data-product-view]").forEach((button) => {
      const isActive = button.dataset.productView === selectedView;
      button.classList.toggle("active", isActive);
      button.setAttribute("aria-pressed", String(isActive));
    });
    if (persist) {
      try {
        localStorage.setItem(STORAGE_PRODUCT_VIEW, selectedView);
      } catch (error) {
        // The view still works when browser storage is unavailable.
      }
    }
  }

  function showToast(message, isError = false) {
    const toast = document.querySelector("[data-toast]");
    if (!toast) return;
    window.clearTimeout(toastTimer);
    toast.textContent = message;
    toast.classList.toggle("error", isError);
    toast.classList.add("show");
    if (isError) {
      toast.setAttribute("role", "alert");
    } else {
      toast.removeAttribute("role");
    }
    toastTimer = window.setTimeout(() => toast.classList.remove("show"), 3200);
  }

  async function submitCartForm(form) {
    const button = form.querySelector('button[type="submit"]');
    if (!button || button.disabled) return;
    const originalContent = button.innerHTML;
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
    button.textContent = "…";

    try {
      const response = await fetch(form.action, {
        method: form.method,
        credentials: "same-origin",
        body: new FormData(form),
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "Accept": "application/json",
        },
      });
      const contentType = response.headers.get("Content-Type") || "";
      if (response.redirected || !contentType.includes("application/json")) {
        showToast(tr("cart_response_uncertain"), true);
        return;
      }
      let data;
      try {
        data = await response.json();
      } catch (error) {
        showToast(tr("cart_response_uncertain"), true);
        return;
      }
      if (!response.ok || !data.success) {
        showToast(data.message || tr("cart_add_error"), true);
        return;
      }
      document.querySelectorAll("[data-cart-count]").forEach((counter) => {
        counter.textContent = data.cart_count;
        counter.hidden = false;
        counter.classList.remove("hidden");
      });
      showToast(data.message);
    } catch (error) {
      showToast(tr("cart_network_error"), true);
    } finally {
      button.disabled = false;
      button.removeAttribute("aria-busy");
      button.innerHTML = originalContent;
    }
  }

  setProductView(getProductView(), false);

  function setLang(lang) {
    localStorage.setItem(STORAGE_LANG, lang);
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
    document.querySelectorAll("[data-lang-label]").forEach((element) => {
      element.textContent = lang === "ar" ? "EN" : "AR";
    });
    applyTranslations();
  }

  document.addEventListener("DOMContentLoaded", () => {
    setLang(getLang());
    setProductView(getProductView(), false);
    document.querySelectorAll("[data-product-view]").forEach((button) => {
      button.addEventListener("click", () => setProductView(button.dataset.productView));
    });
    document.addEventListener("submit", (event) => {
      const form = event.target.closest("form[data-cart-add-form]");
      if (!form) return;
      event.preventDefault();
      submitCartForm(form);
    });
    document.querySelector("[data-lang-toggle]")?.addEventListener("click", () => {
      setLang(getLang() === "ar" ? "en" : "ar");
    });
    const menu = document.querySelector("[data-nav-links]");
    document.querySelector("[data-menu-toggle]")?.addEventListener("click", () => {
      menu?.classList.toggle("open");
    });
  });
})();
