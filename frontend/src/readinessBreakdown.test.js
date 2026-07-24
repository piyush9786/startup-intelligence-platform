import { describe, expect, test } from "vitest";
import {
  buildDomainBreakdown,
  buildRoadmapWaves,
} from "./readinessBreakdown";

describe("readinessBreakdown utility", () => {
  test("categorizes findings into 5 core domains with computed scores", () => {
    const sampleAssessment = {
      findings: [
        {
          code: "F_NAME",
          field_path: "startup_name",
          priority: "critical",
          outcome: "present",
          reason: "Startup name provided",
        },
        {
          code: "F_LEGAL",
          field_path: "legal_name",
          priority: "recommended",
          outcome: "missing",
          reason: "Legal name missing",
        },
        {
          code: "F_DPIIT",
          field_path: "dpiit_recognized",
          priority: "critical",
          outcome: "present",
          reason: "DPIIT recognized",
        },
        {
          code: "F_SECTOR",
          field_path: "sectors",
          priority: "recommended",
          outcome: "present",
          reason: "Sectors provided",
        },
      ],
    };

    const breakdown = buildDomainBreakdown(sampleAssessment);
    expect(breakdown).toHaveLength(5);

    const legalDomain = breakdown.find((d) => d.id === "legal");
    expect(legalDomain.findings).toHaveLength(2);
    expect(legalDomain.score).toBe(50); // 1 present out of 2 total

    const complianceDomain = breakdown.find((d) => d.id === "compliance");
    expect(complianceDomain.findings).toHaveLength(1);
    expect(complianceDomain.score).toBe(100);
  });

  test("organizes action items into 3 execution waves", () => {
    const sampleActionPlan = {
      items: [
        {
          id: "item-1",
          title: "Register DPIIT Recognition",
          priority: "critical",
          item_type: "readiness_action",
        },
        {
          id: "item-2",
          title: "Explore Seed Fund Scheme",
          priority: "recommended",
          item_type: "scheme_opportunity",
        },
      ],
    };

    const waves = buildRoadmapWaves(sampleActionPlan, {});
    expect(waves).toHaveLength(3);
    expect(waves[0].items).toHaveLength(1);
    expect(waves[0].items[0].title).toBe("Register DPIIT Recognition");
    expect(waves[1].items).toHaveLength(1);
    expect(waves[1].items[0].title).toBe("Explore Seed Fund Scheme");
  });
});
