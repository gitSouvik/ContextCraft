import React from 'react';

export const IconBase = ({ id, className, style }: { id: string, className?: string, style?: React.CSSProperties }) => (
  <svg className={`icon ${className || ''}`} style={style}>
    <use href={`#i-${id}`}></use>
  </svg>
);

export const IconsDefs = () => (
  <svg width="0" height="0" style={{ position: 'absolute' }}>
    <defs>
      <symbol id="i-compass" viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="8" />
        <path d="M12 2 L12 6" />
        <path d="M12 18 L12 22" />
        <path d="M2 12 L6 12" />
        <path d="M18 12 L22 12" />
      </symbol>
      <symbol id="i-chevron" viewBox="0 0 24 24">
        <path d="M6 9 L12 15 L18 9" />
      </symbol>
      <symbol id="i-folder" viewBox="0 0 24 24">
        <path d="M3 6.5 a1 1 0 0 1 1-1 h4.5 l2 2 h9.5 a1 1 0 0 1 1 1 v9 a1 1 0 0 1 -1 1 h-16 a1 1 0 0 1 -1 -1 z" />
      </symbol>
      <symbol id="i-file" viewBox="0 0 24 24">
        <path d="M6.5 2.5 h7.5 l4.5 4.5 v14 a1 1 0 0 1 -1 1 h-11 a1 1 0 0 1 -1 -1 v-17.5 a1 1 0 0 1 1 -1 z" />
        <path d="M14 2.5 v4.5 h4.5" />
      </symbol>
      <symbol id="i-search" viewBox="0 0 24 24">
        <circle cx="11" cy="11" r="7" />
        <path d="M21 21 L16.65 16.65" />
      </symbol>
      <symbol id="i-plus" viewBox="0 0 24 24">
        <path d="M12 5 L12 19" />
        <path d="M5 12 L19 12" />
      </symbol>
      <symbol id="i-minus" viewBox="0 0 24 24">
        <path d="M5 12 L19 12" />
      </symbol>
      <symbol id="i-reset" viewBox="0 0 24 24">
        <path d="M3.5 9 a8.5 8.5 0 1 1 -1 5" />
        <path d="M3.5 4 v5 h5" />
      </symbol>
      <symbol id="i-download" viewBox="0 0 24 24">
        <path d="M12 3 L12 15" />
        <path d="M7 10 L12 15 L17 10" />
        <path d="M4 20 L20 20" />
      </symbol>
      <symbol id="i-sparkle" viewBox="0 0 24 24">
        <path d="M12 2 L13.6 9.4 L21 12 L13.6 14.6 L12 22 L10.4 14.6 L3 12 L10.4 9.4 Z" />
      </symbol>
      <symbol id="i-clock" viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7 L12 12 L16 14" />
      </symbol>
      <symbol id="i-x" viewBox="0 0 24 24">
        <path d="M5 5 L19 19" />
        <path d="M19 5 L5 19" />
      </symbol>
      <symbol id="i-send" viewBox="0 0 24 24">
        <path d="M3 20 L21 12 L3 4 L3 10.5 L15 12 L3 13.5 Z" />
      </symbol>
      <symbol id="i-flame" viewBox="0 0 24 24">
        <path d="M12 2.5 C9 7 5.5 9 5.5 14 a6.5 6.5 0 0 0 13 0 C18.5 11 16.5 10 15.5 8 C15 10.5 13.5 10.5 13.5 8.5 C13.5 6.5 14.5 5.5 12 2.5 Z" />
      </symbol>
      <symbol id="i-cube" viewBox="0 0 24 24">
        <path d="M12 2.5 L21 7.5 V16.5 L12 21.5 L3 16.5 V7.5 Z" />
        <path d="M12 21.5 V12" />
        <path d="M3 7.5 L12 12 L21 7.5" />
      </symbol>
      <symbol id="i-bars" viewBox="0 0 24 24">
        <path d="M4 20 V11" />
        <path d="M11 20 V6" />
        <path d="M18 20 V3" />
      </symbol>
      <symbol id="i-arrow-right" viewBox="0 0 24 24">
        <path d="M5 12 L19 12" />
        <path d="M13 6 L19 12 L13 18" />
      </symbol>
    </defs>
  </svg>
);
