import {
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import {
  beforeEach,
  describe,
  expect,
  test,
  vi,
} from "vitest";

import FounderConcierge from "./FounderConcierge";


const mocks = vi.hoisted(() => ({
  getCurrent: vi.fn(),
  submitAssessment: vi.fn(),
  transition: vi.fn(),
  updateDraft: vi.fn(),
}));


vi.mock("./conciergeApi", () => ({
  getConciergeCurrent: mocks.getCurrent,
  submitConciergeAssessment: mocks.submitAssessment,
  transitionConcierge: mocks.transition,
  updateConciergeDraft: mocks.updateDraft,
}));


function payload(overrides = {}) {
  return {
    allowed_fields: [],
    assessment_step: 1,
    completed_states: [],
    confirmation_required: false,
    created: false,
    current_state: "greeting",
    draft: {
      current_step: 1,
      data: {},
      id: "draft-1",
      status: "draft",
    },
    is_terminal: false,
    prompt: "Welcome to the bounded assessment.",
    session_id: "session-1",
    state_count: 9,
    state_index: 0,
    system_transition_required: false,
    title: "Welcome",
    version: "founder-concierge-v1",
    ...overrides,
  };
}


function openConcierge() {
  fireEvent.click(
    screen.getByRole("button", {
      name: "Open startup concierge",
    }),
  );
}


describe("founder startup concierge", () => {
  beforeEach(() => {
    mocks.getCurrent.mockReset();
    mocks.submitAssessment.mockReset();
    mocks.transition.mockReset();
    mocks.updateDraft.mockReset();
  });

  test("loads authoritative state only when opened", async () => {
    mocks.getCurrent.mockResolvedValue(payload());

    render(<FounderConcierge />);

    expect(mocks.getCurrent).not.toHaveBeenCalled();

    openConcierge();

    expect(
      await screen.findByRole("dialog", {
        name: "Startup concierge",
      }),
    ).toBeInTheDocument();
    expect(
      await screen.findByText(
        "Welcome to the bounded assessment.",
      ),
    ).toBeInTheDocument();
    expect(mocks.getCurrent).toHaveBeenCalledWith({
      startupProfileId: undefined,
    });
  });

  test("continues using the expected backend state", async () => {
    mocks.getCurrent.mockResolvedValue(payload());
    mocks.transition.mockResolvedValue(
      payload({
        allowed_fields: [
          "startup_name",
        ],
        current_state: "basic_info",
        prompt: "Provide startup basics.",
        state_index: 1,
        title: "Startup basics",
      }),
    );

    render(<FounderConcierge />);

    openConcierge();

    fireEvent.click(
      await screen.findByRole("button", {
        name: "Continue",
      }),
    );

    await waitFor(() => {
      expect(mocks.transition).toHaveBeenCalledWith({
        draftId: "draft-1",
        expectedState: "greeting",
        startupProfileId: undefined,
      });
    });

    expect(
      await screen.findByLabelText("Startup name"),
    ).toBeInTheDocument();
  });

  test("renders and saves only allowed fields", async () => {
    const basicPayload = payload({
      allowed_fields: [
        "startup_name",
        "sectors",
      ],
      current_state: "basic_info",
      draft: {
        current_step: 1,
        data: {
          startup_name: "Original Startup",
        },
        id: "draft-1",
        status: "draft",
      },
      state_index: 1,
      title: "Startup basics",
    });

    mocks.getCurrent.mockResolvedValue(basicPayload);
    mocks.updateDraft.mockResolvedValue(basicPayload);

    render(<FounderConcierge />);

    openConcierge();

    const startupName = await screen.findByLabelText(
      "Startup name",
    );
    const sectors = screen.getByRole("textbox", {
      name: /Sectors/i,
    });

    expect(
      screen.queryByLabelText("Funding required"),
    ).not.toBeInTheDocument();

    fireEvent.change(startupName, {
      target: {
        value: "Updated Startup",
      },
    });
    fireEvent.change(sectors, {
      target: {
        value: "climate, mobility",
      },
    });
    fireEvent.click(
      screen.getByRole("button", {
        name: "Save answers",
      }),
    );

    await waitFor(() => {
      expect(mocks.updateDraft).toHaveBeenCalledWith({
        draftId: "draft-1",
        startupProfileId: undefined,
        updates: {
          sectors: [
            "climate",
            "mobility",
          ],
          startup_name: "Updated Startup",
        },
      });
    });
  });

  test("requires explicit confirmation before submission", async () => {
    const confirmationPayload = payload({
      confirmation_required: true,
      current_state: "confirm_profile",
      draft: {
        current_step: 8,
        data: {
          startup_name: "Confirmed Startup",
        },
        id: "draft-1",
        status: "draft",
      },
      state_index: 6,
      title: "Confirm assessment",
    });
    const generatingPayload = payload({
      current_state: "generating_plan",
      state_index: 7,
      system_transition_required: true,
      title: "Generating deterministic results",
    });
    const readyPayload = payload({
      current_state: "plan_ready",
      draft: {
        current_step: 8,
        data: {
          startup_name: "Confirmed Startup",
        },
        id: "draft-1",
        status: "submitted",
      },
      is_terminal: true,
      state_index: 8,
      title: "Starting plan ready",
    });

    mocks.getCurrent
      .mockResolvedValueOnce(confirmationPayload)
      .mockResolvedValueOnce(readyPayload);
    mocks.transition.mockResolvedValue(
      generatingPayload,
    );
    mocks.submitAssessment.mockResolvedValue({
      draft: {
        id: "draft-1",
      },
    });

    render(<FounderConcierge />);

    openConcierge();

    fireEvent.click(
      await screen.findByRole("button", {
        name: "Confirm and generate plan",
      }),
    );

    await waitFor(() => {
      expect(mocks.transition).toHaveBeenCalledWith({
        confirmed: true,
        draftId: "draft-1",
        expectedState: "confirm_profile",
        startupProfileId: undefined,
      });
    });

    expect(
      mocks.submitAssessment,
    ).toHaveBeenCalledWith({
      draftId: "draft-1",
    });

    expect(
      await screen.findByText(
        "Starting plan ready",
        {
          selector: ".concierge-ready-card strong",
        },
      ),
    ).toBeInTheDocument();
  });

  test("reloads authoritative state after a stale conflict", async () => {
    const initialPayload = payload();
    const latestPayload = payload({
      allowed_fields: [
        "startup_name",
      ],
      current_state: "basic_info",
      state_index: 1,
      title: "Startup basics",
    });

    mocks.getCurrent
      .mockResolvedValueOnce(initialPayload)
      .mockResolvedValueOnce(latestPayload);
    mocks.transition.mockRejectedValue({
      response: {
        data: {
          code: "concierge_state_conflict",
          detail: "The state changed.",
        },
        status: 409,
      },
    });

    render(<FounderConcierge />);

    openConcierge();

    fireEvent.click(
      await screen.findByRole("button", {
        name: "Continue",
      }),
    );

    expect(
      await screen.findByText(
        /latest authoritative state has been loaded/i,
      ),
    ).toBeInTheDocument();
    expect(
      await screen.findByLabelText("Startup name"),
    ).toBeInTheDocument();
    expect(mocks.getCurrent).toHaveBeenCalledTimes(2);
  });

  test("provides an assessment action when no draft exists", async () => {
    const onNavigate = vi.fn();

    mocks.getCurrent.mockRejectedValue({
      response: {
        data: {
          detail: "An open assessment draft was not found.",
        },
        status: 404,
      },
    });

    render(
      <FounderConcierge
        onNavigate={onNavigate}
      />,
    );

    openConcierge();

    fireEvent.click(
      await screen.findByRole("button", {
        name: "Open startup assessment",
      }),
    );

    expect(onNavigate).toHaveBeenCalledWith(
      "assessment",
    );
  });
});
