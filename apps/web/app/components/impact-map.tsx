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
  if (value >= 0.78) {
    return "#e24b4a";
  }
  if (value >= 0.52) {
    return "#ef9f27";
  }
  if (value >= 0.3) {
    return "#378add";
  }
  return "#1d9e75";
}

function hexToRgba(hex: string, alpha: number): string {
  const clean = hex.replace("#", "");
  const r = Number.parseInt(clean.slice(0, 2), 16);
  const g = Number.parseInt(clean.slice(2, 4), 16);
  const b = Number.parseInt(clean.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
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
  const ringsLayerRef = useRef<L.LayerGroup | null>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);
  const tileLayerRef = useRef<L.TileLayer | null>(null);

  useEffect(() => {
    if (!containerRef.current) {
      return;
    }

    const container = containerRef.current as HTMLDivElement & { _leaflet_id?: number };

    if (container._leaflet_id) {
      container._leaflet_id = undefined;
      container.innerHTML = "";
    }

    const map = L.map(container, {
      center: [20, 10],
      zoom: 2,
      zoomControl: true,
      scrollWheelZoom: false,
      worldCopyJump: true,
      zoomAnimation: false,
      fadeAnimation: false,
      markerZoomAnimation: false,
      inertia: false,
    });

    map.attributionControl.setPrefix("");
    tileLayerRef.current = L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      subdomains: "abcd",
      maxZoom: 19,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    });
    tileLayerRef.current.addTo(map);

    ringsLayerRef.current = L.layerGroup().addTo(map);
    markersLayerRef.current = L.layerGroup().addTo(map);

    mapRef.current = map;
    return () => {
      try {
        ringsLayerRef.current?.clearLayers();
        markersLayerRef.current?.clearLayers();
        ringsLayerRef.current?.remove();
        markersLayerRef.current?.remove();
        tileLayerRef.current?.remove();
        map.remove();
      } finally {
        mapRef.current = null;
        ringsLayerRef.current = null;
        markersLayerRef.current = null;
        tileLayerRef.current = null;
        container.innerHTML = "";
        if (container._leaflet_id) {
          container._leaflet_id = undefined;
        }
      }
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    const ringsLayer = ringsLayerRef.current;
    const markersLayer = markersLayerRef.current;
    if (!map || !ringsLayer || !markersLayer) {
      return;
    }

    ringsLayer.clearLayers();
    markersLayer.clearLayers();

    points.forEach((point) => {
      const color = severityColor(point.severity);
      const ringRadiusMeters = Math.round(
        (point.directness === "direct" ? 170000 : 240000) + (point.severity * 620000)
      );

      L.circle([point.lat, point.lon], {
        color,
        fillColor: hexToRgba(color, 0.18),
        fillOpacity: 1,
        weight: 1.5,
        radius: ringRadiusMeters,
        opacity: 0.85,
      }).addTo(ringsLayer);

      const marker = L.circleMarker([point.lat, point.lon], {
        radius: point.directness === "direct" ? 6 : 5,
        color,
        weight: 2,
        fillColor: color,
        fillOpacity: 1,
      }).addTo(markersLayer);

      const status =
        point.severity >= 0.78
          ? "DIRECT CONFLICT"
          : point.severity >= 0.52
            ? "ELEVATED TENSION"
            : point.severity >= 0.3
              ? "SYSTEMIC RISK"
              : "MONITORING";
      marker.bindPopup(
        `<div style="min-width:180px;">
          <div style="font-size:10px;letter-spacing:0.06em;color:#6b7a99;margin-bottom:4px;">${status}</div>
          <div style="font-weight:600;font-size:13px;margin-bottom:6px;color:#e2e8f4;">${point.label}</div>
          <div style="font-size:11px;color:#8898b8;line-height:1.5;">Exposure: ${point.directness}</div>
        </div>`
      );
    });

    const regionPreset = REGION_VIEW[lensFocus];
    const defaultCenter: [number, number] = [20, 10];
    const defaultZoom = lensType === "global" ? 2 : 3;
    const bounds = boundsFromPoints(points);
    if (bounds) {
      map.fitBounds(bounds, { padding: [16, 16], maxZoom: lensType === "country" ? 6 : 5 });
    } else {
      map.setView(regionPreset?.center ?? defaultCenter, regionPreset?.zoom ?? defaultZoom);
    }
  }, [points, lensType, lensFocus]);

  return (
    <div className="country-map-shell">
      <div className="risk-map-title">Geopolitical Risk Map</div>
      <div ref={containerRef} className="country-map" />
      <div className="risk-map-legend">
        <div className="risk-map-legend-title">Risk Status</div>
        <div className="risk-map-legend-item"><span className="risk-dot red" />Direct conflict zone</div>
        <div className="risk-map-legend-item"><span className="risk-dot amber" />Elevated / active tension</div>
        <div className="risk-map-legend-item"><span className="risk-dot blue" />Indirect / systemic risk</div>
        <div className="risk-map-legend-item"><span className="risk-dot green" />Monitoring / stable</div>
      </div>
    </div>
  );
}
