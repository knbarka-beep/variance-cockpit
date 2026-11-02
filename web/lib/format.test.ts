// Run: npm test   (Node runs TypeScript directly)
import { test } from "node:test";
import assert from "node:assert/strict";
import { label, signed, amount, groupSignificant, last12, materialsSplit, millions, monthLabel, pct } from "./format.ts";

test("European number format", () => {
  assert.equal(millions(-236321), "DKK 0,24m");
  assert.equal(amount(-236321.4), "−236.321");
  assert.equal(pct(-8.94), "8,9 %");
  assert.equal(monthLabel("2026-09"), "Sep 2026");
  assert.equal(signed(14432), "+14.432");
  assert.equal(label("one_off"), "One-off");
  assert.equal(label("unclear"), "Unclear");
  assert.deepEqual(last12(["a", "b", "c"], "b"), ["a", "b"]);
});

test("price row stands alone when its account total is not significant (Sep 2026)", () => {
  const g = groupSignificant([
    { variance_id: "s_1010", variance_type: "total", cell_id: "s_1010" },
    { variance_id: "s_2010_price", variance_type: "price", cell_id: "s_2010" },
  ]);
  assert.equal(g.count, 2);
  assert.equal(g.priceEffects, 1);
  assert.equal(g.top.length, 2);
});

test("price row becomes a sub-row when its account total is significant", () => {
  const g = groupSignificant([
    { variance_id: "s_2010", variance_type: "total", cell_id: "s_2010" },
    { variance_id: "s_2010_price", variance_type: "price", cell_id: "s_2010" },
  ]);
  assert.equal(g.count, 1);
  assert.equal(g.top.length, 1);
  assert.equal(g.subRows.get("s_2010")?.variance_id, "s_2010_price");
});

test("raw materials split sentence", () => {
  assert.equal(materialsSplit({ price_usage_variance_profit_dkk: -368034, volume_variance_profit_dkk: 202778,
    total_variance_profit_dkk: -165256, volume_pct_of_budget: 95.2 }),
  "Price effect DKK 0,37m unfavourable, partly offset by lower volume DKK 0,20m favourable. Total DKK 0,17m unfavourable.");
});
