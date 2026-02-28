'use client';

import { useEffect, useRef } from 'react';

interface UnitLocation {
  unit_id: string;
  unit_number: string;
  lat: number;
  lng: number;
  status: string;
}

interface CadLiveMapProps {
  units?: UnitLocation[];
  className?: string;
}

export function CadLiveMap({ units = [], className = '' }: CadLiveMapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<unknown>(null);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (mapInstance.current) return;

    import('leaflet').then((L) => {
      if (!mapRef.current) return;

      const map = L.map(mapRef.current, {
        center: [44.5, -89.5],
        zoom: 7,
        zoomControl: true,
      });

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19,
      }).addTo(map);

      const statusColors: Record<string, string> = {
        available: 'var(--color-status-active)',
        dispatched: 'var(--color-status-warning)',
        on_scene: 'var(--color-brand-orange)',
        transport: 'var(--color-system-fleet)',
        at_hospital: 'var(--color-system-compliance)',
      };

      units.forEach((unit) => {
        const color = statusColors[unit.status] || 'var(--color-text-muted)';
        const icon = L.divIcon({
          className: '',
          html: `<div style="background:${color};width:12px;height:12px;border-radius:50%;border:2px solid white;box-shadow:0 0 6px ${color}"></div>`,
          iconSize: [12, 12],
          iconAnchor: [6, 6],
        });
        L.marker([unit.lat, unit.lng], { icon })
          .addTo(map)
          .bindPopup(`<b>${unit.unit_number}</b><br>Status: ${unit.status}`);
      });

      mapInstance.current = map;
    });

    return () => {
      if (mapInstance.current) {
        (mapInstance.current as { remove: () => void }).remove();
        mapInstance.current = null;
      }
    };
  }, []);

  return (
    <div className={`rounded-2xl overflow-hidden border border-border ${className}`}>
      <div ref={mapRef} style={{ height: '400px', width: '100%' }} />
    </div>
  );
}
