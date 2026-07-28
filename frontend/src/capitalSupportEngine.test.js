import { describe, expect, test } from "vitest";

import {
  calculateCapitalMetrics,
  categorizeCapitalSupport,
  isDebtFacility,
} from "./capitalSupportEngine";

describe("capitalSupportEngine utility", () => {
  test("detects debt facility vs grant correctly", () => {
    expect(isDebtFacility({ funding_type: "Working Capital Loan" })).toBe(true);
    expect(isDebtFacility({ funding_type: "Grant & Seed Fund" })).toBe(false);
  });

  test("categorizes capital support records", () => {
    const schemes = [
      { id: "s1", funding_type: "Seed Grant" },
      { id: "s2", funding_type: "Working Capital Loan" },
    ];
    const external = [
      { id: "e1", funding_type: "Credit Guarantee Facility" },
    ];

    const result = categorizeCapitalSupport(schemes, external);

    expect(result.total).toBe(3);
    expect(result.grants).toHaveLength(1);
    expect(result.loans).toHaveLength(2);
  });

  test("calculates capital metrics", () => {
    const metrics = calculateCapitalMetrics([{ id: "1" }], [{ id: "2" }]);
    expect(metrics.totalRecords).toBe(2);
    expect(metrics.verifiedCount).toBe(1);
    expect(metrics.externalCount).toBe(1);
  });
});
