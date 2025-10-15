import React from 'react';

export const CopyIcon = ({ size = 16, strokeWidth = 2, ...props }) => (
  <svg
    aria-hidden="true"
    fill="none"
    focusable="false"
    height={size}
    role="presentation"
    viewBox="0 0 24 24"
    width={size}
    {...props}
  >
    <path
      d="M16 12.9V17.1C16 20.6 14.6 22 11.1 22H6.9C3.4 22 2 20.6 2 17.1V12.9C2 9.4 3.4 8 6.9 8H11.1C14.6 8 16 9.4 16 12.9Z"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={strokeWidth}
    />
    <path
      d="M22 6.9V11.1C22 14.6 20.6 16 17.1 16H16V12.9C16 9.4 14.6 8 11.1 8H8V6.9C8 3.4 9.4 2 12.9 2H17.1C20.6 2 22 3.4 22 6.9Z"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={strokeWidth}
    />
  </svg>
);

export const CheckIcon = ({ size = 16, strokeWidth = 2, ...props }) => (
  <svg
    aria-hidden="true"
    fill="none"
    focusable="false"
    height={size}
    role="presentation"
    viewBox="0 0 24 24"
    width={size}
    {...props}
  >
    <polyline
      points="20 6 9 17 4 12"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={strokeWidth}
    />
  </svg>
);
