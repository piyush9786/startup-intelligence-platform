import React from 'react';
import { render } from '@testing-library/react';
import { DashboardHome } from './src/DashboardHome';
import { MemoryRouter } from 'react-router-dom';

const div = document.createElement('div');
try {
  render(
    <MemoryRouter>
      <DashboardHome dashboardData={null} />
    </MemoryRouter>,
    { container: div }
  );
  console.log("Rendered without crash!");
} catch (e) {
  console.error("CRASHED:", e);
}
