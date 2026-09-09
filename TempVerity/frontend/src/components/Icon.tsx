const paths = {
  search: 'M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0m-2 5 6 6',
  chevronRight: 'm9 5 7 7-7 7',
  shield: 'M12 2 3 6v6c0 5 5 8 9 10 4-2 9-5 9-10V6l-9-4zM8 12l3 3 5-6',
  settings: 'M10 2h4l.5 3 2 1.2 2.8-1 2 3.6-2.3 2v2.4l2.3 2-2 3.6-2.8-1-2 1.2-.5 3h-4l-.5-3-2-1.2-2.8 1-2-3.6 2.3-2v-2.4l-2.3-2 2-3.6 2.8 1L9.5 5 10 2zM15.5 12a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0',
  devices: 'M5 3h14v18H5zM3 21h18M8 7h8M8 11h8M8 15h8M8 18h3',
  online: 'M8 12l3 3 5-6',
  alarm: 'M12 3 2 21h20L12 3zM12 9v5M12 17v.1',
  offline: 'M8 12h.01M12 12h.01M16 12h.01',
  bell: 'M18 9a6 6 0 0 0-12 0v5l-2 4h16l-2-4V9M10 21h4M12 2v1',
  temperature: 'M9 14V5a3 3 0 0 1 6 0v9a5 5 0 1 1-6 0M12 9v9',
  door: 'M5 3h12v18H5zM17 7h3v10h-3M8 6v12',
  events: 'M6 3h12v18H6zM9 7h6M9 11h6M9 15h4',
  reports: 'M4 21V11h4v10M10 21V3h4v18M16 21V7h4v14',
  grid: 'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z',
  list: 'M8 5h13M8 12h13M8 19h13M3 5h.01M3 12h.01M3 19h.01',
  monitor: 'M3 3h18v14H3zM8 21h8M12 17v4',
  lock: 'M5 10h14v11H5zM8 10V6a4 4 0 0 1 8 0v4',
  mail: 'M3 5h18v14H3zM3 5l9 7 9-7',
  code: 'm8 6-6 6 6 6m8-12 6 6-6 6M14 3l-4 18',
  plus: 'M4 4h16v16H4zM12 8v8M8 12h8',
  trash: 'M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7',
} as const;

export type IconName = keyof typeof paths;

export function Icon({ name, className = '' }: { name: IconName; className?: string }) {
  return <svg className={`ui-icon ${className}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {name === 'online' || name === 'offline' ? <circle cx="12" cy="12" r="9.5" /> : null}
    <path d={paths[name]} />
  </svg>;
}
