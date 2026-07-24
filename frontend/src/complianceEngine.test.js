import { describe, expect, test } from "vitest";

import {
  calculateAuthorityMetrics,
  detectAuthorityGroup,
  groupRequirementsByAuthority,
} from "./complianceEngine";

describe("complianceEngine utility", () => {
  test("detects authority group correctly from record text", () => {
    expect(
      detectAuthorityGroup({ authority_name: "DPIIT Startup Recognition" })
    ).toBe("dpiit");

    expect(
      detectAuthorityGroup({ issuing_authority: "FSSAI Licensing Authority" })
    ).toBe("fssai");

    expect(
      detectAuthorityGroup({ certificate_name: "ISO 9001 Quality Certification" })
    ).toBe("iso_bis");
  });

  test("groups canonical schemes and external requirements by authority", () => {
    const schemes = [
      { id: "s1", authority_name: "DPIIT Recognition" },
      { id: "s2", authority_name: "FSSAI Food License" },
    ];
    const external = [
      { id: "e1", issuing_authority: "ISO Certification Board" },
    ];

    const groups = groupRequirementsByAuthority(schemes, external);

    expect(groups.all).toHaveLength(3);
    expect(groups.dpiit).toHaveLength(1);
    expect(groups.fssai).toHaveLength(1);
    expect(groups.iso_bis).toHaveLength(1);
  });

  test("calculates authority metrics correctly", () => {
    const items = [
      { id: "s1", _isCanonical: true },
      { id: "e1", _isExternal: true },
    ];

    const metrics = calculateAuthorityMetrics(items);
    expect(metrics.total).toBe(2);
    expect(metrics.canonicalCount).toBe(1);
    expect(metrics.externalCount).toBe(1);
  });
});
