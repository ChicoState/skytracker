const assert = require("node:assert/strict");
const {
  filterConstellations,
  normalizeConstellation,
} = require("../static/skytracker/constellation-filters.js");

const constellations = [
  { id: "Ori", properties: { n: "Orion" } },
  { id: "UMa", properties: { n: "Ursa Major" } },
];

assert.deepEqual(normalizeConstellation(constellations[0]), {
  id: "Ori",
  name: "Orion",
});

assert.deepEqual(filterConstellations(constellations, "orion"), [
  { id: "Ori", name: "Orion" },
]);

assert.deepEqual(filterConstellations(constellations, "uma"), [
  { id: "UMa", name: "Ursa Major" },
]);

assert.deepEqual(filterConstellations(constellations, ""), [
  { id: "Ori", name: "Orion" },
  { id: "UMa", name: "Ursa Major" },
]);
