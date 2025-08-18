import React from 'react';

// Componente para el icono del candado cerrado
export const LockClosedIcon = ({ className }) => (
  <svg 
    className={className} 
    fill="none" 
    viewBox="0 0 24 24" 
    strokeWidth={1} 
    stroke="currentColor"
  >
    <path 
      strokeLinecap="round" 
      strokeLinejoin="round" 
      d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" 
    />
  </svg>
);

// Componente para el icono del candado abierto
export const LockOpenIcon = ({ className }) => (
  <svg 
    className={className} 
    fill="none" 
    viewBox="0 0 24 24" 
    strokeWidth={1} 
    stroke="currentColor"
  >
    {/* Cuerpo del candado - exactamente igual al cerrado */}
    <path 
      strokeLinecap="round" 
      strokeLinejoin="round" 
      d="M6.75 21.75h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" 
    />
    {/* Arco abierto - con más espaciado, se separa del cuerpo */}
    <path 
      strokeLinecap="round" 
      strokeLinejoin="round" 
      d="M7.5 10.5V6.75a4.5 4.5 0 019 0v1.5" 
    />
  </svg>
);
