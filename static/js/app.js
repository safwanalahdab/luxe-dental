(function () {
  const STORAGE_LANG = "luxe_lang";
  const i18n = window.LUXE_I18N || {};

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
  }

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
    document.querySelector("[data-lang-toggle]")?.addEventListener("click", () => {
      setLang(getLang() === "ar" ? "en" : "ar");
    });
    const menu = document.querySelector("[data-nav-links]");
    document.querySelector("[data-menu-toggle]")?.addEventListener("click", () => {
      menu?.classList.toggle("open");
    });
  });
})();
