import CompleteWebsiteTour from "./tour/CompleteWebsiteTour";
import PageTour from "./tour/PageTour";

export default function WebsiteTour({
  includeReviewer = false,
  mode = "page",
  navigate,
  onDismiss,
  pathname = "/dashboard",
  run = false,
}) {
  if (mode === "complete") {
    return (
      <CompleteWebsiteTour
        includeReviewer={includeReviewer}
        navigate={navigate}
        onDismiss={onDismiss}
        pathname={pathname}
        run={run}
      />
    );
  }

  return (
    <PageTour
      onDismiss={onDismiss}
      pathname={pathname}
      run={run}
    />
  );
}
