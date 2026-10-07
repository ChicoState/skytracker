(function (global, factory) {
  const api = factory();

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }

  if (global) {
    global.SkyTrackerConstellationFilters = api;
  }
})(typeof window === "undefined" ? null : window, function () {
  "use strict";

  function normalizeConstellation(constellation) {
    if (!constellation) {
      return null;
    }

    const properties = constellation.properties || {};
    const id = constellation.id || properties.id;
    const name = constellation.name || properties.n || properties.name;

    if (!id || !name) {
      return null;
    }

    return { id: String(id), name: String(name) };
  }

  function filterConstellations(constellations, query) {
    const normalizedQuery = String(query || "").trim().toLowerCase();

    return constellations
      .map(normalizeConstellation)
      .filter(Boolean)
      .filter((constellation) => {
        if (!normalizedQuery) {
          return true;
        }

        return (
          constellation.name.toLowerCase().includes(normalizedQuery) ||
          constellation.id.toLowerCase().includes(normalizedQuery)
        );
      })
      .sort((left, right) => left.name.localeCompare(right.name));
  }

  function create(root, options) {
    if (!root) {
      throw new Error("A filter root element is required.");
    }

    const config = options || {};
    const searchInput = root.querySelector("[data-constellation-search]");
    const select = root.querySelector("[data-constellation-select]");
    const clearButton = root.querySelector("[data-constellation-clear]");
    const count = root.querySelector("[data-constellation-count]");

    if (!searchInput || !select || !clearButton || !count) {
      throw new Error("The filter template is missing a required control.");
    }

    let constellations = [];

    function state() {
      const matches = filterConstellations(constellations, searchInput.value);
      return {
        query: searchInput.value.trim(),
        selectedId: select.value || null,
        matches,
      };
    }

    function renderOptions() {
      const selectedId = select.value;
      const matches = filterConstellations(constellations, searchInput.value);

      select.replaceChildren();
      const allOption = document.createElement("option");
      allOption.value = "";
      allOption.textContent = "All matching constellations";
      select.append(allOption);

      matches.forEach((constellation) => {
        const option = document.createElement("option");
        option.value = constellation.id;
        option.textContent = `${constellation.name} (${constellation.id})`;
        option.selected = constellation.id === selectedId;
        select.append(option);
      });

      if (selectedId && !matches.some(({ id }) => id === selectedId)) {
        select.value = "";
      }

      count.textContent = `${matches.length} constellation${matches.length === 1 ? "" : "s"}`;
    }

    function notify() {
      const detail = state();
      root.dispatchEvent(
        new CustomEvent("skytracker:constellation-filter-change", {
          bubbles: true,
          detail,
        }),
      );

      if (typeof config.onChange === "function") {
        config.onChange(detail);
      }
    }

    function refresh() {
      renderOptions();
      notify();
    }

    searchInput.addEventListener("input", refresh);
    select.addEventListener("change", notify);
    clearButton.addEventListener("click", () => {
      searchInput.value = "";
      select.value = "";
      refresh();
      searchInput.focus();
    });

    function setConstellations(items) {
        constellations = Array.isArray(items) ? items : [];
        refresh();
    }

    return {
      setConstellations,
      setGeoJson(geoJson) {
        setConstellations(geoJson && geoJson.features);
      },
      getState: state,
    };
  }

  return { create, filterConstellations, normalizeConstellation };
});
