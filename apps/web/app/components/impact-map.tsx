"use client";

import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { useEffect, useRef } from "react";

type MapPoint = {
  label: string;
  severity: number;
  directness: string;
  lat: number;
  lon: number;
};

type ImpactMapProps = {
  points: MapPoint[];
  lensType: "global" | "region" | "country";
  lensFocus: string;
};

const REGION_VIEW: Record<string, { center: [number, number]; zoom: number }> = {
  Gulf: { center: [25.5, 51.0], zoom: 4 },
  Levant: { center: [33.5, 36.0], zoom: 5 },
  MENA: { center: [28.5, 38.0], zoom: 4 },
  Europe: { center: [52.0, 12.0], zoom: 4 },
  "East Asia": { center: [30.0, 122.0], zoom: 4 },
  "Global shipping lanes": { center: [19.0, 40.0], zoom: 3 },
};

function severityColor(value: number): string {
  if (value >= 0.8) {
    return "#ef4444";
  }
  if (value >= 0.6) {
    return "#f97316";
  }
  if (value >= 0.4) {
    return "#f59e0b";
  }
  if (value >= 0.2) {
    return "#84cc16";
  }
  return "#22c55e";
}

function boundsFromPoints(points: MapPoint[]): L.LatLngBounds | null {
  if (points.length === 0) {
    return null;
  }
  const lats = points.map((p) => p.lat);
  const lons = points.map((p) => p.lon);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLon = Math.min(...lons);
  const maxLon = Math.max(...lons);
  const latPad = Math.max((maxLat - minLat) * 0.35, 4);
  const lonPad = Math.max((maxLon - minLon) * 0.35, 6);
  return L.latLngBounds(
    L.latLng(minLat - latPad, minLon - lonPad),
    L.latLng(maxLat + latPad, maxLon + lonPad)
  );
}

export default function ImpactMap({ points, lensType, lensFocus }: ImpactMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!containerRef.current) {
      return;
    }

    const container = containerRef.current as HTMLDivElement & { _leaflet_id?: number };

    if (mapRef.current) {
      mapRef.current.remove();
      mapRef.current = null;
    }

    // Guard against dev hot-reload/strict-mode remounts leaving stale Leaflet metadata on the same DOM node.
    if (container._leaflet_id) {
      container._leaflet_id = undefined;
      container.innerHTML = "";
    }

    const regionPreset = REGION_VIEW[lensFocus];
    const defaultCenter: [number, number] = [20, 10];
    const defaultZoom = lensType === "global" ? 2 : 3;

    const map = L.map(container, {
      center: regionPreset?.center ?? defaultCenter,
      zoom: regionPreset?.zoom ?? defaultZoom,
      zoomControl: true,
      scrollWheelZoom: false,
      worldCopyJump: true,
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);

    points.forEach((point) => {
      const marker = L.circleMarker([point.lat, point.lon], {
        radius: point.directness === "direct" ? 8 : 6,
        color: "#e2e8f0",
        weight: 1,
        fillColor: severityColor(point.severity),
        fillOpacity: 0.9,
      }).addTo(map);

      marker.bindTooltip(point.label, {
        permanent: true,
        direction: "top",
        offset: [0, -10],
        opacity: 0.9,
      });
    });

    const bounds = boundsFromPoints(points);
    if (bounds) {
      map.fitBounds(bounds, { padding: [16, 16], maxZoom: lensType === "country" ? 6 : 5 });
    } else if (lensType === "global") {
      map.setView([18, 5], 2);
    }

    mapRef.current = map;
    return () => {
      try {
        map.remove();
      } finally {
        mapRef.current = null;
        container.innerHTML = "";
        if (container._leaflet_id) {
          container._leaflet_id = undefined;
        }
      }
    };
  }, [points, lensType, lensFocus]);

  return <div ref={containerRef} className="country-map" />;
}
